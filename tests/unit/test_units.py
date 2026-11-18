import math

import numpy as np
import pytest

from efa import units


def test_round_trips():
    assert units.pa_to_bar(units.bar_to_pa(2.5)) == pytest.approx(2.5)
    assert units.m_to_mm(units.mm_to_m(86.0)) == pytest.approx(86.0)
    assert units.rad_to_deg(units.deg_to_rad(370.0)) == pytest.approx(370.0)
    assert units.kg_to_g(units.g_to_kg(550.0)) == pytest.approx(550.0)


def test_values():
    assert units.bar_to_pa(1.0) == 1.0e5
    assert units.rpm_to_rad_s(60.0) == pytest.approx(2.0 * math.pi)
    assert np.allclose(units.mm_to_m(np.array([1.0, 2.0])), [1e-3, 2e-3])
