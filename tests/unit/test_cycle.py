import math

import numpy as np
import pytest

from efa.loads.cycle import EngineSpec, evaluate_cycle, peak_load
from efa.loads.gas import PressureTable
from efa.provenance import Status
from efa.units import bar_to_pa

ANGLES = [0, 180, 300, 340, 360, 370, 380, 400, 450, 540, 720]
P_BAR = [1.0, 1.0, 5.0, 25.0, 45.0, 60.0, 50.0, 30.0, 10.0, 3.0, 1.0]
BASE = dict(
    bore=0.086,
    stroke=0.086,
    rod_length=0.143,
    speed_rpm=4000.0,
    m_piston=0.40,
    m_pin=0.10,
    m_rings=0.03,
    m_rod=0.55,
    l_g=0.040,
)


def make_spec(table=None, **overrides):
    if table is None:
        table = PressureTable(ANGLES, bar_to_pa(P_BAR), "WE-02", Status.ASSUMED)
    return EngineSpec(**{**BASE, **overrides}, pressure_table=table)


def test_inertia_force_periodic_over_360():
    res = evaluate_cycle(make_spec())
    assert np.allclose(res.F_i[:360], res.F_i[360:], rtol=1e-12, atol=1e-9)


def test_identities_at_90_degrees():
    res = evaluate_cycle(make_spec(), [90.0, 450.0])
    assert np.allclose(res.F_t, res.F_p, rtol=1e-12)
    assert np.allclose(res.F_r, -res.F_p * np.tan(res.beta), rtol=1e-12)


def test_inertia_only_mean_torque_is_zero():
    p_cc = 101325.0
    table = PressureTable([0, 720], [p_cc, p_cc], "constant", Status.ASSUMED)
    res = evaluate_cycle(make_spec(table, p_crankcase=p_cc))
    assert np.all(res.F_g == 0.0)
    assert abs(res.T_mean) < 1e-9 * np.max(np.abs(res.T))


def test_peak_load_matches_cycle():
    spec = make_spec()
    cyc = evaluate_cycle(spec)
    pk = peak_load(spec, bar_to_pa(60.0), 370.0)
    i = 370
    for name in ("p_cyl", "F_g", "a_p", "F_i", "F_p", "beta", "F_rod", "F_side"):
        assert getattr(pk, name)[0] == pytest.approx(getattr(cyc, name)[i], rel=1e-12)
    for name in ("F_t", "F_r", "T"):
        assert getattr(pk, name)[0] == pytest.approx(getattr(cyc, name)[i], rel=1e-12)
    assert pk.F_c == cyc.F_c


def test_result_note_contents():
    note = evaluate_cycle(make_spec()).note
    text = " ".join(note.validity_notes)
    assert "second-order series" in text
    assert "Constant crank speed" in text
    assert "Two-mass rod model" in text
    assert note.input_statuses["cylinder pressure"] is Status.ASSUMED
    assert {"K3", "L5", "L6"} <= set(note.equation_ids)


def test_cycle_requires_pressure_table():
    spec = EngineSpec(**BASE)
    with pytest.raises(ValueError, match="pressure_table"):
        evaluate_cycle(spec)
    assert math.isfinite(peak_load(spec, 6.0e6, 370.0).F_rod[0])


@pytest.mark.parametrize(
    ("angles", "pressures", "match"),
    [
        ([0, 360, 360, 720], [1e5, 2e5, 3e5, 1e5], "strictly increasing"),
        ([0, 400, 300, 720], [1e5, 2e5, 3e5, 1e5], "strictly increasing"),
        ([0, 360, 700], [1e5, 2e5, 1e5], "end at 720"),
        ([10, 360, 720], [1e5, 2e5, 1e5], "start at 0"),
        ([0, 360, 720], [1e5, 2e5, 1.1e5], "must be equal"),
        ([0, 360, 720], [1e5, -2e5, 1e5], "positive"),
    ],
)
def test_pressure_table_validation(angles, pressures, match):
    with pytest.raises(ValueError, match=match):
        PressureTable(angles, pressures, "test", Status.ASSUMED)


def test_pressure_table_interpolation_modulo_720():
    t = PressureTable(ANGLES, bar_to_pa(P_BAR), "WE-02", Status.ASSUMED)
    assert t.pressure_at(330.0) == pytest.approx(2.0e6)
    assert t.pressure_at(330.0 + 720.0) == pytest.approx(2.0e6)
    assert t.pressure_at(-390.0) == pytest.approx(2.0e6)


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"rod_length": 0.043}, "rod_length"),
        ({"rod_length": 0.040}, "rod_length"),
        ({"l_g": 0.143}, "l_g"),
        ({"l_g": 0.200}, "l_g"),
        ({"l_g": 0.0}, "l_g"),
        ({"bore": -0.086}, "bore"),
    ],
)
def test_engine_spec_validation(overrides, match):
    with pytest.raises(ValueError, match=match):
        make_spec(**overrides)
