"""Notch effects: fatigue stress-concentration factor (N1, N2)."""

import math

import numpy as np
from numpy.typing import ArrayLike

from efa._checks import FloatOrArray, as_float_array, require_positive, to_output


def fatigue_notch_factor(k_t: float, q: float) -> float:
    """N1: fatigue stress-concentration factor K_f = 1 + q (K_t − 1).

    Symbols:
        K_t (k_t): theoretical (elastic) stress-concentration factor [-], >= 1.
        q: notch sensitivity [-], 0 <= q <= 1.
        K_f: fatigue stress-concentration factor [-], 1 <= K_f <= K_t.

    Validity: K_t from a chart or analysis for the same geometry and loading
    mode; high-cycle fatigue.
    Source: definition of q.
    """
    k_t = float(k_t)
    q = float(q)
    if not math.isfinite(k_t) or k_t < 1.0:
        raise ValueError(f"K_t must be >= 1, got {k_t}.")
    if not math.isfinite(q) or not 0.0 <= q <= 1.0:
        raise ValueError(f"q must lie in [0, 1], got {q}.")
    return 1.0 + q * (k_t - 1.0)


def notch_sensitivity(sqrt_a: float, rho: float) -> float:
    """N2: Neuber notch sensitivity q = 1 / (1 + √a / √ρ) (verify).

    Symbols:
        √a (sqrt_a): Neuber constant of the material [m^0.5], from a cited
            source for the material and loading mode.
        ρ (rho): notch root radius [m].
        q: notch sensitivity [-], 0 < q < 1.

    Validity: steels and aluminium alloys within the range of the source
    data for √a; q may instead be entered directly.
    Source: SRC-SHIGLEY (verify).
    """
    sqrt_a = require_positive("sqrt_a", sqrt_a)
    rho = require_positive("rho", rho)
    return 1.0 / (1.0 + sqrt_a / math.sqrt(rho))


def notched_stresses(
    sigma_a: ArrayLike, sigma_m: ArrayLike, k_f: float
) -> tuple[FloatOrArray, FloatOrArray]:
    """Apply K_f to amplitude and mean: σ_a,notch = K_f σ_a; σ_m,notch = K_f σ_m.

    Symbols:
        σ_a, σ_m (sigma_a, sigma_m): nominal amplitude and mean stress [Pa].
        K_f (k_f): fatigue stress-concentration factor [-], >= 1.

    Validity: decision D9 (K_f applied to the mean stress as well); local
    yielding at the notch is checked in efa.fatigue.mean_stress.assess.
    Source: project decision D9 (docs/decisions/0002-phase-3.md).
    """
    k_f = float(k_f)
    if not math.isfinite(k_f) or k_f < 1.0:
        raise ValueError(f"K_f must be >= 1, got {k_f}.")
    sa = as_float_array("sigma_a", sigma_a)
    if np.any(sa < 0.0):
        raise ValueError("sigma_a must be >= 0.")
    return to_output(k_f * sa), to_output(k_f * as_float_array("sigma_m", sigma_m))
