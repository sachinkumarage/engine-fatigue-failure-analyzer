"""Engine load cycle: rod and crankpin forces (equations L4 to L6) and the
evaluation of all load equations over the crank cycle.

Conventions (docs/decisions/0001-phase-0-decisions.md):
    θ: 0° = intake TDC, 360° = firing TDC, cycle 0–720°.
    Forces along the cylinder axis and the rod force are positive toward the
    crank (rod compression positive).
"""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import ArrayLike, NDArray

from efa._checks import (
    FloatOrArray,
    as_float_array,
    require_non_negative,
    require_positive,
    to_output,
)
from efa.loads.gas import PressureTable, gas_force, piston_area
from efa.loads.inertia import (
    centrifugal_force,
    inertia_force,
    reciprocating_mass,
    rod_mass_split,
)
from efa.loads.kinematics import (
    angular_speed,
    crank_radius,
    crank_ratio,
    piston_acceleration,
    rod_angle,
    series_acceleration_deviation,
)
from efa.provenance import ResultNote, Status

P_ATM = 101325.0

# --- Equations L4 to L6 ----------------------------------------------------


def net_piston_force(f_g: ArrayLike, f_i: ArrayLike) -> FloatOrArray:
    """L4: net piston force F_p = F_g + F_i.

    Symbols:
        F_g (f_g): gas force, positive toward the crank [N].
        F_i (f_i): inertia force, positive toward the crank [N].
        F_p: net force along the cylinder axis, positive toward the crank [N].

    Validity: friction and piston-pin offset neglected.
    """
    return to_output(as_float_array("f_g", f_g) + as_float_array("f_i", f_i))


def rod_forces(f_p: ArrayLike, beta: ArrayLike) -> tuple[FloatOrArray, FloatOrArray]:
    """L5: rod axial force and piston side thrust.

    F_rod = F_p / cos β;   F_side = F_p tan β

    Symbols:
        F_p (f_p): net piston force, positive toward the crank [N].
        β (beta): rod angle [rad].
        F_rod: rod axial force, compression positive [N].
        F_side: side thrust on the cylinder wall [N]; its sign follows β.

    Validity: |β| < π/2; rod inertia (rotating share, rod whip) neglected in
    the force balance at the small end.

    Returns:
        (F_rod, F_side) in N.
    """
    fp = as_float_array("f_p", f_p)
    b = as_float_array("beta", beta)
    return to_output(fp / np.cos(b)), to_output(fp * np.tan(b))


def crankpin_forces(
    f_rod: ArrayLike, theta: ArrayLike, beta: ArrayLike, r: float
) -> tuple[FloatOrArray, FloatOrArray, FloatOrArray]:
    """L6: crankpin tangential and radial force, and crank torque.

    F_t = F_rod sin(θ + β);   F_r = F_rod cos(θ + β);   T = F_t r

    Symbols:
        F_rod (f_rod): rod axial force, compression positive [N].
        θ (theta): crank angle [rad].
        β (beta): rod angle [rad].
        r: crank radius [m].
        F_t: tangential crankpin force, positive in the direction of rotation
            (driving) [N].
        F_r: radial crankpin force, positive toward the crank axis [N].
        T: crank torque from one cylinder [N·m].

    Validity: rotating-mass force F_c (L7) is not included in F_r.

    Returns:
        (F_t, F_r, T) with F_t, F_r in N and T in N·m.
    """
    fr = as_float_array("f_rod", f_rod)
    phi = as_float_array("theta", theta) + as_float_array("beta", beta)
    r = require_positive("r", r)
    f_t = fr * np.sin(phi)
    return to_output(f_t), to_output(fr * np.cos(phi)), to_output(f_t * r)


# --- Engine specification and cycle evaluation ------------------------------


@dataclass(frozen=True)
class EngineSpec:
    """Single-cylinder engine data in SI units.

    Attributes:
        bore: Cylinder bore B [m].
        stroke: Piston stroke S [m].
        rod_length: Rod length l, centre to centre [m].
        speed_rpm: Crankshaft speed n [rpm].
        m_piston: Piston mass [kg].
        m_pin: Gudgeon pin mass [kg], >= 0 (may be lumped into m_piston).
        m_rings: Ring-pack mass [kg], >= 0 (may be lumped into m_piston).
        m_rod: Total connecting-rod mass [kg].
        l_g: Distance from big-end centre to rod centre of gravity [m].
        p_crankcase: Absolute crankcase pressure [Pa], default 1 atm.
        pressure_table: Absolute cylinder pressure over the cycle, optional.
    """

    bore: float
    stroke: float
    rod_length: float
    speed_rpm: float
    m_piston: float
    m_pin: float
    m_rings: float
    m_rod: float
    l_g: float
    p_crankcase: float = P_ATM
    pressure_table: PressureTable | None = None

    def __post_init__(self) -> None:
        for name in (
            "bore",
            "stroke",
            "rod_length",
            "speed_rpm",
            "m_piston",
            "m_rod",
            "l_g",
            "p_crankcase",
        ):
            object.__setattr__(self, name, require_positive(name, getattr(self, name)))
        for name in ("m_pin", "m_rings"):
            value = require_non_negative(name, getattr(self, name))
            object.__setattr__(self, name, value)
        r = self.stroke / 2.0
        if self.rod_length <= r:
            raise ValueError(
                f"rod_length ({self.rod_length} m) must be greater than the crank "
                f"radius stroke/2 ({r} m)."
            )
        if not 0.0 < self.l_g < self.rod_length:
            raise ValueError(
                f"l_g ({self.l_g} m) must lie between 0 and rod_length "
                f"({self.rod_length} m)."
            )
        if self.pressure_table is not None and not isinstance(
            self.pressure_table, PressureTable
        ):
            raise ValueError("pressure_table must be a PressureTable or None.")


@dataclass(frozen=True)
class CycleResult:
    """Engine loads at the evaluated crank angles (SI units).

    Array attributes share the shape of ``theta_deg``:
        theta_deg [deg], p_cyl [Pa], F_g [N], a_p [m/s²], F_i [N], F_p [N],
        beta [rad], F_rod [N], F_side [N], F_t [N], F_r [N], T [N·m].
    Scalar attributes:
        r: crank radius [m] (K1).
        omega: crank angular speed [rad/s] (K1).
        F_c: rotating-mass centrifugal force [N].
        a_series_max_dev: max |a_exact (K3e) − a_p (K3)| on the grid [m/s²].
        a_series_max_dev_pct: that deviation in % of the peak |a_exact|.
        a_series_max_dev_theta_deg: angle of the maximum deviation [deg].
        F_rod_max_compression, theta_max_compression_deg: largest F_rod
            (compression positive) and its angle.
        F_rod_max_tension, theta_max_tension_deg: smallest F_rod (most
            tensile) and its angle; positive if the rod is never in tension.
        note: equations, validity notes, verify flags and input statuses.
    """

    theta_deg: NDArray[np.float64]
    p_cyl: NDArray[np.float64]
    F_g: NDArray[np.float64]
    a_p: NDArray[np.float64]
    F_i: NDArray[np.float64]
    F_p: NDArray[np.float64]
    beta: NDArray[np.float64]
    F_rod: NDArray[np.float64]
    F_side: NDArray[np.float64]
    F_t: NDArray[np.float64]
    F_r: NDArray[np.float64]
    T: NDArray[np.float64]
    r: float
    omega: float
    F_c: float
    a_series_max_dev: float
    a_series_max_dev_pct: float
    a_series_max_dev_theta_deg: float
    F_rod_max_compression: float
    theta_max_compression_deg: float
    F_rod_max_tension: float
    theta_max_tension_deg: float
    note: ResultNote = field(repr=False)

    @property
    def T_mean(self) -> float:
        """Arithmetic mean of T over the evaluated angles [N·m].

        Equals the cycle-mean torque only for a uniform grid covering one full
        cycle, such as the default 0..719° grid.
        """
        return float(np.mean(self.T))


def _evaluate(
    spec: EngineSpec,
    theta_deg: NDArray[np.float64],
    p_cyl: NDArray[np.float64],
    pressure_status: Status,
    extra_notes: tuple[str, ...],
) -> CycleResult:
    r = crank_radius(spec.stroke)
    l_rod = spec.rod_length
    lam = crank_ratio(r, l_rod)
    omega = angular_speed(spec.speed_rpm)
    theta = np.deg2rad(theta_deg)

    f_g = np.asarray(gas_force(p_cyl, spec.p_crankcase, piston_area(spec.bore)))
    a_p = np.asarray(piston_acceleration(theta, r, l_rod, omega))
    m_rod_a, m_rot = rod_mass_split(spec.m_rod, spec.l_g, l_rod)
    m_rec = reciprocating_mass(spec.m_piston, spec.m_pin, spec.m_rings, m_rod_a)
    f_i = np.asarray(inertia_force(m_rec, a_p))
    f_p = np.asarray(net_piston_force(f_g, f_i))
    beta = np.asarray(rod_angle(theta, r, l_rod))
    f_rod, f_side = (np.asarray(v) for v in rod_forces(f_p, beta))
    f_t, f_r, torque = (np.asarray(v) for v in crankpin_forces(f_rod, theta, beta, r))
    f_c = centrifugal_force(m_rot, r, omega)

    i_c = int(np.argmax(f_rod))
    i_t = int(np.argmin(f_rod))

    dev, dev_pct, dev_theta = series_acceleration_deviation(theta, r, l_rod, omega)
    dev_theta_deg = float(np.rad2deg(dev_theta))

    verify: list[str] = []
    if pressure_status is Status.ASSUMED:
        verify.append(
            "Cylinder pressure status is 'assumed': results are not loads of a "
            "real engine until cited or measured pressure data are used."
        )
    note = ResultNote(
        equation_ids=(
            "K1",
            "K3",
            "K3e",
            "K4",
            "L1",
            "L2",
            "L3",
            "L4",
            "L5",
            "L6",
            "L7",
        ),
        validity_notes=(
            f"K3 is a second-order series in λ; its error grows with λ "
            f"(λ = {lam:.4f} here).",
            f"Series acceleration (K3) deviates from exact (K3e) by at most "
            f"{dev_pct:.4g} % of peak |a_p| on the evaluated grid "
            f"(max at {dev_theta_deg:g} deg).",
            "Constant crank speed; speed variation within a cycle is not modelled.",
            "Two-mass rod model (L2): rod moment of inertia is not preserved and "
            "rod whip bending is not included.",
            "Single cylinder, four-stroke; no torsional vibration.",
            *extra_notes,
        ),
        verify_flags=tuple(verify),
        input_statuses={"cylinder pressure": pressure_status},
    )

    arrays = [theta_deg, p_cyl, f_g, a_p, f_i, f_p, beta, f_rod, f_side]
    arrays += [f_t, f_r, torque]
    for a in arrays:
        a.setflags(write=False)
    return CycleResult(
        theta_deg=theta_deg,
        p_cyl=p_cyl,
        F_g=f_g,
        a_p=a_p,
        F_i=f_i,
        F_p=f_p,
        beta=beta,
        F_rod=f_rod,
        F_side=f_side,
        F_t=f_t,
        F_r=f_r,
        T=torque,
        r=r,
        omega=omega,
        F_c=f_c,
        a_series_max_dev=dev,
        a_series_max_dev_pct=dev_pct,
        a_series_max_dev_theta_deg=dev_theta_deg,
        F_rod_max_compression=float(f_rod[i_c]),
        theta_max_compression_deg=float(theta_deg[i_c]),
        F_rod_max_tension=float(f_rod[i_t]),
        theta_max_tension_deg=float(theta_deg[i_t]),
        note=note,
    )


def evaluate_cycle(spec: EngineSpec, theta_deg: ArrayLike | None = None) -> CycleResult:
    """Evaluate equations K1, K3, K3e, K4 and L1 to L7 over the crank cycle.

    Args:
        spec: Engine data; ``spec.pressure_table`` is required.
        theta_deg: Crank angles [deg]; default integer degrees 0..719.
            Pressure is interpolated with θ modulo 720°.

    Returns:
        CycleResult with arrays over ``theta_deg``.

    Raises:
        ValueError: if the spec has no pressure table or angles are invalid.
    """
    if spec.pressure_table is None:
        raise ValueError(
            "evaluate_cycle needs spec.pressure_table; use peak_load for a "
            "single peak-pressure point."
        )
    if theta_deg is None:
        th = np.arange(720, dtype=float)
    else:
        th = np.atleast_1d(as_float_array("theta_deg", theta_deg)).astype(float)
        if th.ndim != 1 or th.size == 0:
            raise ValueError("theta_deg must be a non-empty 1-D sequence.")
    p_cyl = np.atleast_1d(np.asarray(spec.pressure_table.pressure_at(th)))
    notes = (f"Cylinder pressure from table '{spec.pressure_table.source_id}'.",)
    return _evaluate(spec, th, p_cyl, spec.pressure_table.status, notes)


def peak_load(
    spec: EngineSpec,
    p_peak: float,
    theta_peak_deg: float,
    *,
    status: Status = Status.ASSUMED,
) -> CycleResult:
    """Evaluate the loads at a single crank angle with a given peak pressure.

    Args:
        spec: Engine data; ``spec.pressure_table`` is ignored.
        p_peak: Absolute cylinder pressure at ``theta_peak_deg`` [Pa].
        theta_peak_deg: Crank angle of the peak pressure [deg].
        status: Data status of ``p_peak`` (default assumed).

    Returns:
        CycleResult whose arrays have length 1.
    """
    p = require_positive("p_peak", p_peak)
    th = np.array([float(as_float_array("theta_peak_deg", theta_peak_deg))])
    notes = (
        "Peak-only mode: loads at one crank angle; cycle extremes and mean "
        "torque refer to that single point.",
    )
    return _evaluate(spec, th, np.array([p]), Status(status), notes)
