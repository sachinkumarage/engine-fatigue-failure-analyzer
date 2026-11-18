"""Connecting-rod assessment: axial fatigue per section and buckling (R1)."""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from efa._checks import FloatOrArray, as_float_array, require_positive
from efa.buckling import ColumnResult, column_check
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
    notch_factor,
    report,
)
from efa.fatigue.basquin import BasquinConstants
from efa.fatigue.marin import EnduranceLimit
from efa.loads.cycle import CycleResult
from efa.provenance import ResultNote, Status
from efa.stress.nominal import axial_stress

MPA = 1.0e6


def rod_axial_stress(f_rod: ArrayLike, area: float) -> FloatOrArray:
    """R1: rod axial stress σ(θ) = −F_rod(θ) / A_s.

    Symbols:
        F_rod (f_rod): rod axial force, compression positive [N].
        A_s (area): section area [m²].
        σ: axial stress, tension positive [Pa].

    Validity: axial stress only; rod whip bending excluded (D5). The whole
    F_rod is used at every section (the mass above the section is not
    removed), which is conservative for tension.
    Source: S1 with the rod-force sign convention (decision 0003).
    """
    area = require_positive("A_s", area)
    return axial_stress(-as_float_array("f_rod", f_rod), area)


@dataclass(frozen=True)
class RodSection:
    """A connecting-rod section to assess.

    Attributes:
        name: section name.
        A: section area [m²].
        K_t: axial stress-concentration factor [-], >= 1.
        rho: notch radius [m], needed with sqrt_a when K_t > 1.
        sqrt_a: Neuber constant [m^0.5], or None if q is given.
        q: notch sensitivity [-], or None to use N2.
        status: data status of the section inputs.
    """

    name: str
    A: float
    K_t: float = 1.0
    rho: float | None = None
    sqrt_a: float | None = None
    q: float | None = None
    status: Status = Status.ASSUMED

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", Status(self.status))
        if not str(self.name).strip():
            raise ValueError("Section name must not be empty.")
        object.__setattr__(self, "A", require_positive("A", self.A))
        notch_factor(self.K_t, self.rho, self.sqrt_a, self.q)


@dataclass(frozen=True)
class BucklingPlane:
    """Buckling plane: second moment of area [m⁴] and effective-length factor."""

    name: str
    I: float  # noqa: E741
    K: float


@dataclass(frozen=True)
class RodBuckling:
    """Column data of the rod shank: area [m²], length [m], E [Pa], planes."""

    A: float
    L: float
    E: float
    planes: tuple[BucklingPlane, ...]
    status: Status = Status.ASSUMED


@dataclass(frozen=True)
class SectionResult:
    """Per-section results.

    Attributes:
        section: the section assessed.
        K_f: fatigue notch factor used [-].
        q: notch sensitivity used, or None.
        sigma_max_nom, sigma_min_nom: nominal stress extremes [Pa].
        sigma_history: notched stress over θ [Pa].
        location: fatigue assessment of the notched history.
    """

    section: RodSection
    K_f: float
    q: float | None
    sigma_max_nom: float
    sigma_min_nom: float
    sigma_history: NDArray[np.float64]
    location: LocationResult


@dataclass(frozen=True)
class ConrodResult:
    """Connecting-rod assessment."""

    theta_deg: NDArray[np.float64]
    sections: tuple[SectionResult, ...]
    buckling: tuple[tuple[str, ColumnResult], ...]
    governing: tuple[str, float]
    inputs: tuple[tuple[str, str, str, str, str], ...]
    note: ResultNote

    def as_markdown(self) -> str:
        """Markdown report of inputs, equations, results and warnings."""
        rows = []
        for s in self.sections:
            a = s.location.assessment
            life = s.location.life
            rows.append((
                s.section.name, fmt(s.K_f), fmt(s.sigma_max_nom / MPA),
                fmt(s.sigma_min_nom / MPA), fmt(s.location.sigma_a / MPA),
                fmt(s.location.sigma_m / MPA), a.regime, fmt(a.n_goodman),
                fmt(a.n_gerber), fmt(a.n_elliptic), fmt(a.n_yield),
                fmt(life.N_f) if life else "—",
            ))  # fmt: skip
        fatigue = markdown_table(
            ("Section", "K_f", "σ_max,nom [MPa]", "σ_min,nom [MPa]", "σ_a [MPa]",
             "σ_m [MPa]", "Regime", "n Goodman", "n Gerber", "n Elliptic",
             "n_y Langer", "N_f"),
            rows,
        )  # fmt: skip
        buck = markdown_table(
            ("Plane", "L_e/k", "(L_e/k)₁", "Regime", "σ_cr [MPa]", "P_cr [N]", "n"),
            [
                (name, fmt(c.slenderness), fmt(c.transition_slenderness), c.regime,
                 fmt(c.sigma_cr / MPA), fmt(c.P_cr), fmt(c.n))
                for name, c in self.buckling
            ],
        )  # fmt: skip
        gov = f"**Governing:** {self.governing[0]}, n = {fmt(self.governing[1])}"
        results = f"### Fatigue\n\n{fatigue}\n\n### Buckling\n\n{buck}\n\n{gov}"
        return report("Connecting-rod assessment", self.inputs, results, self.note)


def assess_conrod(
    cycle: CycleResult,
    sections: Sequence[RodSection],
    material: Material,
    marin: EnduranceLimit,
    basquin: BasquinConstants | None,
    buckling_inputs: RodBuckling,
) -> ConrodResult:
    """Fatigue per section (R1, N1/N2, S2, M1–M5, B2) and buckling (C1–C3).

    Args:
        cycle: result of evaluate_cycle (0..719 grid).
        sections: rod sections to assess.
        material: rod material (S_ut, S_y).
        marin: endurance limit for axial loading (F1).
        basquin: constants for finite life when n_Goodman < 1, or None.
        buckling_inputs: shank column data; checked with the maximum
            compressive F_rod in every plane.
    """
    if not sections:
        raise ValueError("At least one rod section is needed.")
    if not buckling_inputs.planes:
        raise ValueError("At least one buckling plane is needed.")
    results = []
    for sec in sections:
        k_f, q = notch_factor(sec.K_t, sec.rho, sec.sqrt_a, sec.q)
        nominal = np.asarray(rod_axial_stress(cycle.F_rod, sec.A))
        notched = k_f * nominal
        loc = assess_location(sec.name, notched, None, marin, material, basquin)
        results.append(
            SectionResult(sec, k_f, q, float(nominal.max()), float(nominal.min()),
                          as_array(notched), loc)
        )  # fmt: skip

    p_max = cycle.F_rod_max_compression
    buck = tuple(
        (pl.name, column_check(buckling_inputs.A, pl.I, buckling_inputs.L, pl.K,
                               buckling_inputs.E, material.S_y, p_max))
        for pl in buckling_inputs.planes
    )  # fmt: skip
    items = [(f"{r.section.name} fatigue", r.location.assessment.n_goodman)
             for r in results]  # fmt: skip
    items += [(f"{r.section.name} yield (Langer)", r.location.assessment.n_yield)
              for r in results]  # fmt: skip
    items += [(f"buckling {name}", c.n) for name, c in buck]
    gov = governing(items)

    validity = [
        "R1: axial stress only, σ = −F_rod / A (tension positive); rod whip "
        "bending excluded (D5).",
        "Whole F_rod used at every section; mass above the section not removed "
        "(conservative for tension).",
        f"Buckling checked with the maximum compressive F_rod = {fmt(p_max)} N "
        f"at θ = {cycle.theta_max_compression_deg:g}°.",
        "Governing item: lowest of fatigue n (Goodman, or M5 for compressive "
        "mean), Langer yield n and buckling n.",
        *check_cycle_grid(cycle),
    ]
    statuses = {
        "material": material.status,
        "S_e'": marin.S_e_prime.status,
        "cylinder pressure": cycle.note.input_statuses.get(
            "cylinder pressure", Status.ASSUMED
        ),
        "buckling inputs": buckling_inputs.status,
    }
    if basquin is not None:
        statuses["Basquin constants"] = basquin.status
    sub = [(r.section.name, r.location.note) for r in results]
    sub += [(f"buckling {n}", c.note) for n, c in buck]
    sub.append(("endurance limit", marin.note))
    ids = ["R1", "N1"]
    if any(r.q is not None and r.section.q is None for r in results):
        ids.append("N2")
    note = merge_notes(ids, validity, sub, statuses)

    inputs = [
        ("Material", material.name, "", material.status.value, material.source_id),
        ("S_ut", fmt(material.S_ut / MPA), "MPa", material.status.value,
         material.source_id),
        ("S_y", fmt(material.S_y / MPA), "MPa", material.status.value,
         material.source_id),
        *endurance_inputs("Axial", marin),
    ]  # fmt: skip
    for sec in sections:
        st_ = sec.status.value
        inputs.append((f"{sec.name} A", fmt(sec.A * 1e6), "mm²", st_, ""))
        inputs.append((f"{sec.name} K_t", fmt(sec.K_t), "-", st_, ""))
        if sec.rho is not None:
            inputs.append((f"{sec.name} ρ", fmt(sec.rho * 1e3), "mm", st_, ""))
        if sec.q is not None:
            inputs.append((f"{sec.name} q", fmt(sec.q), "-", st_, ""))
        elif sec.sqrt_a is not None:
            inputs.append((f"{sec.name} √a", fmt(sec.sqrt_a), "m^0.5", st_, ""))
    b = buckling_inputs
    bs = b.status.value
    inputs += [("Buckling A", fmt(b.A * 1e6), "mm²", bs, ""),
               ("Buckling L", fmt(b.L * 1e3), "mm", bs, ""),
               ("E", fmt(b.E / 1e9), "GPa", bs, "")]  # fmt: skip
    inputs += [(f"{p.name} I / K", f"{fmt(p.I * 1e12)} / {fmt(p.K)}", "mm⁴ / -",
                bs, "") for p in b.planes]  # fmt: skip
    if basquin is not None:
        inputs.append(("σ′_f / b", f"{fmt(basquin.sigma_f_prime / MPA)} / "
                       f"{fmt(basquin.b)}", "MPa / -", basquin.status.value,
                       basquin.source_id))  # fmt: skip

    return ConrodResult(
        as_array(cycle.theta_deg), tuple(results), buck, gov, tuple(inputs), note
    )
