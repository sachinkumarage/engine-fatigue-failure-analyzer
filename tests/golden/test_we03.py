"""WE-03: endurance limit, notch, mean stress (docs/worked_examples/WE-03.md)."""

import pytest

from efa.fatigue.marin import (
    MarinFactor,
    endurance_limit,
    load_factor,
    reliability_factor,
    size_factor,
    steel_endurance_estimate,
    surface_factor,
)
from efa.fatigue.mean_stress import LOCAL_YIELD_WARNING, assess
from efa.provenance import Status
from efa.stress.nominal import peak_abs_stress
from efa.stress.notch import fatigue_notch_factor, notch_sensitivity, notched_stresses
from tests.golden._tol import close

MPA = 1.0e6
S_UT, S_Y = 900 * MPA, 750 * MPA


@pytest.fixture(scope="module")
def endurance():
    factors = {
        "k_a": surface_factor(S_UT, 4.51, -0.265, status=Status.ASSUMED),
        "k_b": size_factor(0.040, "bending"),
        "k_c": load_factor("bending"),
        "k_d": MarinFactor(1.0, "WE-03 input k_d = 1", Status.ASSUMED),
        "k_e": reliability_factor(2.326),
        "k_f": MarinFactor(1.0, "WE-03 input k_f = 1", Status.ASSUMED),
    }
    return endurance_limit(steel_endurance_estimate(S_UT), factors)


@pytest.fixture(scope="module")
def k_f():
    return fatigue_notch_factor(2.0, notch_sensitivity(0.0019, 0.002))


def test_factors(endurance):
    f = endurance.factors
    assert f["k_a"].value == close("0.7435364728")
    assert f["k_b"].value == close("0.8356054543")
    assert f["k_e"].value == close("0.81392")
    assert endurance.S_e_prime.value / MPA == close("450")
    assert endurance.S_e / MPA == close("227.560970")


def test_endurance_note(endurance):
    note = endurance.note
    assert {"F1", "F2", "F3", "F4", "F5", "F6"} <= set(note.equation_ids)
    assert note.verify
    assert all(n in " ".join(note.validity_notes) for n in ("k_a", "k_f", "S_e'"))


def test_notch(k_f):
    assert notch_sensitivity(0.0019, 0.002) == close("0.9592461477")
    assert k_f == close("1.9592461477")


CASES = [
    ("A", 150, 100, "293.886922", "195.924615",
     "0.66262090", "0.75348153", "0.75894399", "1.53120117", "tensile_mean"),
    ("B", 150, -80, "293.886922", "-156.739692",
     "0.77431472", "0.77431472", "0.77431472", "1.66434910",
     "compressive_or_zero_mean"),
    ("C", 120, 0, "235.109538", "0",
     "0.96789340", "0.96789340", "0.96789340", "3.19000244",
     "compressive_or_zero_mean"),
]  # fmt: skip


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_cases(endurance, k_f, case):
    _, sa_nom, sm_nom, sa, sm, n_go, n_ge, n_el, n_y, regime = case
    sig_a, sig_m = notched_stresses(sa_nom * MPA, sm_nom * MPA, k_f)
    assert sig_a / MPA == close(sa)
    assert sig_m / MPA == close(sm)
    sigma_max = peak_abs_stress(sa_nom * MPA, sm_nom * MPA)
    res = assess(sig_a, sig_m, endurance.S_e, S_UT, S_Y, K_f=k_f, sigma_max=sigma_max)
    assert res.n_goodman == close(n_go)
    assert res.n_gerber == close(n_ge)
    assert res.n_elliptic == close(n_el)
    assert res.n_yield == close(n_y)
    assert res.regime == regime
    assert LOCAL_YIELD_WARNING not in res.note.warnings
