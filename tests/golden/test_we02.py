"""WE-02: rod and crankpin loads over the cycle (docs/worked_examples/WE-02.md)."""

import math

import numpy as np
import pytest

from efa.loads.cycle import EngineSpec, evaluate_cycle
from efa.loads.gas import PressureTable, piston_area
from efa.loads.kinematics import angular_speed
from efa.provenance import Status
from efa.units import bar_to_pa


def close(expected: float):
    return pytest.approx(expected, rel=1e-6, abs=1e-6 if expected == 0 else 0.0)


ANGLES = [0, 180, 300, 340, 360, 370, 380, 400, 450, 540, 720]
P_BAR = [1.0, 1.0, 5.0, 25.0, 45.0, 60.0, 50.0, 30.0, 10.0, 3.0, 1.0]


@pytest.fixture(scope="module")
def result():
    table = PressureTable(ANGLES, bar_to_pa(P_BAR), "WE-02", Status.ASSUMED)
    spec = EngineSpec(
        bore=0.086,
        stroke=0.086,
        rod_length=0.143,
        speed_rpm=4000.0,
        m_piston=0.40,
        m_pin=0.10,
        m_rings=0.03,
        m_rod=0.55,
        l_g=0.040,
        p_crankcase=101325.0,
        pressure_table=table,
    )
    return evaluate_cycle(spec)


def test_scalars(result):
    assert piston_area(0.086) == close(5.8088048165e-3)
    assert angular_speed(4000.0) == close(418.8790204786)
    assert result.F_c == close(2988.887377)


ROWS = [
    # θ, p_cyl, F_g, a_p, F_i, F_p, β [deg], F_rod, F_side, F_t, F_r, T
    (0, 100000, -7.696666, 9813.469588, -6710.903434, -6718.600100, 0,
     -6718.600100, 0, 0, -6718.600100, 0),
    (90, 100000, -7.696666, -2268.705335, 1551.445417, 1543.748751, 17.499610,
     1618.662050, 486.730546, 1543.748751, -486.730546, 66.381196),
    (330, 2000000, 11029.032485, 7668.310176, -5243.944421, 5785.088064,
     -8.647190, 5851.603915, -879.786603, -3654.461580, 4570.139926, -157.141848),
    (370, 6000000, 34264.251751, 9562.027993, -6538.956066, 27725.295685,
     2.993111, 27763.169641, 1449.678490, 6242.101687, 27052.352117, 268.410373),
    (450, 1000000, 5220.227668, -2268.705335, 1551.445417, 6771.673086,
     17.499610, 7100.281202, 2135.049592, 6771.673086, -2135.049592, 291.181943),
]  # fmt: skip


@pytest.mark.parametrize("row", ROWS, ids=[f"theta={r[0]}" for r in ROWS])
def test_rows(result, row):
    i = int(np.flatnonzero(result.theta_deg == row[0])[0])
    computed = (
        result.p_cyl[i],
        result.F_g[i],
        result.a_p[i],
        result.F_i[i],
        result.F_p[i],
        math.degrees(result.beta[i]),
        result.F_rod[i],
        result.F_side[i],
        result.F_t[i],
        result.F_r[i],
        result.T[i],
    )
    for got, expected in zip(computed, row[1:], strict=True):
        assert got == close(expected)


def test_extremes(result):
    assert result.F_rod_max_compression == close(27763.169641)
    assert result.theta_max_compression_deg == 370
    assert result.F_rod_max_tension == close(-6718.600100)
    assert result.theta_max_tension_deg == 0
    assert result.T_mean == close(38.641812)
