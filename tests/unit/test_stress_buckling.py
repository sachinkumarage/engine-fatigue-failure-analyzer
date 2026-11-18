import math

import pytest

from efa.buckling import (
    column_check,
    euler_stress,
    johnson_stress,
    transition_slenderness,
)
from efa.stress.nominal import (
    amplitude_and_mean,
    amplitude_and_mean_from_history,
    axial_stress,
    bending_stress,
    torsional_stress,
    von_mises,
)

E, S_Y = 205e9, 750e6


def test_nominal_stresses():
    assert axial_stress(1000.0, 1e-4) == pytest.approx(1e7)
    assert bending_stress(10.0, 0.01, 1e-8) == pytest.approx(1e7)
    assert torsional_stress(10.0, 0.01, 2e-8) == pytest.approx(5e6)
    assert von_mises(100.0, 0.0) == 100.0
    assert von_mises(0.0, 100.0) == pytest.approx(100.0 * math.sqrt(3.0))


def test_amplitude_and_mean():
    assert amplitude_and_mean(250.0, -50.0) == (150.0, 100.0)
    assert amplitude_and_mean_from_history([10.0, 250.0, -50.0, 0.0]) == (150.0, 100.0)
    with pytest.raises(ValueError):
        amplitude_and_mean(-50.0, 250.0)
    with pytest.raises(ValueError):
        axial_stress(1.0, 0.0)


def test_euler_equals_johnson_at_transition():
    s1 = transition_slenderness(E, S_Y)
    assert euler_stress(E, s1) == pytest.approx(S_Y / 2.0, rel=1e-12)
    assert johnson_stress(S_Y, E, s1) == pytest.approx(S_Y / 2.0, rel=1e-12)


def test_tension_gives_infinite_safety_factor():
    res = column_check(2.4e-4, 1.8e-8, 0.143, 1.0, E, S_Y, -5000.0)
    assert res.n == math.inf
    assert any("n = inf" in v for v in res.note.validity_notes)


def test_column_note_ids():
    assert column_check(2.4e-4, 1.8e-8, 0.143, 1.0, E, S_Y, 1e4).note.equation_ids == (
        "C1", "C2", "C3"
    )  # fmt: skip
    assert column_check(2.4e-4, 8e-9, 1.5, 1.0, E, S_Y, 1e3).note.equation_ids == (
        "C1", "C3"
    )  # fmt: skip


@pytest.mark.parametrize("name", ["A", "I", "L", "K", "E", "S_y"])
def test_column_validation(name):
    args = dict(A=2.4e-4, I=1.8e-8, L=0.143, K=1.0, E=E, S_y=S_Y, P=1e4)
    args[name] = 0.0
    with pytest.raises(ValueError, match=name):
        column_check(**args)
