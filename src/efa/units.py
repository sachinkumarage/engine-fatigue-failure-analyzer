"""Unit conversions between display units and internal SI units.

All functions accept floats or numpy arrays.
"""

import math

from numpy.typing import ArrayLike

from efa._checks import FloatOrArray, as_float_array, to_output

PA_PER_BAR = 1.0e5
M_PER_MM = 1.0e-3
KG_PER_G = 1.0e-3


def bar_to_pa(p_bar: ArrayLike) -> FloatOrArray:
    """Pressure [bar] to [Pa]."""
    return to_output(as_float_array("p_bar", p_bar) * PA_PER_BAR)


def pa_to_bar(p_pa: ArrayLike) -> FloatOrArray:
    """Pressure [Pa] to [bar]."""
    return to_output(as_float_array("p_pa", p_pa) / PA_PER_BAR)


def mm_to_m(length_mm: ArrayLike) -> FloatOrArray:
    """Length [mm] to [m]."""
    return to_output(as_float_array("length_mm", length_mm) * M_PER_MM)


def m_to_mm(length_m: ArrayLike) -> FloatOrArray:
    """Length [m] to [mm]."""
    return to_output(as_float_array("length_m", length_m) / M_PER_MM)


def rpm_to_rad_s(n_rpm: ArrayLike) -> FloatOrArray:
    """Rotational speed [rpm] to angular speed [rad/s]."""
    return to_output(as_float_array("n_rpm", n_rpm) * (2.0 * math.pi / 60.0))


def deg_to_rad(angle_deg: ArrayLike) -> FloatOrArray:
    """Angle [deg] to [rad]."""
    return to_output(as_float_array("angle_deg", angle_deg) * (math.pi / 180.0))


def rad_to_deg(angle_rad: ArrayLike) -> FloatOrArray:
    """Angle [rad] to [deg]."""
    return to_output(as_float_array("angle_rad", angle_rad) * (180.0 / math.pi))


def g_to_kg(mass_g: ArrayLike) -> FloatOrArray:
    """Mass [g] to [kg]."""
    return to_output(as_float_array("mass_g", mass_g) * KG_PER_G)


def kg_to_g(mass_kg: ArrayLike) -> FloatOrArray:
    """Mass [kg] to [g]."""
    return to_output(as_float_array("mass_kg", mass_kg) / KG_PER_G)


PA_PER_MPA = 1.0e6
PA_PER_GPA = 1.0e9


def mpa_to_pa(s_mpa: ArrayLike) -> FloatOrArray:
    """Stress [MPa] to [Pa]."""
    return to_output(as_float_array("s_mpa", s_mpa) * PA_PER_MPA)


def pa_to_mpa(s_pa: ArrayLike) -> FloatOrArray:
    """Stress [Pa] to [MPa]."""
    return to_output(as_float_array("s_pa", s_pa) / PA_PER_MPA)


def gpa_to_pa(s_gpa: ArrayLike) -> FloatOrArray:
    """Modulus or stress [GPa] to [Pa]."""
    return to_output(as_float_array("s_gpa", s_gpa) * PA_PER_GPA)


def mm2_to_m2(area_mm2: ArrayLike) -> FloatOrArray:
    """Area [mm²] to [m²]."""
    return to_output(as_float_array("area_mm2", area_mm2) * M_PER_MM**2)


def mm4_to_m4(i_mm4: ArrayLike) -> FloatOrArray:
    """Second moment of area [mm⁴] to [m⁴]."""
    return to_output(as_float_array("i_mm4", i_mm4) * M_PER_MM**4)


def sqrt_mm_to_sqrt_m(value: ArrayLike) -> FloatOrArray:
    """Neuber constant √a [mm^0.5] to [m^0.5]."""
    return to_output(as_float_array("value", value) * math.sqrt(M_PER_MM))
