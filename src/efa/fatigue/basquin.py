"""Finite-life fatigue: Basquin relation with Morrow mean-stress correction
(equations B1, B2)."""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from efa._checks import FloatOrArray, as_float_array, require_positive, to_output
from efa.provenance import ResultNote, Status

RANGE_WARNING = "outside the stated data range"


@dataclass(frozen=True)
class BasquinConstants:
    """Basquin fatigue-strength constants with their valid life range.

    Attributes:
        sigma_f_prime: fatigue strength coefficient σ′_f [Pa], > 0.
        b: fatigue strength exponent [-], < 0.
        N_min, N_max: life range [cycles] covered by the source data.
        source_id: identifier of the data source.
        status: data status: cited, measured or assumed.
    """

    sigma_f_prime: float
    b: float
    N_min: float
    N_max: float
    source_id: str
    status: Status

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "sigma_f_prime", require_positive("sigma_f_prime", self.sigma_f_prime)
        )
        b = float(self.b)
        if not math.isfinite(b) or b >= 0.0:
            raise ValueError(f"b must be negative, got {self.b}.")
        object.__setattr__(self, "b", b)
        n_min = require_positive("N_min", self.N_min)
        n_max = require_positive("N_max", self.N_max)
        if n_min >= n_max:
            raise ValueError(f"N_min ({n_min}) must be less than N_max ({n_max}).")
        object.__setattr__(self, "N_min", n_min)
        object.__setattr__(self, "N_max", n_max)
        if not str(self.source_id).strip():
            raise ValueError("source_id must not be empty.")
        object.__setattr__(self, "status", Status(self.status))


@dataclass(frozen=True)
class LifeResult:
    """Result of ``life``: N_f [cycles] (float or array) and a ResultNote."""

    N_f: FloatOrArray
    note: ResultNote


@dataclass(frozen=True)
class StrengthResult:
    """Result of ``strength``: σ_a [Pa] (float or array) and a ResultNote."""

    sigma_a: FloatOrArray
    note: ResultNote


def _mean(sigma_m: ArrayLike, consts: BasquinConstants) -> np.ndarray:
    sm = as_float_array("sigma_m", sigma_m)
    if np.any(sm >= consts.sigma_f_prime):
        raise ValueError(
            "sigma_m must be less than sigma_f_prime "
            f"({consts.sigma_f_prime} Pa) for the Morrow correction."
        )
    return sm


def _note(
    ids: tuple[str, ...], consts: BasquinConstants, n_f: np.ndarray
) -> ResultNote:
    warnings = ()
    if np.any((n_f < consts.N_min) | (n_f > consts.N_max)):
        warnings = (
            f"N_f {RANGE_WARNING} [{consts.N_min:g}, {consts.N_max:g}] cycles; "
            "value kept but extrapolated.",
        )
    return ResultNote(
        equation_ids=ids,
        validity_notes=(
            "Basquin (B1) stress-life relation for fully reversed loading.",
            "Morrow mean-stress correction (B2): σ′_f replaced by σ′_f − σ_m.",
            "Constant amplitude, uniaxial stress; no cumulative damage.",
            f"Constants valid for {consts.N_min:g} to {consts.N_max:g} cycles.",
        ),
        verify_flags=("B2 Morrow (SRC-SHIGLEY): verify edition and equation numbers.",),
        input_statuses={f"Basquin constants ({consts.source_id})": consts.status},
        warnings=warnings,
    )


def life(
    sigma_a: ArrayLike, sigma_m: ArrayLike, consts: BasquinConstants
) -> LifeResult:
    """B1/B2: cycles to failure with Morrow mean-stress correction (verify).

    N_f = ½ (σ_a / (σ′_f − σ_m))^(1/b)   (B1 when σ_m = 0)

    Symbols:
        σ_a (sigma_a): stress amplitude [Pa], > 0.
        σ_m (sigma_m): mean stress [Pa], < σ′_f.
        σ′_f, b: Basquin constants [Pa], [-].
        N_f: cycles to failure [cycles]; 2N_f reversals.

    Validity: N_f within [N_min, N_max] of the constants; outside, the value
    is kept and a warning is added.
    Source: B1 definition; B2 SRC-SHIGLEY (verify).
    """
    sa = as_float_array("sigma_a", sigma_a)
    if np.any(sa <= 0.0):
        raise ValueError("sigma_a must be > 0.")
    sm = _mean(sigma_m, consts)
    n_f = 0.5 * (sa / (consts.sigma_f_prime - sm)) ** (1.0 / consts.b)
    ids = ("B1",) if np.all(sm == 0.0) else ("B1", "B2")
    return LifeResult(to_output(n_f), _note(ids, consts, np.atleast_1d(n_f)))


def strength(
    N_f: ArrayLike, sigma_m: ArrayLike, consts: BasquinConstants
) -> StrengthResult:
    """B1/B2: stress amplitude for a given life (verify).

    σ_a = (σ′_f − σ_m) (2 N_f)^b   (B1 when σ_m = 0)

    Symbols:
        N_f: cycles to failure [cycles], > 0.
        σ_m (sigma_m): mean stress [Pa], < σ′_f.
        σ′_f, b: Basquin constants [Pa], [-].
        σ_a: allowable stress amplitude [Pa].

    Validity: as for ``life``.
    Source: B1 definition; B2 SRC-SHIGLEY (verify).
    """
    n_f = as_float_array("N_f", N_f)
    if np.any(n_f <= 0.0):
        raise ValueError("N_f must be > 0.")
    sm = _mean(sigma_m, consts)
    sa = (consts.sigma_f_prime - sm) * (2.0 * n_f) ** consts.b
    ids = ("B1",) if np.all(sm == 0.0) else ("B1", "B2")
    return StrengthResult(to_output(sa), _note(ids, consts, np.atleast_1d(n_f)))
