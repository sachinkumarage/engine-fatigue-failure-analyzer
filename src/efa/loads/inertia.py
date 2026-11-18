"""Inertia loads from the two-mass model (equations L2, L3, L7)."""

from numpy.typing import ArrayLike

from efa._checks import (
    FloatOrArray,
    as_float_array,
    require_non_negative,
    require_positive,
    to_output,
)


def rod_mass_split(m_rod: float, l_g: float, l_rod: float) -> tuple[float, float]:
    """L2: split the rod mass into reciprocating and rotating parts.

    m_rod,A = m_rod l_G / l;   m_rot = m_rod − m_rod,A

    Symbols:
        m_rod: total connecting-rod mass [kg].
        l_G (l_g): distance from big-end centre to rod centre of gravity [m].
        l (l_rod): rod length, centre to centre [m].
        m_rod,A: rod mass assigned to the small end (reciprocating) [kg].
        m_rot: rod mass assigned to the big end (rotating) [kg].

    Validity: 0 < l_G < l. The two-mass model preserves total mass and centre
    of gravity but not the rod moment of inertia.

    Returns:
        (m_rod_A, m_rot) in kg.
    """
    m_rod = require_positive("m_rod", m_rod)
    l_g = require_positive("l_g", l_g)
    l_rod = require_positive("l_rod", l_rod)
    if l_g >= l_rod:
        raise ValueError(f"l_g ({l_g} m) must be less than rod length l ({l_rod} m).")
    m_rod_a = m_rod * l_g / l_rod
    return m_rod_a, m_rod - m_rod_a


def reciprocating_mass(
    m_piston: float, m_pin: float, m_rings: float, m_rod_a: float
) -> float:
    """L2: reciprocating mass m_rec = m_piston + m_pin + m_rings + m_rod,A.

    Symbols:
        m_piston, m_pin, m_rings: piston, gudgeon pin and ring-pack masses [kg].
        m_rod,A (m_rod_a): reciprocating share of the rod mass [kg].
        m_rec: total reciprocating mass [kg].

    Validity: m_piston > 0 and m_rod,A > 0; m_pin >= 0 and m_rings >= 0 (they
    may be lumped into m_piston); two-mass rod model.
    """
    return (
        require_positive("m_piston", m_piston)
        + require_non_negative("m_pin", m_pin)
        + require_non_negative("m_rings", m_rings)
        + require_positive("m_rod_a", m_rod_a)
    )


def inertia_force(m_rec: float, a_p: ArrayLike) -> FloatOrArray:
    """L3: reciprocating inertia force F_i = −m_rec a_p.

    Symbols:
        m_rec: reciprocating mass [kg].
        a_p: piston acceleration, positive toward the crank [m/s²].
        F_i: inertia force on the piston, positive toward the crank [N].

    Validity: rigid masses; acceleration from K3.
    """
    m_rec = require_positive("m_rec", m_rec)
    return to_output(-m_rec * as_float_array("a_p", a_p))


def centrifugal_force(m_rot: float, r: float, omega: float) -> float:
    """L7: rotating-mass centrifugal force F_c = m_rot r ω².

    Symbols:
        m_rot: rotating mass at the crankpin [kg].
        r: crank radius [m].
        ω (omega): crank angular speed [rad/s].
        F_c: centrifugal force, radially outward from the crank axis [N].

    Validity: constant ω, so F_c is constant over the cycle.
    """
    m_rot = require_positive("m_rot", m_rot)
    r = require_positive("r", r)
    omega = require_positive("omega", omega)
    return m_rot * r * omega**2
