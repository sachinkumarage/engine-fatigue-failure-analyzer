"""Shared building blocks for component assessments.

A location assessment follows the Phase 4 procedure: notched stress histories
→ S2 (separately for σ and τ) → S3 if combined → ``mean_stress.assess`` →
Basquin/Morrow life (B2) only when n_Goodman < 1.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from efa._checks import as_float_array, require_positive
from efa.fatigue.basquin import BasquinConstants, LifeResult, life
from efa.fatigue.marin import EnduranceLimit
from efa.fatigue.mean_stress import MeanStressResult, assess
from efa.loads.cycle import CycleResult
from efa.provenance import ResultNote, Status
from efa.stress.nominal import amplitude_and_mean_from_history, von_mises
from efa.stress.notch import fatigue_notch_factor, notch_sensitivity

NO_FINITE_LIFE = "no finite-life calculation (n ≥ 1)"


@dataclass(frozen=True)
class Material:
    """Static strength data of a component material.

    Attributes:
        name: material designation or description.
        S_ut: ultimate tensile strength [Pa].
        S_y: yield strength [Pa], <= S_ut.
        status: data status of the strengths.
        source_id: source of the data, or "" if none.
        E: Young's modulus [Pa], needed for buckling only.
    """

    name: str
    S_ut: float
    S_y: float
    status: Status
    source_id: str = ""
    E: float | None = None

    def __post_init__(self) -> None:
        s_ut = require_positive("S_ut", self.S_ut)
        s_y = require_positive("S_y", self.S_y)
        if s_y > s_ut:
            raise ValueError(f"S_y ({s_y} Pa) must not exceed S_ut ({s_ut} Pa).")
        object.__setattr__(self, "S_ut", s_ut)
        object.__setattr__(self, "S_y", s_y)
        object.__setattr__(self, "status", Status(self.status))
        if self.E is not None:
            object.__setattr__(self, "E", require_positive("E", self.E))


def notch_factor(
    k_t: float, rho: float | None, sqrt_a: float | None, q: float | None
) -> tuple[float, float | None]:
    """K_f from K_t with q entered directly or from N2 (Neuber).

    Returns:
        (K_f, q); q is None when K_t = 1 and no q is needed.
    """
    if k_t == 1.0 and q is None and sqrt_a is None:
        return 1.0, None
    if q is None:
        if sqrt_a is None or rho is None:
            raise ValueError("K_t > 1 needs either q or both sqrt_a and rho.")
        q = notch_sensitivity(sqrt_a, rho)
    return fatigue_notch_factor(k_t, q), q


@dataclass(frozen=True)
class LocationResult:
    """Fatigue assessment of one location (SI units).

    Attributes:
        name: location name.
        sigma_a, sigma_m: notched normal-stress amplitude and mean [Pa].
        tau_a, tau_m: notched shear-stress amplitude and mean [Pa]; 0 if none.
        sigma_eq_a, sigma_eq_m: amplitude and mean used for the criteria [Pa]
            (von Mises S3 if combined, otherwise σ_a and σ_m).
        combined: True if shear stress is present (S3 applied).
        S_e: endurance limit used [Pa].
        assessment: mean-stress result (M1 to M5).
        life: Basquin/Morrow result, or None when n_Goodman >= 1.
        note: equations, validity, warnings.
    """

    name: str
    sigma_a: float
    sigma_m: float
    tau_a: float
    tau_m: float
    sigma_eq_a: float
    sigma_eq_m: float
    combined: bool
    S_e: float
    assessment: MeanStressResult
    life: LifeResult | None
    note: ResultNote


def assess_location(
    name: str,
    sigma_history: ArrayLike,
    tau_history: ArrayLike | None,
    endurance: EnduranceLimit,
    material: Material,
    basquin: BasquinConstants | None,
) -> LocationResult:
    """Fatigue assessment of one location from notched stress histories.

    Args:
        name: location name.
        sigma_history: notched normal stress over the cycle [Pa].
        tau_history: notched shear stress over the cycle [Pa], or None.
        endurance: endurance limit for this location (F1).
        material: S_ut and S_y.
        basquin: constants for B2 when n_Goodman < 1, or None.
    """
    sig = np.atleast_1d(as_float_array("sigma_history", sigma_history))
    sigma_a, sigma_m = amplitude_and_mean_from_history(sig)
    tau_a = tau_m = 0.0
    combined = tau_history is not None
    if combined:
        tau = np.atleast_1d(as_float_array("tau_history", tau_history))
        tau_a, tau_m = amplitude_and_mean_from_history(tau)
        eq_a, eq_m = float(von_mises(sigma_a, tau_a)), float(von_mises(sigma_m, tau_m))
    else:
        eq_a, eq_m = sigma_a, sigma_m
    if eq_a <= 0.0:
        raise ValueError(f"{name}: no alternating stress over the cycle.")

    res = assess(
        eq_a,
        eq_m,
        endurance.S_e,
        material.S_ut,
        material.S_y,
        K_f=1.0,
        sigma_max=eq_a + abs(eq_m),
    )
    ids = ["S2", *(["S3"] if combined else []), *res.note.equation_ids]
    validity = [
        "Notched histories (K_f on amplitude and mean, D9); S2 applied "
        "separately to σ and τ.",
    ]
    if combined:
        validity.append(
            "S3 von Mises applied separately to amplitudes and means; σ and τ "
            "extrema taken independently (non-proportional loading not modelled)."
        )
    validity.append(
        "Local-yield check on the notched stresses: σ′_a + |σ′_m| compared with S_y."
    )
    warnings = list(res.note.warnings)
    verify = list(res.note.verify_flags)
    life_res = None
    if res.n_goodman < 1.0:
        if basquin is None:
            warnings.append(
                "n_Goodman < 1 but no Basquin constants given: life not computed."
            )
        else:
            try:
                life_res = life(eq_a, eq_m, basquin)
            except ValueError as exc:
                warnings.append(f"Finite life not computed: {exc}")
            else:
                ids += [i for i in life_res.note.equation_ids if i not in ids]
                warnings += life_res.note.warnings
                verify += life_res.note.verify_flags
    else:
        validity.append(NO_FINITE_LIFE + ".")
    note = ResultNote(
        equation_ids=tuple(ids),
        validity_notes=tuple(validity) + res.note.validity_notes,
        verify_flags=tuple(dict.fromkeys(verify)),
        warnings=tuple(warnings),
    )
    return LocationResult(
        name, sigma_a, sigma_m, tau_a, tau_m, eq_a, eq_m, combined,
        endurance.S_e, res, life_res, note,
    )  # fmt: skip


def check_cycle_grid(cycle: CycleResult) -> tuple[str, ...]:
    """Validity note if the cycle is not the full 0..719 integer-degree grid."""
    if cycle.theta_deg.size == 720 and np.array_equal(cycle.theta_deg, np.arange(720)):
        return ()
    return (
        "Cycle is not the 0..719 integer-degree grid of evaluate_cycle; "
        "load extremes between grid points may be missed.",
    )


def governing(items: Iterable[tuple[str, float]]) -> tuple[str, float]:
    """Return the (name, n) pair with the lowest safety factor."""
    items = list(items)
    if not items:
        raise ValueError("No items to compare.")
    return min(items, key=lambda it: it[1])


def merge_notes(
    ids: Sequence[str],
    validity: Sequence[str],
    notes: Iterable[tuple[str, ResultNote]],
    statuses: dict[str, Status],
    extra_verify: Sequence[str] = (),
) -> ResultNote:
    """Combine sub-results' notes into one component note."""
    all_ids = list(ids)
    verify = list(extra_verify)
    warnings: list[str] = []
    for label, note in notes:
        all_ids += [i for i in note.equation_ids if i not in all_ids]
        verify += note.verify_flags
        warnings += [f"{label}: {w}" for w in note.warnings]
    return ResultNote(
        equation_ids=tuple(all_ids),
        validity_notes=tuple(validity),
        verify_flags=tuple(dict.fromkeys(verify)),
        input_statuses=statuses,
        warnings=tuple(warnings),
    )


def fmt(value: float, digits: int = 6) -> str:
    """Format a number for Markdown tables."""
    if value is None:
        return "—"
    if isinstance(value, float) and math.isinf(value):
        return "inf"
    return f"{value:.{digits}g}"


def markdown_table(header: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    """A GitHub-flavoured Markdown table."""
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def report(
    title: str,
    inputs: Sequence[Sequence[object]],
    results: str,
    note: ResultNote,
) -> str:
    """Markdown report: inputs with status, equations, results and warnings."""
    parts = [
        f"# {title}",
        "## Inputs",
        markdown_table(("Input", "Value", "Unit", "Status", "Source"), inputs),
        "## Equations used",
        ", ".join(note.equation_ids),
        "## Results",
        results,
        "## Warnings",
        "\n".join(f"- {w}" for w in note.warnings) or "None.",
        "## Validity and verification",
        "\n".join(f"- {v}" for v in (*note.validity_notes, *note.verify_flags)),
    ]
    return "\n\n".join(parts) + "\n"


def endurance_inputs(
    label: str, endurance: EnduranceLimit
) -> list[tuple[str, str, str, str, str]]:
    """Input rows for S_e′ and the Marin factors of one endurance limit."""
    s = endurance.S_e_prime
    rows = [(f"{label} S_e′", fmt(s.value / 1e6), "MPa", s.status.value, s.source_id)]
    rows += [
        (f"{label} {n}", fmt(f.value), "-", f.status.value, f.source_id)
        for n, f in endurance.factors.items()
    ]
    return rows


def as_array(values: ArrayLike) -> NDArray[np.float64]:
    """Read-only float array."""
    arr = np.array(values, dtype=float)
    arr.setflags(write=False)
    return arr
