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


def test_stress_and_section_units():
    assert units.pa_to_mpa(units.mpa_to_pa(750.0)) == pytest.approx(750.0)
    assert units.gpa_to_pa(205.0) == pytest.approx(205e9)
    assert units.mm2_to_m2(240.0) == pytest.approx(2.4e-4)
    assert units.mm4_to_m4(18000.0) == pytest.approx(1.8e-8)
    assert units.sqrt_mm_to_sqrt_m(math.sqrt(1000.0) * 0.0019) == pytest.approx(0.0019)
