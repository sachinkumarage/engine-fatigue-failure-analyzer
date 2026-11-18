"""Gas loads: cylinder pressure table and gas force (equation L1)."""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from efa._checks import FloatOrArray, as_float_array, require_positive, to_output
from efa.provenance import Status

CYCLE_DEG = 720.0


@dataclass(frozen=True)
class PressureTable:
    """Absolute cylinder pressure over one four-stroke cycle.

    Attributes:
        angles_deg: Crank angles [deg], strictly increasing, from 0 to 720
            (0° = intake TDC, 360° = firing TDC).
        pressures_pa: Absolute cylinder pressure at each angle [Pa], all > 0.
            The first and last values must be equal (periodic cycle).
        source_id: Identifier of the data source (see efa.provenance.Source).
        status: Data status: cited, measured or assumed.
    """

    angles_deg: NDArray[np.float64]
    pressures_pa: NDArray[np.float64]
    source_id: str
    status: Status

    def __post_init__(self) -> None:
        angles = as_float_array("angles_deg", self.angles_deg)
        pressures = as_float_array("pressures_pa", self.pressures_pa)
        if angles.ndim != 1 or pressures.ndim != 1:
            raise ValueError("angles_deg and pressures_pa must be 1-D sequences.")
        if angles.size != pressures.size:
            raise ValueError(
                f"angles_deg ({angles.size}) and pressures_pa ({pressures.size}) "
                "must have the same length."
            )
        if angles.size < 2:
            raise ValueError("A pressure table needs at least two points.")
        if np.any(np.diff(angles) <= 0.0):
            raise ValueError("angles_deg must be strictly increasing.")
        if angles[0] != 0.0:
            raise ValueError(f"angles_deg must start at 0, got {angles[0]}.")
        if angles[-1] != CYCLE_DEG:
            raise ValueError(f"angles_deg must end at 720, got {angles[-1]}.")
        if np.any(pressures <= 0.0):
            raise ValueError("All pressures must be positive absolute pressures.")
        if not math.isclose(pressures[0], pressures[-1], rel_tol=1e-9, abs_tol=0.0):
            raise ValueError(
                "Pressures at 0° and 720° must be equal (periodic cycle), got "
                f"{pressures[0]} Pa and {pressures[-1]} Pa."
            )
        if not str(self.source_id).strip():
            raise ValueError("source_id must not be empty.")
        try:
            status = Status(self.status)
        except ValueError as exc:
            raise ValueError(
                f"status must be one of {[s.value for s in Status]}, "
                f"got {self.status!r}."
            ) from exc
        angles.setflags(write=False)
        pressures.setflags(write=False)
        object.__setattr__(self, "angles_deg", angles)
        object.__setattr__(self, "pressures_pa", pressures)
        object.__setattr__(self, "status", status)

    def pressure_at(self, theta_deg: ArrayLike) -> FloatOrArray:
        """Absolute cylinder pressure [Pa] at crank angle θ [deg].

        Linear interpolation between table points; θ is taken modulo 720°.
        """
        th = np.mod(as_float_array("theta_deg", theta_deg), CYCLE_DEG)
        return to_output(np.interp(th, self.angles_deg, self.pressures_pa))


def piston_area(bore: float) -> float:
    """L1: piston crown area A_p = π B² / 4.

    Symbols:
        B (bore): cylinder bore [m].
        A_p: projected piston area [m²].

    Validity: B > 0; circular bore.
    """
    return math.pi * require_positive("bore", bore) ** 2 / 4.0


def gas_force(p_cyl: ArrayLike, p_cc: float, area: float) -> FloatOrArray:
    """L1: net gas force on the piston F_g = (p_cyl − p_cc) A_p.

    Symbols:
        p_cyl: absolute cylinder pressure [Pa].
        p_cc: absolute crankcase pressure [Pa].
        A_p (area): piston area [m²].
        F_g: gas force, positive toward the crank [N].

    Validity: pressures are absolute and > 0; ring-pack leakage and pressure
    on the piston skirt are neglected.
    """
    p = as_float_array("p_cyl", p_cyl)
    if np.any(p <= 0.0):
        raise ValueError("p_cyl must be a positive absolute pressure.")
    p_cc = require_positive("p_cc", p_cc)
    area = require_positive("area", area)
    return to_output((p - p_cc) * area)
