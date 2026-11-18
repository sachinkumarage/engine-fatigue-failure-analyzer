import math

import numpy as np
import pytest

from efa.fatigue.basquin import BasquinConstants, life, strength
from efa.fatigue.marin import (
    FACTOR_NAMES,
    MarinFactor,
    endurance_limit,
    load_factor,
    reliability_factor,
    size_factor,
    steel_endurance_estimate,
    surface_factor,
)
from efa.fatigue.mean_stress import (
    LOCAL_YIELD_WARNING,
    assess,
    elliptic,
    gerber,
    goodman,
    haigh_curves,
    langer,
)
from efa.provenance import Status, TracedValue
from efa.stress.notch import fatigue_notch_factor, notch_sensitivity

MPA = 1.0e6
S_E, S_UT, S_Y = 250 * MPA, 900 * MPA, 750 * MPA


def unit_factors():
    return {n: MarinFactor(1.0, "test", Status.ASSUMED) for n in FACTOR_NAMES}


# --- mean stress -------------------------------------------------------------


def test_zero_mean_gives_endurance_ratio():
    sa = 180 * MPA
    for n in (
        goodman(sa, 0.0, S_E, S_UT),
        gerber(sa, 0.0, S_E, S_UT),
        elliptic(sa, 0.0, S_E, S_Y),
    ):
        assert n == pytest.approx(S_E / sa, rel=1e-14)


def test_gerber_not_below_goodman_for_tensile_mean():
    rng = np.random.default_rng(12345)
    sa = rng.uniform(1.0, 500.0, 2000) * MPA
    sm = rng.uniform(1.0, 800.0, 2000) * MPA
    assert np.all(gerber(sa, sm, S_E, S_UT) >= goodman(sa, sm, S_E, S_UT) * (1 - 1e-12))


def test_compressive_mean_uses_m5_and_langer_uses_abs():
    sa, sm = 100 * MPA, -200 * MPA
    assert goodman(sa, sm, S_E, S_UT) == pytest.approx(S_E / sa)
    assert langer(sa, sm, S_Y) == pytest.approx(S_Y / (sa + 200 * MPA))


def test_local_yield_warning():
    res = assess(300 * MPA, 300 * MPA, S_E, S_UT, S_Y, K_f=2.0, sigma_max=400 * MPA)
    assert LOCAL_YIELD_WARNING in res.note.warnings


def test_local_yield_check_skipped_without_inputs():
    res = assess(100 * MPA, 50 * MPA, S_E, S_UT, S_Y)
    assert not res.note.warnings
    assert any("not performed" in v for v in res.note.validity_notes)


def test_assess_note_ids():
    assert set(assess(100 * MPA, 50 * MPA, S_E, S_UT, S_Y).note.equation_ids) == {
        "M1", "M2", "M3", "M4"
    }  # fmt: skip
    assert "M5" in assess(100 * MPA, -50 * MPA, S_E, S_UT, S_Y).note.equation_ids


def test_haigh_curves_pass_through_intercepts():
    c = haigh_curves(S_E, S_UT, S_Y)
    assert c["Goodman"][1][0] == pytest.approx(S_E)
    assert c["Goodman"][1][-1] == pytest.approx(0.0, abs=1e-6)
    assert c["Langer"][1][0] == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"sigma_a": 0.0}, "sigma_a"),
        ({"S_y": 1000 * MPA}, "S_y"),
        ({"S_ut": -1.0}, "S_ut"),
        ({"S_e": 0.0}, "S_e"),
        ({"K_f": 0.9, "sigma_max": 1.0}, "K_f"),
    ],
)
def test_assess_validation(kwargs, match):
    args = dict(sigma_a=100 * MPA, sigma_m=0.0, S_e=S_E, S_ut=S_UT, S_y=S_Y)
    with pytest.raises(ValueError, match=match):
        assess(**{**args, **kwargs})


# --- notch ---------------------------------------------------------------------


def test_kt_one_gives_kf_one():
    assert fatigue_notch_factor(1.0, 0.8) == 1.0


def test_q_tends_to_one_for_large_radius():
    assert notch_sensitivity(0.0019, 1.0e6) == pytest.approx(1.0, abs=1e-5)


@pytest.mark.parametrize(
    ("k_t", "q", "match"), [(0.9, 0.5, "K_t"), (2.0, -0.1, "q"), (2.0, 1.1, "q")]
)
def test_notch_validation(k_t, q, match):
    with pytest.raises(ValueError, match=match):
        fatigue_notch_factor(k_t, q)


# --- Marin ---------------------------------------------------------------------


@pytest.mark.parametrize("d", [0.00278, 0.2541])
def test_size_factor_range(d):
    with pytest.raises(ValueError, match="2.79 mm <= d <= 254 mm"):
        size_factor(d, "bending")


def test_size_factor_axial_and_branches():
    assert size_factor(0.5, "axial").value == 1.0
    assert size_factor(0.051, "bending").value == pytest.approx(1.24 * 51**-0.107)
    assert size_factor(0.100, "torsion").value == pytest.approx(1.51 * 100**-0.157)


def test_shigley_factors_flag_verify():
    for f in (
        surface_factor(900 * MPA, 4.51, -0.265),
        size_factor(0.04, "bending"),
        load_factor("axial"),
        reliability_factor(2.326),
        steel_endurance_estimate(900 * MPA),
    ):
        assert f.verify and f.source_id == "SRC-SHIGLEY"
    assert steel_endurance_estimate(1500 * MPA).value == 700 * MPA


def test_endurance_limit_requires_all_factors():
    factors = unit_factors()
    del factors["k_d"]
    with pytest.raises(ValueError, match="k_d"):
        endurance_limit(TracedValue(400 * MPA, "test", Status.ASSUMED), factors)


def test_endurance_limit_note_lists_factors():
    res = endurance_limit(
        TracedValue(400 * MPA, "test", Status.ASSUMED), unit_factors()
    )
    assert res.S_e == 400 * MPA
    assert "F1" in res.note.equation_ids
    assert set(res.note.input_statuses) == {"S_e'", *FACTOR_NAMES}


def test_invalid_factor_values():
    with pytest.raises(ValueError):
        MarinFactor(0.0, "zero", Status.ASSUMED)
    with pytest.raises(ValueError):
        load_factor("shear")
    with pytest.raises(ValueError):
        reliability_factor(-1.0)


# --- Basquin -------------------------------------------------------------------

CONSTS = BasquinConstants(1200 * MPA, -0.09, 1e3, 1e6, "test", Status.ASSUMED)


@pytest.mark.parametrize("sigma_m", [0.0, 150 * MPA, -100 * MPA])
def test_life_strength_round_trip(sigma_m):
    n = life(380 * MPA, sigma_m, CONSTS).N_f
    assert strength(n, sigma_m, CONSTS).sigma_a == pytest.approx(380 * MPA, rel=1e-12)


def test_basquin_ids():
    assert life(400 * MPA, 0.0, CONSTS).note.equation_ids == ("B1",)
    assert "B2" in life(400 * MPA, 50 * MPA, CONSTS).note.equation_ids


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"b": 0.0}, "b must be negative"),
        ({"b": 0.1}, "b must be negative"),
        ({"N_min": 1e6, "N_max": 1e3}, "N_min"),
        ({"sigma_f_prime": -1.0}, "sigma_f_prime"),
    ],
)
def test_basquin_constants_validation(kwargs, match):
    args = dict(
        sigma_f_prime=1200 * MPA, b=-0.09, N_min=1e3, N_max=1e6,
        source_id="t", status=Status.ASSUMED,
    )  # fmt: skip
    with pytest.raises(ValueError, match=match):
        BasquinConstants(**{**args, **kwargs})


def test_mean_not_below_sigma_f_prime():
    with pytest.raises(ValueError, match="sigma_f_prime"):
        life(100 * MPA, 1200 * MPA, CONSTS)
    assert math.isfinite(life(100 * MPA, 1100 * MPA, CONSTS).N_f)
