"""Nominal stresses, amplitude and mean, and von Mises equivalent (S1 to S3)."""

import numpy as np
from numpy.typing import ArrayLike

from efa._checks import FloatOrArray, as_float_array, to_output


def _positive_array(name: str, value: ArrayLike) -> np.ndarray:
    arr = as_float_array(name, value)
    if np.any(arr <= 0.0):
        raise ValueError(f"{name} must be positive.")
    return arr


def axial_stress(force: ArrayLike, area: ArrayLike) -> FloatOrArray:
    """S1: axial stress σ = F / A.

    Symbols:
        F (force): axial force, tension positive [N].
        A (area): cross-section area [m²].
        σ: normal stress, tension positive [Pa].

    Validity: uniform stress over the section, away from load introduction.
    Source: definition.
    """
    return to_output(as_float_array("force", force) / _positive_array("area", area))


def bending_stress(moment: ArrayLike, c: ArrayLike, inertia: ArrayLike) -> FloatOrArray:
    """S1: bending stress σ_b = M c / I.

    Symbols:
        M (moment): bending moment [N·m].
        c: distance from the neutral axis to the fibre considered [m].
        I (inertia): second moment of area about the neutral axis [m⁴].
        σ_b: bending stress [Pa].

    Validity: linear-elastic straight beam, plane sections remain plane.
    Source: definition (elementary beam theory).
    """
    m = as_float_array("moment", moment)
    return to_output(m * as_float_array("c", c) / _positive_array("inertia", inertia))


def torsional_stress(torque: ArrayLike, rho: ArrayLike, j: ArrayLike) -> FloatOrArray:
    """S1: torsional shear stress τ = T ρ / J.

    Symbols:
        T (torque): torque [N·m].
        ρ (rho): radial distance from the shaft axis [m].
        J (j): polar second moment of area [m⁴].
        τ: shear stress [Pa].

    Validity: linear-elastic circular (solid or hollow) shaft.
    Source: definition (elementary torsion theory).
    """
    t = as_float_array("torque", torque)
    return to_output(t * as_float_array("rho", rho) / _positive_array("j", j))


def amplitude_and_mean(
    sigma_max: ArrayLike, sigma_min: ArrayLike
) -> tuple[FloatOrArray, FloatOrArray]:
    """S2: stress amplitude and mean from the extremes of a cycle.

    σ_a = (σ_max − σ_min) / 2;   σ_m = (σ_max + σ_min) / 2

    Symbols:
        σ_max, σ_min: maximum and minimum stress of the cycle [Pa].
        σ_a: stress amplitude [Pa], >= 0.
        σ_m: mean stress [Pa].

    Validity: constant-amplitude cycle; σ_max >= σ_min.
    Source: definition.
    """
    hi = as_float_array("sigma_max", sigma_max)
    lo = as_float_array("sigma_min", sigma_min)
    if np.any(hi < lo):
        raise ValueError("sigma_max must not be less than sigma_min.")
    return to_output((hi - lo) / 2.0), to_output((hi + lo) / 2.0)


def amplitude_and_mean_from_history(history: ArrayLike) -> tuple[float, float]:
    """S2: amplitude and mean from a stress history, using its max and min.

    Symbols:
        history: stress values over one load cycle [Pa].

    Validity: the history is one constant-amplitude cycle; intermediate
    reversals are ignored (no cycle counting).
    Source: definition.
    """
    h = np.atleast_1d(as_float_array("history", history))
    if h.size == 0:
        raise ValueError("history must not be empty.")
    sa, sm = amplitude_and_mean(float(np.max(h)), float(np.min(h)))
    return float(sa), float(sm)


def von_mises(sigma: ArrayLike, tau: ArrayLike) -> FloatOrArray:
    """S3: von Mises equivalent stress σ′ = √(σ² + 3τ²).

    Symbols:
        σ (sigma): normal stress [Pa].
        τ (tau): shear stress on the same plane [Pa].
        σ′: equivalent stress [Pa], >= 0.

    Validity: one normal and one shear stress component. Applied separately to
    amplitudes and to means, which assumes proportional (in-phase) loading.
    Source: definition (distortion-energy criterion).
    """
    s = as_float_array("sigma", sigma)
    t = as_float_array("tau", tau)
    return to_output(np.sqrt(s**2 + 3.0 * t**2))


def peak_abs_stress(sigma_a: ArrayLike, sigma_m: ArrayLike) -> FloatOrArray:
    """Largest absolute stress of a cycle, max(|σ_m + σ_a|, |σ_m − σ_a|).

    Symbols:
        σ_a (sigma_a): stress amplitude [Pa], >= 0.
        σ_m (sigma_m): mean stress [Pa].

    Source: follows from S2.
    """
    sa = as_float_array("sigma_a", sigma_a)
    sm = as_float_array("sigma_m", sigma_m)
    return to_output(np.maximum(np.abs(sm + sa), np.abs(sm - sa)))
