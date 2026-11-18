"""Column buckling: Euler and Johnson (equations C1 to C3)."""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from efa._checks import FloatOrArray, as_float_array, require_positive, to_output
from efa.provenance import ResultNote


def radius_of_gyration(inertia: float, area: float) -> float:
    """C1: radius of gyration k = √(I / A).

    Symbols:
        I (inertia): second moment of area about the buckling axis [m⁴].
        A (area): cross-section area [m²].
        k: radius of gyration [m].

    Source: definition.
    """
    return math.sqrt(require_positive("I", inertia) / require_positive("A", area))


def euler_stress(E: float, slenderness: ArrayLike) -> FloatOrArray:
    """C1: Euler critical stress σ_cr = π² E / (L_e/k)² (verify).

    Symbols:
        E: Young's modulus [Pa].
        L_e/k (slenderness): effective slenderness ratio [-], L_e = K L.
        σ_cr: critical stress [Pa].

    Validity: elastic buckling, L_e/k >= (L_e/k)₁ (C3); straight, centrally
    loaded column.
    Source: SRC-SHIGLEY (verify).
    """
    E = require_positive("E", E)
    s = as_float_array("slenderness", slenderness)
    if np.any(s <= 0.0):
        raise ValueError("slenderness must be > 0.")
    return to_output(math.pi**2 * E / s**2)


def johnson_stress(S_y: float, E: float, slenderness: ArrayLike) -> FloatOrArray:
    """C2: Johnson critical stress σ_cr = S_y − (S_y² / (4π² E)) (L_e/k)² (verify).

    Symbols:
        S_y: yield strength [Pa].
        E: Young's modulus [Pa].
        L_e/k (slenderness): effective slenderness ratio [-].
        σ_cr: critical stress [Pa].

    Validity: inelastic (intermediate) columns, L_e/k < (L_e/k)₁ (C3).
    Source: SRC-SHIGLEY (verify).
    """
    S_y = require_positive("S_y", S_y)
    E = require_positive("E", E)
    s = as_float_array("slenderness", slenderness)
    if np.any(s < 0.0):
        raise ValueError("slenderness must be >= 0.")
    return to_output(S_y - S_y**2 / (4.0 * math.pi**2 * E) * s**2)


def transition_slenderness(E: float, S_y: float) -> float:
    """C3: Euler–Johnson transition (L_e/k)₁ = √(2π² E / S_y) (verify).

    Symbols:
        E: Young's modulus [Pa].
        S_y: yield strength [Pa].
        (L_e/k)₁: transition slenderness [-]; there σ_cr = S_y / 2.

    Source: SRC-SHIGLEY (verify).
    """
    E = require_positive("E", E)
    S_y = require_positive("S_y", S_y)
    return math.sqrt(2.0 * math.pi**2 * E / S_y)


@dataclass(frozen=True)
class ColumnResult:
    """Result of ``column_check`` (SI units).

    Attributes:
        k: radius of gyration [m].
        slenderness: L_e/k [-].
        transition_slenderness: (L_e/k)₁ [-].
        regime: "Euler" or "Johnson".
        sigma_cr: critical stress [Pa].
        P_cr: critical load σ_cr A [N].
        n: buckling safety factor P_cr / P [-]; inf for P <= 0.
        note: equations, validity and verify flags.
    """

    k: float
    slenderness: float
    transition_slenderness: float
    regime: str
    sigma_cr: float
    P_cr: float
    n: float
    note: ResultNote


def column_check(
    A: float,
    I: float,  # noqa: E741
    L: float,
    K: float,
    E: float,
    S_y: float,
    P: float,
) -> ColumnResult:
    """Buckling check of a pin-ended or restrained column (C1 to C3).

    Args:
        A: cross-section area [m²].
        I: second moment of area about the buckling axis [m⁴].
        L: column length [m].
        K: effective-length factor [-], L_e = K L.
        E: Young's modulus [Pa].
        S_y: yield strength [Pa].
        P: axial load [N], compression positive. P <= 0 gives n = inf.

    Returns:
        ColumnResult with the regime chosen by C3.
    """
    A = require_positive("A", A)
    I = require_positive("I", I)  # noqa: E741
    L = require_positive("L", L)
    K = require_positive("K", K)
    E = require_positive("E", E)
    S_y = require_positive("S_y", S_y)
    P = float(P)
    if not math.isfinite(P):
        raise ValueError("P must be finite.")

    k = radius_of_gyration(I, A)
    slender = K * L / k
    s1 = transition_slenderness(E, S_y)
    if slender < s1:
        regime, sigma_cr, eq = "Johnson", float(johnson_stress(S_y, E, slender)), "C2"
    else:
        regime, sigma_cr, eq = "Euler", float(euler_stress(E, slender)), "C1"
    p_cr = sigma_cr * A

    validity = [
        f"{regime} regime ({eq}): L_e/k = {slender:.4g}, (L_e/k)₁ = {s1:.4g} (C3).",
        "Straight, prismatic, centrally loaded column; no eccentricity or "
        "initial crookedness.",
        f"Effective-length factor K = {K:g} for this plane must be justified "
        "by the end conditions.",
    ]
    if P <= 0.0:
        n = math.inf
        validity.append("P <= 0 (tension or no load): buckling not possible, n = inf.")
    else:
        n = p_cr / P
    note = ResultNote(
        equation_ids=("C1", "C2", "C3") if eq == "C2" else ("C1", "C3"),
        validity_notes=tuple(validity),
        verify_flags=("C1 to C3 (SRC-SHIGLEY): verify edition and equation numbers.",),
    )
    return ColumnResult(k, slender, s1, regime, sigma_cr, p_cr, n, note)
