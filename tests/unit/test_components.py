import math

import numpy as np
import pytest

from efa.components.common import Material, assess_location
from efa.components.conrod import RodSection, rod_axial_stress
from efa.components.conrod_bolt import (
    BoltJoint,
    bolt_and_member_forces,
    bolt_external_load,
    bolt_fatigue_factor,
    bolt_stresses,
    proof_factor,
    separation_factor,
    stiffness_ratio,
)
from efa.components.crankshaft import (
    CrankGeometry,
    FilletNotch,
    crankpin_torques,
    fillet_stresses,
    pin_bending_moment,
)
from efa.fatigue.basquin import BasquinConstants
from efa.fatigue.marin import FACTOR_NAMES, MarinFactor, endurance_limit
from efa.provenance import Status, TracedValue
from efa.stress.nominal import amplitude_and_mean_from_history

MPA = 1.0e6
NOTCH = FilletNotch(2.2, 1.6, 0.0025)


def test_r1_sign():
    assert rod_axial_stress(-1000.0, 1e-4) == pytest.approx(1.0e7)
    assert rod_axial_stress(1000.0, 1e-4) == pytest.approx(-1.0e7)


def test_x3_symmetry():
    f_t = np.linspace(-5000.0, 12000.0, 9)
    free, drive = crankpin_torques(f_t, 0.043)
    assert np.allclose(free, drive, rtol=1e-14)
    assert np.allclose(free, f_t * 0.043 / 2.0)


def test_x2_constant_radial_load_gives_mean_only():
    m = pin_bending_moment(np.full(720, 12000.0), 0.09, 0.012)
    sigma, _ = fillet_stresses(m, np.zeros(720), 0.048, 2.0, 1.5)
    s_a, s_m = amplitude_and_mean_from_history(sigma)
    assert s_a == 0.0
    assert s_m > 0.0


def test_bolt_relations_with_simple_inputs():
    c = stiffness_ratio(1.0e8, 3.0e8)
    assert c == 0.25
    assert bolt_and_member_forces(c, 1000.0, 10000.0) == (10250.0, -9250.0)
    s_a, s_m = bolt_stresses(c, 1000.0, 10000.0, 1.0e-4)
    assert s_a == pytest.approx(1.25e6)
    assert s_m == pytest.approx(1.25e6 + 1.0e8)
    assert proof_factor(600e6, 1.0e-4, c, 1000.0, 10000.0) == pytest.approx(
        60000.0 / 10250.0
    )
    assert separation_factor(10000.0, 1000.0, c) == pytest.approx(10000.0 / 750.0)
    s_i = 1.0e8
    n_f = bolt_fatigue_factor(100e6, 1000e6, s_a, s_m, s_i)
    assert n_f == pytest.approx(100e6 * 900e6 / (1000e6 * 1.25e6 + 100e6 * 1.25e6))
    assert bolt_external_load(-1000.0, 0.3, 0.1, 0.05, 100.0, 2) == (
        pytest.approx(1100.0), pytest.approx(550.0)
    )  # fmt: skip


def test_goodman_below_one_triggers_morrow_life():
    factors = {n: MarinFactor(1.0, "t", Status.ASSUMED) for n in FACTOR_NAMES}
    end = endurance_limit(TracedValue(200 * MPA, "t", Status.ASSUMED), factors)
    mat = Material("t", 900 * MPA, 750 * MPA, Status.ASSUMED)
    consts = BasquinConstants(1200 * MPA, -0.09, 1e3, 1e6, "t", Status.ASSUMED)
    theta = np.radians(np.arange(720.0))
    history = 100 * MPA + 250 * MPA * np.sin(theta)
    loc = assess_location("hot spot", history, None, end, mat, consts)
    assert loc.assessment.n_goodman < 1.0
    assert loc.life is not None
    assert loc.life.N_f == pytest.approx(
        0.5 * (250e6 / (1200e6 - 100e6)) ** (1 / -0.09), rel=1e-9
    )
    assert "B2" in loc.note.equation_ids
    ok = assess_location("ok", 50 * MPA * np.sin(theta), None, end, mat, consts)
    assert ok.life is None


def test_local_yield_warning_in_location():
    factors = {n: MarinFactor(1.0, "t", Status.ASSUMED) for n in FACTOR_NAMES}
    end = endurance_limit(TracedValue(200 * MPA, "t", Status.ASSUMED), factors)
    mat = Material("t", 900 * MPA, 500 * MPA, Status.ASSUMED)
    theta = np.radians(np.arange(720.0))
    loc = assess_location("x", 300 * MPA + 250 * MPA * np.sin(theta), None, end, mat,
                          None)  # fmt: skip
    assert any("local yielding" in w for w in loc.note.warnings)
    assert any("no Basquin constants" in w for w in loc.note.warnings)


def geometry(**kw):
    args = dict(L_b=0.09, s_p=0.012, d_pin=0.048, s_j=0.01, d_journal=0.055,
                pin_fillet=NOTCH, journal_fillet=NOTCH, sqrt_a=0.0019)  # fmt: skip
    return CrankGeometry(**{**args, **kw})


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        ({"s_p": 0.045}, "s_p"),
        ({"s_p": 0.050}, "s_p"),
        ({"d_pin": 0.0}, "d_pin"),
        ({"d_journal": -0.05}, "d_journal"),
        ({"s_j": 0.0}, "s_j"),
    ],
)
def test_crank_geometry_validation(kw, match):
    with pytest.raises(ValueError, match=match):
        geometry(**kw)


def joint(**kw):
    args = dict(n_b=2, A_t=61.2e-6, k_b=3e8, k_m=1.2e9, F_i=30e3, S_p=830e6,
                S_ut=1040e6, S_y=940e6, S_e=162e6, m_cap=0.1)  # fmt: skip
    return BoltJoint(**{**args, **kw})


@pytest.mark.parametrize(
    ("kw", "match"),
    [({"F_i": 0.0}, "F_i"), ({"F_i": -1.0}, "F_i"), ({"n_b": 0}, "n_b"),
     ({"n_b": 1.5}, "n_b"), ({"k_b": 0.0}, "k_b")],
)  # fmt: skip
def test_bolt_joint_validation(kw, match):
    with pytest.raises(ValueError, match=match):
        joint(**kw)


@pytest.mark.parametrize("c", [0.0, 1.0, -0.2, 1.5])
def test_c_outside_unit_interval(c):
    with pytest.raises(ValueError, match="C must lie in"):
        bolt_and_member_forces(c, 1000.0, 1e4)


def test_cap_mass_not_below_rotating_mass():
    with pytest.raises(ValueError, match="m_cap"):
        bolt_external_load(-1000.0, 0.3, 0.3, 0.05, 100.0, 2)


def test_rod_section_needs_notch_data():
    with pytest.raises(ValueError, match="q or both sqrt_a and rho"):
        RodSection("x", 1e-4, K_t=1.8)
    assert RodSection("x", 1e-4, K_t=1.8, q=0.9).q == 0.9
    assert math.isfinite(rod_axial_stress(0.0, 1e-4))
