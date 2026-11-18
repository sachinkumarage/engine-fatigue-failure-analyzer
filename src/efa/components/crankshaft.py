"""Crankshaft assessment: single-throw statically determinate beam (X1 to X5).

Model (decision D4): one crank throw between two main bearings, symmetric,
output torque taken at the drive-side journal. Two fillets are assessed:
"crankpin fillet" and "main journal fillet (drive side)".
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from efa._checks import FloatOrArray, as_float_array, require_positive, to_output
from efa.components.common import (
    LocationResult,
    Material,
    as_array,
    assess_location,
    check_cycle_grid,
    endurance_inputs,
    fmt,
    governing,
    markdown_table,
    merge_notes,
    report,
)
from efa.fatigue.basquin import BasquinConstants
from efa.fatigue.marin import EnduranceLimit
from efa.loads.cycle import CycleResult
from efa.provenance import ResultNote, Status
from efa.stress.nominal import bending_stress, torsional_stress
from efa.stress.notch import fatigue_notch_factor, notch_sensitivity

MPA = 1.0e6
PIN = "crankpin fillet"
JOURNAL = "main journal fillet (drive side)"
FILLETS = (PIN, JOURNAL)


def total_radial_load(f_r: ArrayLike, f_c: float) -> FloatOrArray:
    """X1: total radial crankpin load F_R(θ) = F_r(θ) − F_c.

    Symbols:
        F_r (f_r): radial crankpin force from the rod, positive toward the
            crank axis [N] (L6).
        F_c (f_c): rotating-mass centrifugal force, acting outward [N] (L7).
        F_R: total radial load, positive toward the crank axis [N].

    Validity: crank-web and counterweight masses excluded.
    Source: force balance at the crankpin (decision 0003).
    """
    return to_output(as_float_array("f_r", f_r) - float(f_c))


def crankpin_torques(f_t: ArrayLike, r: float) -> tuple[FloatOrArray, FloatOrArray]:
    """X3 by statics: crankpin torsion on the free-end and drive sides.

    Free-end side: T = (F_t/2) r from the free-end bearing reaction F_t/2.
    Drive side: T = F_t r − (F_t/2) r, output torque F_t r minus the moment of
    the drive-side bearing reaction. Both equal F_t r / 2.

    Symbols:
        F_t (f_t): tangential crankpin force [N] (L6).
        r: crank radius [m].

    Validity: symmetric single throw, output torque at the drive-side
    journal (D4); torsional vibration excluded.
    Source: statics, derived in docs/methods/crankshaft.md.

    Returns:
        (T free-end side, T drive side) [N·m].
    """
    ft = as_float_array("f_t", f_t)
    r = require_positive("r", r)
    reaction = ft / 2.0
    return to_output(reaction * r), to_output(ft * r - reaction * r)


def pin_bending_moment(f_rad: ArrayLike, l_b: float, s_p: float) -> FloatOrArray:
    """X2: crankpin fillet bending moment M_pin = (F_R/2)(L_b/2 − s_p).

    Symbols:
        F_R (f_rad): total radial load [N] (X1).
        L_b (l_b): main-bearing span, centre to centre [m].
        s_p: axial distance from the pin centre to the fillet [m].
        M_pin: bending moment in the crank plane [N·m].

    Validity: symmetric single throw, simply supported (D4); 0 < s_p < L_b/2.
    Source: statics (decision 0003).
    """
    l_b, s_p = _check_span(l_b, s_p)
    return to_output(as_float_array("f_rad", f_rad) / 2.0 * (l_b / 2.0 - s_p))


def pin_torque(f_t: ArrayLike, r: float) -> FloatOrArray:
    """X3: crankpin torsion T_pin = F_t r / 2.

    Symbols:
        F_t (f_t): tangential crankpin force [N].
        r: crank radius [m].
        T_pin: torque in the crankpin [N·m].

    Validity: symmetric single throw with output torque at the drive-side
    journal (D4).
    Source: statics, see ``crankpin_torques`` and docs/methods/crankshaft.md.
    """
    return crankpin_torques(f_t, r)[0]


def journal_loads(
    f_rad: ArrayLike, f_t: ArrayLike, s_j: float, r: float
) -> tuple[FloatOrArray, FloatOrArray]:
    """X4: drive-side main-journal fillet M_j = (F_R/2) s_j; T_j = F_t r.

    Symbols:
        F_R (f_rad): total radial load [N].
        F_t (f_t): tangential crankpin force [N].
        s_j: distance from the bearing centre to the fillet [m].
        r: crank radius [m].
        M_j, T_j: bending moment and torque at the fillet [N·m].

    Validity: symmetric single throw; output torque at the drive side.
    Source: statics (decision 0003).
    """
    s_j = require_positive("s_j", s_j)
    r = require_positive("r", r)
    m = as_float_array("f_rad", f_rad) / 2.0 * s_j
    return to_output(m), to_output(as_float_array("f_t", f_t) * r)


def fillet_stresses(
    moment: ArrayLike, torque: ArrayLike, d: float, k_f_b: float, k_f_t: float
) -> tuple[FloatOrArray, FloatOrArray]:
    """X5: notched fillet stresses σ_b = K_f,b 32 M/(π d³); τ = K_f,t 16 T/(π d³).

    Symbols:
        M (moment): bending moment in the crank plane [N·m].
        T (torque): torque [N·m].
        d: shaft diameter at the fillet [m].
        K_f,b, K_f,t: fatigue notch factors in bending and torsion [-].
        σ_b, τ: notched bending and shear stress [Pa].

    Validity: fillet point in the crank plane on the pin side facing the
    crank axis; tangential bending is zero there (neutral axis). Solid round
    section.
    Source: S1 with c = d/2, I = π d⁴/64, J = π d⁴/32.
    """
    d = require_positive("d", d)
    for name, k in (("K_f,b", k_f_b), ("K_f,t", k_f_t)):
        if not math.isfinite(k) or k < 1.0:
            raise ValueError(f"{name} must be >= 1, got {k}.")
    inertia = math.pi * d**4 / 64.0
    sigma = k_f_b * np.asarray(bending_stress(moment, d / 2.0, inertia))
    tau = k_f_t * np.asarray(torsional_stress(torque, d / 2.0, 2.0 * inertia))
    return to_output(sigma), to_output(tau)


@dataclass(frozen=True)
class FilletNotch:
    """Stress concentration at one fillet: K_t in bending and torsion [-],
    fillet radius rho [m]."""

    K_t_bending: float
    K_t_torsion: float
    rho: float


@dataclass(frozen=True)
class CrankGeometry:
    """Single-throw crankshaft geometry (SI units).

    Attributes:
        L_b: main-bearing span [m].
        s_p: pin centre to crankpin fillet, axial [m], 0 < s_p < L_b/2.
        d_pin: crankpin diameter [m].
        s_j: drive-side bearing centre to journal fillet, axial [m].
        d_journal: main-journal diameter [m].
        pin_fillet, journal_fillet: K_t and ρ per fillet (inputs; to be
            replaced by FEA results in Phase 5).
        sqrt_a: Neuber constant [m^0.5] for N2.
        status: data status of the geometry inputs.
    """

    L_b: float
    s_p: float
    d_pin: float
    s_j: float
    d_journal: float
    pin_fillet: FilletNotch
    journal_fillet: FilletNotch
    sqrt_a: float
    status: Status = Status.ASSUMED

    def __post_init__(self) -> None:
        _check_span(self.L_b, self.s_p)
        for name in ("d_pin", "s_j", "d_journal", "sqrt_a"):
            require_positive(name, getattr(self, name))
        object.__setattr__(self, "status", Status(self.status))
        for f in (self.pin_fillet, self.journal_fillet):
            require_positive("rho", f.rho)
            fatigue_notch_factor(f.K_t_bending, 0.0)
            fatigue_notch_factor(f.K_t_torsion, 0.0)


@dataclass(frozen=True)
class FilletResult:
    """Results at one fillet: notch factors, load extremes, histories and the
    fatigue assessment."""

    name: str
    d: float
    q: float
    K_f_b: float
    K_f_t: float
    M_max: float
    M_min: float
    T_max: float
    T_min: float
    sigma_history: NDArray[np.float64]
    tau_history: NDArray[np.float64]
    location: LocationResult


@dataclass(frozen=True)
class CrankshaftResult:
    """Crankshaft assessment."""

    theta_deg: NDArray[np.float64]
    F_R: NDArray[np.float64]
    fillets: tuple[FilletResult, ...]
    governing: tuple[str, float]
    inputs: tuple[tuple[str, str, str, str, str], ...]
    note: ResultNote

    def fillet(self, name: str) -> FilletResult:
        """Result of the fillet with the given name."""
        for f in self.fillets:
            if f.name == name:
                return f
        raise KeyError(name)

    def as_markdown(self) -> str:
        """Markdown report of inputs, equations, results and warnings."""

        def row(label, fn):
            return (label, *(fn(f) for f in self.fillets))

        rows = [
            row("K_f,b / K_f,t", lambda f: f"{fmt(f.K_f_b)} / {fmt(f.K_f_t)}"),
            row("S_e [MPa]", lambda f: fmt(f.location.S_e / MPA)),
            row("M max / min [N·m]", lambda f: f"{fmt(f.M_max)} / {fmt(f.M_min)}"),
            row("T max / min [N·m]", lambda f: f"{fmt(f.T_max)} / {fmt(f.T_min)}"),
            row("σ_a / σ_m [MPa]", lambda f: f"{fmt(f.location.sigma_a / MPA)} / "
                f"{fmt(f.location.sigma_m / MPA)}"),
            row("τ_a / τ_m [MPa]", lambda f: f"{fmt(f.location.tau_a / MPA)} / "
                f"{fmt(f.location.tau_m / MPA)}"),
            row("σ′_a / σ′_m [MPa]", lambda f: f"{fmt(f.location.sigma_eq_a / MPA)}"
                f" / {fmt(f.location.sigma_eq_m / MPA)}"),
            row("n Goodman", lambda f: fmt(f.location.assessment.n_goodman)),
            row("n Gerber", lambda f: fmt(f.location.assessment.n_gerber)),
            row("n Elliptic", lambda f: fmt(f.location.assessment.n_elliptic)),
            row("n_y Langer", lambda f: fmt(f.location.assessment.n_yield)),
            row("N_f", lambda f: fmt(f.location.life.N_f) if f.location.life else "—"),
        ]  # fmt: skip
        table = markdown_table(("Quantity", *(f.name for f in self.fillets)), rows)
        gov = f"**Governing:** {self.governing[0]}, n = {fmt(self.governing[1])}"
        return report("Crankshaft assessment", self.inputs, f"{table}\n\n{gov}",
                      self.note)  # fmt: skip


def assess_crankshaft(
    cycle: CycleResult,
    geometry: CrankGeometry,
    material: Material,
    marin_per_fillet: Mapping[str, EnduranceLimit],
    basquin: BasquinConstants | None,
) -> CrankshaftResult:
    """Assess the crankpin fillet and the drive-side main-journal fillet.

    Args:
        cycle: result of evaluate_cycle (0..719 grid).
        geometry: crank geometry and fillet notch data.
        material: crankshaft material (S_ut, S_y).
        marin_per_fillet: endurance limit per fillet name ("crankpin fillet",
            "main journal fillet (drive side)").
        basquin: constants for finite life when n_Goodman < 1, or None.
    """
    missing = [n for n in FILLETS if n not in marin_per_fillet]
    if missing:
        raise ValueError(f"marin_per_fillet is missing {missing}.")
    r = cycle.r
    f_rad = np.asarray(total_radial_load(cycle.F_r, cycle.F_c))
    m_pin = np.asarray(pin_bending_moment(f_rad, geometry.L_b, geometry.s_p))
    t_pin = np.asarray(pin_torque(cycle.F_t, r))
    m_j, t_j = (np.asarray(v) for v in journal_loads(f_rad, cycle.F_t, geometry.s_j, r))

    results = []
    for name, d, notch, m, t in (
        (PIN, geometry.d_pin, geometry.pin_fillet, m_pin, t_pin),
        (JOURNAL, geometry.d_journal, geometry.journal_fillet, m_j, t_j),
    ):
        q = notch_sensitivity(geometry.sqrt_a, notch.rho)
        k_f_b = fatigue_notch_factor(notch.K_t_bending, q)
        k_f_t = fatigue_notch_factor(notch.K_t_torsion, q)
        sig, tau = (np.asarray(v) for v in fillet_stresses(m, t, d, k_f_b, k_f_t))
        loc = assess_location(name, sig, tau, marin_per_fillet[name], material, basquin)
        results.append(FilletResult(
            name, d, q, k_f_b, k_f_t, float(m.max()), float(m.min()),
            float(t.max()), float(t.min()), as_array(sig), as_array(tau), loc,
        ))  # fmt: skip

    items = [(f"{f.name} fatigue", f.location.assessment.n_goodman) for f in results]
    items += [(f"{f.name} yield (Langer)", f.location.assessment.n_yield)
              for f in results]  # fmt: skip
    gov = governing(items)
    validity = [
        "Single-throw statically determinate beam between two main bearings, "
        "symmetric, output torque at the drive-side journal (D4).",
        "Torsional vibration excluded.",
        "Crank-web and counterweight masses excluded (X1 uses F_r − F_c only).",
        "σ and τ extrema taken independently (non-proportional loading not modelled).",
        "K_t values are inputs, to be replaced by FEA results in Phase 5.",
        "Fillet point in the crank plane facing the crank axis; tangential "
        "bending is zero there (X5).",
        f"Crank radius r = {fmt(r * 1e3)} mm.",
        *check_cycle_grid(cycle),
    ]
    statuses = {
        "material": material.status,
        "geometry": geometry.status,
        "cylinder pressure": cycle.note.input_statuses.get(
            "cylinder pressure", Status.ASSUMED
        ),
    }
    for n in FILLETS:
        statuses[f"S_e' ({n})"] = marin_per_fillet[n].S_e_prime.status
    if basquin is not None:
        statuses["Basquin constants"] = basquin.status
    sub = [(f.name, f.location.note) for f in results]
    sub += [(f"endurance limit ({n})", marin_per_fillet[n].note) for n in FILLETS]
    note = merge_notes(
        ("X1", "X2", "X3", "X4", "X5", "N1", "N2"), validity, sub, statuses,
        extra_verify=("N2 Neuber (SRC-SHIGLEY): verify √a for the material.",),
    )  # fmt: skip

    gs = geometry.status.value
    inputs = [
        ("Material", material.name, "", material.status.value, material.source_id),
        ("S_ut", fmt(material.S_ut / MPA), "MPa", material.status.value,
         material.source_id),
        ("S_y", fmt(material.S_y / MPA), "MPa", material.status.value,
         material.source_id),
        ("L_b", fmt(geometry.L_b * 1e3), "mm", gs, ""),
        ("s_p", fmt(geometry.s_p * 1e3), "mm", gs, ""),
        ("d_pin", fmt(geometry.d_pin * 1e3), "mm", gs, ""),
        ("s_j", fmt(geometry.s_j * 1e3), "mm", gs, ""),
        ("d_journal", fmt(geometry.d_journal * 1e3), "mm", gs, ""),
        ("√a", fmt(geometry.sqrt_a), "m^0.5", gs, ""),
    ]  # fmt: skip
    for label, f in (
        ("Pin", geometry.pin_fillet),
        ("Journal", geometry.journal_fillet),
    ):
        inputs.append((f"{label} K_t,b / K_t,t / ρ",
                       f"{fmt(f.K_t_bending)} / {fmt(f.K_t_torsion)} / "
                       f"{fmt(f.rho * 1e3)}", "- / - / mm", gs, ""))  # fmt: skip
    for n in FILLETS:
        inputs += endurance_inputs(n, marin_per_fillet[n])
    if basquin is not None:
        inputs.append(("σ′_f / b", f"{fmt(basquin.sigma_f_prime / MPA)} / "
                       f"{fmt(basquin.b)}", "MPa / -", basquin.status.value,
                       basquin.source_id))  # fmt: skip
    return CrankshaftResult(
        as_array(cycle.theta_deg), as_array(f_rad), tuple(results), gov,
        tuple(inputs), note,
    )  # fmt: skip


def _check_span(l_b: float, s_p: float) -> tuple[float, float]:
    l_b = require_positive("L_b", l_b)
    s_p = require_positive("s_p", s_p)
    if s_p >= l_b / 2.0:
        raise ValueError(f"s_p ({s_p} m) must be less than L_b/2 ({l_b / 2.0} m).")
    return l_b, s_p
