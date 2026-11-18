"""Internal helpers for input validation and array/float output."""

import math

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatOrArray = float | NDArray[np.float64]


def require_positive(name: str, value: float) -> float:
    """Return ``value`` as float, or raise ValueError if not finite and > 0."""
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number, got {value!r}.") from exc
    if not math.isfinite(v) or v <= 0.0:
        raise ValueError(f"{name} must be a finite positive number, got {value!r}.")
    return v


def as_float_array(name: str, value: ArrayLike) -> NDArray[np.float64]:
    """Convert to a float array, or raise ValueError if any entry is not finite."""
    arr = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite values.")
    return arr


def to_output(arr: NDArray[np.float64]) -> FloatOrArray:
    """Return a Python float for 0-d results and an array otherwise."""
    arr = np.asarray(arr, dtype=float)
    return float(arr) if arr.ndim == 0 else arr
