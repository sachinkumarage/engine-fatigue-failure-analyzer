import math

import numpy as np
import pytest

from efa.loads.kinematics import (
    angular_speed,
    crank_radius,
    crank_ratio,
    piston_acceleration,
    piston_acceleration_exact,
    piston_displacement,
    rod_angle,
)

S, L = 0.086, 0.143
R = crank_radius(S)
OMEGA = angular_speed(3000.0)


def test_displacement_at_bdc_equals_stroke():
    assert piston_displacement(math.pi, R, L) == pytest.approx(S, rel=1e-12)


def test_acceleration_tends_to_first_order_term_for_long_rod():
    theta = np.linspace(0.0, 2.0 * math.pi, 37)
    a = piston_acceleration(theta, R, 1.0e6, OMEGA)
    expected = R * OMEGA**2 * np.cos(theta)
    assert np.allclose(a, expected, rtol=0.0, atol=1e-6 * R * OMEGA**2)


def test_rod_angle_zero_at_dead_centres():
    assert rod_angle(0.0, R, L) == 0.0
    assert rod_angle(math.pi, R, L) == pytest.approx(0.0, abs=1e-15)


def test_rod_angle_sign():
    assert rod_angle(math.radians(90), R, L) > 0
    assert rod_angle(math.radians(270), R, L) < 0
    assert rod_angle(math.radians(450), R, L) > 0
    assert rod_angle(math.radians(630), R, L) < 0


def test_accepts_arrays_and_floats():
    assert isinstance(piston_displacement(0.5, R, L), float)
    out = piston_displacement(np.array([0.0, 0.5]), R, L)
    assert isinstance(out, np.ndarray) and out.shape == (2,)


def test_invalid_geometry():
    with pytest.raises(ValueError, match="greater than crank radius"):
        crank_ratio(0.05, 0.05)
    with pytest.raises(ValueError, match="positive"):
        crank_radius(-0.086)
    with pytest.raises(ValueError, match="positive"):
        angular_speed(0.0)


def test_exact_minus_series_at_90_degrees():
    th = math.pi / 2.0
    lam = R / L
    diff = piston_acceleration(th, R, L, OMEGA) - piston_acceleration_exact(
        th, R, L, OMEGA
    )
    expected = R * OMEGA**2 * lam * (1.0 / math.sqrt(1.0 - lam**2) - 1.0)
    assert diff == pytest.approx(expected, rel=1e-12)


def test_exact_matches_numerical_second_derivative():
    th = np.linspace(0.1, 6.0, 25)
    h = 1e-4
    x = lambda t: piston_displacement(t, R, L)  # noqa: E731
    numeric = (x(th + h) - 2 * x(th) + x(th - h)) / h**2 * OMEGA**2
    exact = piston_acceleration_exact(th, R, L, OMEGA)
    assert np.allclose(exact, numeric, rtol=1e-5, atol=1e-3)
