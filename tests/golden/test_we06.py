"""WE-06: connecting rod (docs/worked_examples/WE-06.md)."""

import pytest

from efa.components.common import Material
from efa.components.conrod import BucklingPlane, RodBuckling, RodSection, assess_conrod
from efa.fatigue.basquin import BasquinConstants
from efa.fatigue.marin import (
    MarinFactor,
    endurance_limit,
    load_factor,
    reliability_factor,
    size_factor,
    surface_factor,
)
from efa.fatigue.mean_stress import LOCAL_YIELD_WARNING
from efa.provenance import Status, TracedValue
from tests.golden._tol import close
from tests.golden._we02 import we02_cycle

MPA = 1.0e6


@pytest.fixture(scope="module")
def result():
    s_ut = 900 * MPA
    factors = {
        "k_a": surface_factor(s_ut, 4.51, -0.265, status=Status.ASSUMED),
        "k_b": size_factor(0.010, "axial"),
        "k_c": load_factor("axial"),
        "k_d": MarinFactor(1.0, "WE-06 k_d = 1", Status.ASSUMED),
        "k_e": reliability_factor(2.326),
        "k_f": MarinFactor(1.0, "WE-06 k_f = 1", Status.ASSUMED),
    }
    marin = endurance_limit(TracedValue(450 * MPA, "WE-06", Status.ASSUMED), factors)
    sections = [
        RodSection("Shank", 2.4e-4),
        RodSection("Small-end transition", 2.0e-4, K_t=1.8, rho=0.003, sqrt_a=0.0019),
    ]
    buckling = RodBuckling(
        A=2.4e-4, L=0.143, E=205e9,
        planes=(BucklingPlane("plane 1", 1.8e-8, 1.0),
                BucklingPlane("plane 2", 8.0e-9, 0.5)),
    )  # fmt: skip
    material = Material("synthetic", s_ut, 750 * MPA, Status.ASSUMED)
    basquin = BasquinConstants(1200 * MPA, -0.09, 1e3, 1e6, "WE-06", Status.ASSUMED)
    return assess_conrod(we02_cycle(), sections, material, marin, basquin, buckling)


def test_endurance_limit(result):
    assert result.sections[0].location.S_e / MPA == close("231.48104627")


ROWS = [
    ("Shank", "1", "27.99416708", "-115.67987351", "71.83702029", "-43.84285321",
     "3.2223086", "6.4834096"),
    ("Small-end transition", "1.7731791160", "33.59300050", "-138.81584821",
     "152.85588497", "-93.28947804", "1.5143744", "3.0469800"),
]  # fmt: skip


@pytest.mark.parametrize("row", ROWS, ids=[r[0] for r in ROWS])
def test_sections(result, row):
    name, k_f, s_max, s_min, s_a, s_m, n, n_y = row
    sec = next(s for s in result.sections if s.section.name == name)
    loc = sec.location
    assert sec.K_f == close(k_f)
    assert sec.sigma_max_nom / MPA == close(s_max)
    assert sec.sigma_min_nom / MPA == close(s_min)
    assert loc.sigma_a / MPA == close(s_a)
    assert loc.sigma_m / MPA == close(s_m)
    a = loc.assessment
    for value in (a.n_goodman, a.n_gerber, a.n_elliptic):
        assert value == close(n)
    assert a.n_yield == close(n_y)
    assert a.regime == "compressive_or_zero_mean"
    assert "M5" in a.note.equation_ids
    assert LOCAL_YIELD_WARNING not in loc.note.warnings
    assert loc.life is None
    assert any("no finite-life calculation" in v for v in loc.note.validity_notes)


def test_buckling_and_governing(result):
    planes = dict(result.buckling)
    assert planes["plane 1"].n == close("6.3195915")
    assert planes["plane 2"].n == close("6.3912619")
    name, n = result.governing
    assert name == "Small-end transition fatigue"
    assert n == close("1.5143744")
    assert not result.note.warnings
    assert "Small-end transition" in result.as_markdown()
