"""WE-01: kinematics and inertia (docs/worked_examples/WE-01.md)."""

import math

import pytest

from efa.loads.inertia import (
    centrifugal_force,
    inertia_force,
    reciprocating_mass,
    rod_mass_split,
)
from efa.loads.kinematics import (
    angular_speed,
    crank_radius,
    crank_ratio,
    piston_acceleration,
    piston_displacement,
    rod_angle,
)


def close(expected: float):
    return pytest.approx(expected, rel=1e-6, abs=1e-6 if expected == 0 else 0.0)


S, L, N_RPM = 0.086, 0.143, 6000.0
M_PISTON, M_PIN, M_RINGS, M_ROD, L_G = 0.40, 0.10, 0.03, 0.55, 0.040

R = crank_radius(S)
LAM = crank_ratio(R, L)
OMEGA = angular_speed(N_RPM)
M_ROD_A, M_ROT = rod_mass_split(M_ROD, L_G, L)
M_REC = reciprocating_mass(M_PISTON, M_PIN, M_RINGS, M_ROD_A)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (R, 0.043),
        (LAM, 0.3006993007),
        (OMEGA, 628.3185307180),
        (M_ROD_A, 0.1538461538),
        (M_REC, 0.6838461538),
        (M_ROT, 0.3961538462),
        (centrifugal_force(M_ROT, R, OMEGA), 6724.996599),
    ],
    ids=["r", "lambda", "omega", "m_rod_A", "m_rec", "m_rot", "F_c"],
)
def test_scalars(value, expected):
    assert value == close(expected)


@pytest.mark.parametrize(
    ("theta_deg", "x", "a_p", "beta_deg", "f_i"),
    [
        (0, 0.0, 22080.306573, 0.0, -15099.532726),
        (45, 0.015864311436, 12003.646423, 12.27631728, -8208.647439),
        (90, 0.049618183030, -5104.587004, 17.49960958, 3490.752189),
        (180, 0.086, -11871.132566, 0.0, 8118.028347),
    ],
)
def test_angles(theta_deg, x, a_p, beta_deg, f_i):
    th = math.radians(theta_deg)
    acc = piston_acceleration(th, R, L, OMEGA)
    assert piston_displacement(th, R, L) == close(x)
    assert acc == close(a_p)
    assert math.degrees(rod_angle(th, R, L)) == close(beta_deg)
    assert inertia_force(M_REC, acc) == close(f_i)
