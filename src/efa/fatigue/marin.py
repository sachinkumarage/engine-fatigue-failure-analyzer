"""Endurance limit with Marin factors (equations F1 to F6).

Every factor is a ``MarinFactor`` that carries its value, basis, status,
source id and verify flag, so the endurance limit can be traced.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from efa._checks import require_positive
from efa.provenance import ResultNote, Status, TracedValue
from efa.sources import SRC_SHIGLEY

Loading = Literal["bending", "axial", "torsion"]
FACTOR_NAMES = ("k_a", "k_b", "k_c", "k_d", "k_e", "k_f")
PA_PER_MPA = 1.0e6


@dataclass(frozen=True)
class MarinFactor(TracedValue):
    """A Marin modifying factor [-] with its basis and provenance.

    Attributes:
        value: Factor value [-], > 0.
        basis: How the value was obtained (equation id, table, test).
        status: Data status: cited, measured or assumed.
        source_id: Identifier of the source (docs/sources.md), or "".
        verify: True while the relation or value awaits owner checking.
    """

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.value <= 0.0:
            raise ValueError(f"A Marin factor must be > 0, got {self.value}.")


def surface_factor(
    s_ut: float,
    a: float,
    b: float,
    *,
    status: Status = Status.CITED,
    source_id: str = SRC_SHIGLEY,
    verify: bool = True,
) -> MarinFactor:
    """F2: surface factor k_a = a (S_ut / 1 MPa)^b (verify).

    Symbols:
        S_ut (s_ut): ultimate tensile strength [Pa]; converted to MPa here.
        a: surface-finish coefficient on the MPa basis [-], from a cited table.
        b: surface-finish exponent [-], from the same table.
        k_a: surface factor [-].

    Validity: steels; a and b must be the MPa-basis values for the actual
    surface finish.
    Source: SRC-SHIGLEY (verify).
    """
    s_ut = require_positive("S_ut", s_ut)
    a = require_positive("a", a)
    b = float(b)
    if not math.isfinite(b):
        raise ValueError("b must be finite.")
    value = a * (s_ut / PA_PER_MPA) ** b
    basis = f"F2: k_a = {a:g} (S_ut/MPa)^{b:g}, S_ut = {s_ut / PA_PER_MPA:g} MPa"
    return MarinFactor(value, basis, status, source_id, verify)


def size_factor(d: float, loading: Loading) -> MarinFactor:
    """F3: size factor for a round section (verify).

    k_b = 1.24 d^−0.107   for 2.79 <= d <= 51 mm
    k_b = 1.51 d^−0.157   for 51 < d <= 254 mm
    k_b = 1               for axial loading

    Symbols:
        d: diameter of the round section [m]; converted to mm here.
        loading: "bending", "torsion" or "axial".
        k_b: size factor [-].

    Validity: rotating round sections in bending or torsion,
    2.79 mm <= d <= 254 mm; raises ValueError outside this range.
    Non-round or non-rotating sections need an equivalent diameter.
    Source: SRC-SHIGLEY (verify).
    """
    _check_loading(loading)
    d = require_positive("d", d)
    if loading == "axial":
        return MarinFactor(1.0, "F3: k_b = 1 (axial loading)", Status.CITED,
                           SRC_SHIGLEY, True)  # fmt: skip
    d_mm = d * 1.0e3
    if 2.79 <= d_mm <= 51.0:
        value = 1.24 * d_mm**-0.107
        basis = f"F3: k_b = 1.24 d^-0.107, d = {d_mm:g} mm ({loading})"
    elif 51.0 < d_mm <= 254.0:
        value = 1.51 * d_mm**-0.157
        basis = f"F3: k_b = 1.51 d^-0.157, d = {d_mm:g} mm ({loading})"
    else:
        raise ValueError(
            f"F3 size factor is valid for 2.79 mm <= d <= 254 mm, got {d_mm:g} mm."
        )
    return MarinFactor(value, basis, Status.CITED, SRC_SHIGLEY, True)


LOAD_FACTORS = {"bending": 1.0, "axial": 0.85, "torsion": 0.59}


def load_factor(loading: Loading) -> MarinFactor:
    """F4: load factor k_c = 1 (bending), 0.85 (axial), 0.59 (torsion) (verify).

    Symbols:
        loading: "bending", "axial" or "torsion".
        k_c: load factor [-].

    Validity: use k_c = 1 when torsion is combined with bending through the
    von Mises equivalent stress (S3).
    Source: SRC-SHIGLEY (verify).
    """
    _check_loading(loading)
    value = LOAD_FACTORS[loading]
    return MarinFactor(value, f"F4: k_c = {value:g} ({loading})", Status.CITED,
                       SRC_SHIGLEY, True)  # fmt: skip


def reliability_factor(z_a: float) -> MarinFactor:
    """F5: reliability factor k_e = 1 − 0.08 z_a (verify).

    Symbols:
        z_a: standard normal variate for the required reliability [-], >= 0
            (e.g. 2.326 for 99 %).
        k_e: reliability factor [-].

    Validity: assumes an 8 % standard deviation of the endurance limit;
    0 <= z_a < 12.5.
    Source: SRC-SHIGLEY (verify).
    """
    z_a = float(z_a)
    if not math.isfinite(z_a) or not 0.0 <= z_a < 12.5:
        raise ValueError(f"z_a must lie in [0, 12.5), got {z_a}.")
    value = 1.0 - 0.08 * z_a
    return MarinFactor(value, f"F5: k_e = 1 - 0.08 z_a, z_a = {z_a:g}",
                       Status.CITED, SRC_SHIGLEY, True)  # fmt: skip


def steel_endurance_estimate(s_ut: float) -> TracedValue:
    """F6: rotating-beam endurance limit estimate for steels (verify).

    S_e′ = 0.5 S_ut   for S_ut <= 1400 MPa
    S_e′ = 700 MPa    for S_ut > 1400 MPa

    Symbols:
        S_ut (s_ut): ultimate tensile strength [Pa].
        S_e′: rotating-beam endurance limit estimate [Pa].

    Validity: wrought steels only; an estimate, not test data.
    Status: cited (verify).
    Source: SRC-SHIGLEY (verify).
    """
    s_ut = require_positive("S_ut", s_ut)
    if s_ut <= 1400.0 * PA_PER_MPA:
        value, basis = 0.5 * s_ut, "F6: S_e' = 0.5 S_ut (steel estimate)"
    else:
        value, basis = 700.0 * PA_PER_MPA, "F6: S_e' = 700 MPa (steel estimate)"
    return TracedValue(value, basis, Status.CITED, SRC_SHIGLEY, True)


@dataclass(frozen=True)
class EnduranceLimit:
    """Result of F1.

    Attributes:
        S_e: modified endurance limit [Pa].
        S_e_prime: unmodified endurance limit used [Pa].
        factors: the six Marin factors used, keyed k_a to k_f.
        note: equations, factor bases, statuses and verify flags.
    """

    S_e: float
    S_e_prime: TracedValue
    factors: dict[str, MarinFactor]
    note: ResultNote


def endurance_limit(
    S_e_prime: TracedValue, factors: Mapping[str, MarinFactor]
) -> EnduranceLimit:
    """F1: modified endurance limit S_e = k_a k_b k_c k_d k_e k_f S_e′.

    Symbols:
        S_e′ (S_e_prime): unmodified (rotating-beam) endurance limit [Pa].
        k_a .. k_f: surface, size, load, temperature, reliability and
            miscellaneous factors [-]; k_f is used for cited surface-treatment
            factors only.
        S_e: modified endurance limit [Pa].

    Validity: high-cycle fatigue of the specimen-to-part correlation basis of
    the factors. All six factors must be given explicitly.
    Source: SRC-SHIGLEY (verify).
    """
    if not isinstance(S_e_prime, TracedValue):
        raise ValueError("S_e_prime must be a TracedValue with basis and status.")
    require_positive("S_e_prime", S_e_prime.value)
    missing = [n for n in FACTOR_NAMES if n not in factors]
    extra = [n for n in factors if n not in FACTOR_NAMES]
    if missing or extra:
        raise ValueError(
            f"factors must have exactly the keys {FACTOR_NAMES}; "
            f"missing {missing}, unexpected {extra}."
        )
    for name in FACTOR_NAMES:
        if not isinstance(factors[name], MarinFactor):
            raise ValueError(f"{name} must be a MarinFactor.")
    ordered = {n: factors[n] for n in FACTOR_NAMES}
    s_e = S_e_prime.value * math.prod(f.value for f in ordered.values())

    validity = [f"S_e' = {S_e_prime.value / PA_PER_MPA:g} MPa: {S_e_prime.basis}"]
    validity += [f"{n} = {f.value:.6g}: {f.basis}" for n, f in ordered.items()]
    validity.append("F1 product of Marin factors (SRC-SHIGLEY, verify).")
    verify = ["F1 (SRC-SHIGLEY): verify edition and equation numbers."]
    verify += [
        f"{n} ({f.source_id or 'no source'}): verify value and basis."
        for n, f in ordered.items()
        if f.verify
    ]
    if S_e_prime.verify:
        verify.append(f"S_e' ({S_e_prime.source_id or 'no source'}): verify.")
    statuses = {"S_e'": S_e_prime.status}
    statuses.update({n: f.status for n, f in ordered.items()})
    ids = ["F1"] + sorted({f.basis.split(":")[0] for f in ordered.values()
                           if f.basis.startswith("F")})  # fmt: skip
    if S_e_prime.basis.startswith("F6"):
        ids.append("F6")
    note = ResultNote(
        equation_ids=tuple(ids),
        validity_notes=tuple(validity),
        verify_flags=tuple(verify),
        input_statuses=statuses,
    )
    return EnduranceLimit(s_e, S_e_prime, ordered, note)


def _check_loading(loading: str) -> None:
    if loading not in LOAD_FACTORS:
        raise ValueError(
            f"loading must be one of {tuple(LOAD_FACTORS)}, got {loading!r}."
        )
