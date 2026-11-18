"""Mean-stress criteria and fatigue safety factors (equations M1 to M5).

Sign convention: tensile stress positive. For σ_m <= 0 all fatigue criteria
use M5 (n = S_e / σ_a, decision D8); the Langer yield check (M4) is always
reported.
"""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from efa._checks import FloatOrArray, as_float_array, require_positive, to_output
from efa.provenance import ResultNote

LOCAL_YIELD_WARNING = (
    "local yielding at notch; mean-stress treatment needs review (verify)"
)


def _stresses(sigma_a: ArrayLike, sigma_m: ArrayLike):
    sa = as_float_array("sigma_a", sigma_a)
    if np.any(sa <= 0.0):
        raise ValueError("sigma_a must be > 0.")
    sm = as_float_array("sigma_m", sigma_m)
    sa, sm = np.broadcast_arrays(sa, sm)
    return sa, sm, sm > 0.0, np.where(sm > 0.0, sm, 1.0)


def _check_strengths(s_ut: float | None = None, s_y: float | None = None) -> None:
    if s_ut is not None and s_y is not None and s_y > s_ut:
        raise ValueError(f"S_y ({s_y} Pa) must not exceed S_ut ({s_ut} Pa).")


def goodman(
    sigma_a: ArrayLike, sigma_m: ArrayLike, s_e: float, s_ut: float
) -> FloatOrArray:
    """M1: modified Goodman safety factor n = 1 / (σ_a/S_e + σ_m/S_ut) (verify).

    For σ_m <= 0, M5 applies: n = S_e / σ_a.

    Symbols:
        σ_a (sigma_a): stress amplitude [Pa], > 0.
        σ_m (sigma_m): mean stress [Pa], tension positive.
        S_e (s_e): endurance limit [Pa].
        S_ut (s_ut): ultimate tensile strength [Pa].
        n: fatigue safety factor [-] on proportional load increase.

    Validity: infinite-life design, σ_m > 0; first-cycle yield checked
    separately with M4.
    Source: SRC-SHIGLEY (verify); M5 from decision D8.
    """
    s_e, s_ut = require_positive("S_e", s_e), require_positive("S_ut", s_ut)
    sa, sm, pos, sm_safe = _stresses(sigma_a, sigma_m)
    n = np.where(pos, 1.0 / (sa / s_e + sm_safe / s_ut), s_e / sa)
    return to_output(n)


def gerber(
    sigma_a: ArrayLike, sigma_m: ArrayLike, s_e: float, s_ut: float
) -> FloatOrArray:
    """M2: Gerber safety factor (verify).

    n = ½ (S_ut/σ_m)² (σ_a/S_e) [−1 + √(1 + (2 σ_m S_e / (S_ut σ_a))²)]

    For σ_m <= 0, M5 applies: n = S_e / σ_a.

    Symbols:
        σ_a (sigma_a): stress amplitude [Pa], > 0.
        σ_m (sigma_m): mean stress [Pa], tension positive.
        S_e (s_e): endurance limit [Pa].
        S_ut (s_ut): ultimate tensile strength [Pa].
        n: fatigue safety factor [-] on proportional load increase.

    Validity: infinite-life design, σ_m > 0; ductile materials.
    Source: SRC-SHIGLEY (verify); M5 from decision D8.
    """
    s_e, s_ut = require_positive("S_e", s_e), require_positive("S_ut", s_ut)
    sa, sm, pos, sm_safe = _stresses(sigma_a, sigma_m)
    ratio = 2.0 * sm_safe * s_e / (s_ut * sa)
    n_pos = 0.5 * (s_ut / sm_safe) ** 2 * (sa / s_e) * (-1.0 + np.sqrt(1.0 + ratio**2))
    return to_output(np.where(pos, n_pos, s_e / sa))


def elliptic(
    sigma_a: ArrayLike, sigma_m: ArrayLike, s_e: float, s_y: float
) -> FloatOrArray:
    """M3: ASME elliptic safety factor n = √(1 / ((σ_a/S_e)² + (σ_m/S_y)²)) (verify).

    For σ_m <= 0, M5 applies: n = S_e / σ_a.

    Symbols:
        σ_a (sigma_a): stress amplitude [Pa], > 0.
        σ_m (sigma_m): mean stress [Pa], tension positive.
        S_e (s_e): endurance limit [Pa].
        S_y (s_y): yield strength [Pa].
        n: fatigue safety factor [-] on proportional load increase.

    Validity: infinite-life design, σ_m > 0.
    Source: SRC-SHIGLEY (verify); M5 from decision D8.
    """
    s_e, s_y = require_positive("S_e", s_e), require_positive("S_y", s_y)
    sa, sm, pos, sm_safe = _stresses(sigma_a, sigma_m)
    n_pos = np.sqrt(1.0 / ((sa / s_e) ** 2 + (sm_safe / s_y) ** 2))
    return to_output(np.where(pos, n_pos, s_e / sa))


def langer(sigma_a: ArrayLike, sigma_m: ArrayLike, s_y: float) -> FloatOrArray:
    """M4: Langer first-cycle yield safety factor n_y = S_y / (σ_a + |σ_m|) (verify).

    Symbols:
        σ_a (sigma_a): stress amplitude [Pa], > 0.
        σ_m (sigma_m): mean stress [Pa].
        S_y (s_y): yield strength [Pa].
        n_y: yield safety factor [-].

    Validity: tension and compression yield strengths taken equal.
    Source: SRC-SHIGLEY (verify).
    """
    s_y = require_positive("S_y", s_y)
    sa, sm, _, _ = _stresses(sigma_a, sigma_m)
    return to_output(s_y / (sa + np.abs(sm)))


@dataclass(frozen=True)
class MeanStressResult:
    """Safety factors for one stress state.

    Attributes:
        sigma_a, sigma_m: notched amplitude and mean stress used [Pa].
        n_goodman, n_gerber, n_elliptic: fatigue safety factors [-].
        n_yield: Langer first-cycle yield safety factor [-].
        regime: "tensile_mean" (M1 to M3) or "compressive_or_zero_mean" (M5).
        note: equations, validity, warnings and verify flags.
    """

    sigma_a: float
    sigma_m: float
    n_goodman: float
    n_gerber: float
    n_elliptic: float
    n_yield: float
    regime: str
    note: ResultNote


def assess(
    sigma_a: float,
    sigma_m: float,
    S_e: float,
    S_ut: float,
    S_y: float,
    K_f: float | None = None,
    sigma_max: float | None = None,
) -> MeanStressResult:
    """Evaluate M1 to M5 for one notched stress state.

    Args:
        sigma_a: notched stress amplitude K_f σ_a,nom [Pa], > 0.
        sigma_m: notched mean stress K_f σ_m,nom [Pa] (decision D9).
        S_e: endurance limit [Pa].
        S_ut: ultimate tensile strength [Pa].
        S_y: yield strength [Pa], <= S_ut.
        K_f: fatigue stress-concentration factor [-], for the local-yield check.
        sigma_max: largest absolute nominal stress of the cycle [Pa], for the
            local-yield check K_f |σ_max| > S_y.

    Returns:
        MeanStressResult with all criteria and a ResultNote.
    """
    S_e = require_positive("S_e", S_e)
    S_ut = require_positive("S_ut", S_ut)
    S_y = require_positive("S_y", S_y)
    _check_strengths(S_ut, S_y)
    sa, sm = float(sigma_a), float(sigma_m)
    if not (math.isfinite(sa) and math.isfinite(sm)):
        raise ValueError("sigma_a and sigma_m must be finite.")

    tensile = sm > 0.0
    regime = "tensile_mean" if tensile else "compressive_or_zero_mean"
    ids = ("M1", "M2", "M3", "M4") if tensile else ("M5", "M4")
    validity = [
        "Infinite-life criteria on notched stresses (K_f applied to σ_a and σ_m, "
        "decision D9).",
        "Safety factors assume proportional load increase.",
    ]
    if tensile:
        validity.append("σ_m > 0: Goodman (M1), Gerber (M2), ASME elliptic (M3).")
    else:
        validity.append("σ_m <= 0: n = S_e / σ_a for all criteria (M5, decision D8).")
    validity.append("Langer first-cycle yield (M4) always reported.")

    warnings: list[str] = []
    if K_f is not None and sigma_max is not None:
        k_f = float(K_f)
        if not math.isfinite(k_f) or k_f < 1.0:
            raise ValueError(f"K_f must be >= 1, got {K_f}.")
        if k_f * abs(float(sigma_max)) > S_y:
            warnings.append(LOCAL_YIELD_WARNING)
    else:
        validity.append("Local-yield check not performed (K_f or sigma_max not given).")

    n_y = float(langer(sa, sm, S_y))
    if n_y < 1.0:
        warnings.append("Langer n_y < 1: yielding is predicted in the first cycle.")

    note = ResultNote(
        equation_ids=ids,
        validity_notes=tuple(validity),
        verify_flags=("M1 to M4 (SRC-SHIGLEY): verify edition and equation numbers.",),
        warnings=tuple(warnings),
    )
    return MeanStressResult(
        sigma_a=sa,
        sigma_m=sm,
        n_goodman=float(goodman(sa, sm, S_e, S_ut)),
        n_gerber=float(gerber(sa, sm, S_e, S_ut)),
        n_elliptic=float(elliptic(sa, sm, S_e, S_y)),
        n_yield=n_y,
        regime=regime,
        note=note,
    )


def haigh_curves(
    S_e: float, S_ut: float, S_y: float, n_points: int = 101
) -> dict[str, tuple[NDArray[np.float64], NDArray[np.float64]]]:
    """Failure lines (n = 1) of M1 to M5 in the Haigh (σ_m, σ_a) diagram.

    Returns a mapping from curve name to (σ_m [Pa], σ_a [Pa]) arrays:
        "Goodman": σ_a = S_e (1 − σ_m/S_ut), 0 <= σ_m <= S_ut
        "Gerber": σ_a = S_e (1 − (σ_m/S_ut)²), 0 <= σ_m <= S_ut
        "ASME elliptic": σ_a = S_e √(1 − (σ_m/S_y)²), 0 <= σ_m <= S_y
        "Langer": σ_a = S_y − |σ_m|, −S_y <= σ_m <= S_y
        "Compressive mean (M5)": σ_a = S_e, −S_y <= σ_m <= 0
    Source: rearranged M1 to M5 with n = 1.
    """
    S_e = require_positive("S_e", S_e)
    S_ut = require_positive("S_ut", S_ut)
    S_y = require_positive("S_y", S_y)
    _check_strengths(S_ut, S_y)
    m_ut = np.linspace(0.0, S_ut, n_points)
    m_y = np.linspace(0.0, S_y, n_points)
    m_l = np.linspace(-S_y, S_y, 2 * n_points - 1)
    m_c = np.array([-S_y, 0.0])
    return {
        "Goodman": (m_ut, S_e * (1.0 - m_ut / S_ut)),
        "Gerber": (m_ut, S_e * (1.0 - (m_ut / S_ut) ** 2)),
        "ASME elliptic": (m_y, S_e * np.sqrt(np.clip(1.0 - (m_y / S_y) ** 2, 0, None))),
        "Langer": (m_l, S_y - np.abs(m_l)),
        "Compressive mean (M5)": (m_c, np.array([S_e, S_e])),
    }
