"""Slider-crank kinematics (equations K1 to K4).

Conventions (docs/decisions/0001-phase-0-decisions.md):
    θ is the crank angle from TDC [rad]; the piston acceleration is positive
    toward the crank; the rod angle β has the sign of sin θ.
"""

import math

import numpy as np
from numpy.typing import ArrayLike

from efa._checks import FloatOrArray, as_float_array, require_positive, to_output


def _check_rod(r: float, l_rod: float) -> tuple[float, float]:
    r = require_positive("r", r)
    l_rod = require_positive("l_rod", l_rod)
    if l_rod <= r:
        raise ValueError(
            f"Rod length l ({l_rod} m) must be greater than crank radius r ({r} m)."
        )
    return r, l_rod


def crank_radius(stroke: float) -> float:
    """K1: crank radius r = S / 2.

    Symbols:
        S (stroke): piston stroke [m].
        r: crank radius [m].

    Validity: S > 0.
    """
    return require_positive("stroke", stroke) / 2.0


def crank_ratio(r: float, l_rod: float) -> float:
    """K1: crank-to-rod ratio λ = r / l.

    Symbols:
        r: crank radius [m].
        l (l_rod): rod length, centre to centre [m].
        λ: crank ratio [-].

    Validity: 0 < r < l.
    """
    r, l_rod = _check_rod(r, l_rod)
    return r / l_rod


def angular_speed(n_rpm: float) -> float:
    """K1: crank angular speed ω = 2π n / 60.

    Symbols:
        n (n_rpm): crankshaft speed [rpm].
        ω: angular speed [rad/s].

    Validity: n > 0; constant speed over the cycle.
    """
    return 2.0 * math.pi * require_positive("n_rpm", n_rpm) / 60.0


def piston_displacement(theta: ArrayLike, r: float, l_rod: float) -> FloatOrArray:
    """K2: piston distance from TDC, exact.

    x = r (1 − cos θ) + l [1 − √(1 − λ² sin² θ)]

    Symbols:
        θ (theta): crank angle from TDC [rad].
        r: crank radius [m].
        l (l_rod): rod length, centre to centre [m].
        λ = r / l [-].
        x: piston distance from TDC, positive toward the crank [m].

    Validity: in-line slider-crank without pin offset; 0 < r < l.
    """
    r, l_rod = _check_rod(r, l_rod)
    th = as_float_array("theta", theta)
    lam = r / l_rod
    x = r * (1.0 - np.cos(th)) + l_rod * (1.0 - np.sqrt(1.0 - (lam * np.sin(th)) ** 2))
    return to_output(x)


def piston_acceleration(
    theta: ArrayLike, r: float, l_rod: float, omega: float
) -> FloatOrArray:
    """K3: piston acceleration, second-order series in λ.

    a_p = r ω² (cos θ + λ cos 2θ)

    Symbols:
        θ (theta): crank angle from TDC [rad].
        r: crank radius [m].
        l (l_rod): rod length, centre to centre [m].
        ω (omega): constant crank angular speed [rad/s].
        λ = r / l [-].
        a_p: piston acceleration, positive toward the crank [m/s²].

    Validity: constant ω; in-line slider-crank without pin offset; 0 < r < l.
    Terms of order λ³ and higher are neglected, so the error grows with λ.
    """
    r, l_rod = _check_rod(r, l_rod)
    omega = require_positive("omega", omega)
    th = as_float_array("theta", theta)
    lam = r / l_rod
    return to_output(r * omega**2 * (np.cos(th) + lam * np.cos(2.0 * th)))


def rod_angle(theta: ArrayLike, r: float, l_rod: float) -> FloatOrArray:
    """K4: connecting-rod angle β = arcsin(λ sin θ).

    Symbols:
        θ (theta): crank angle from TDC [rad].
        r: crank radius [m].
        l (l_rod): rod length, centre to centre [m].
        λ = r / l [-].
        β: rod angle to the cylinder axis [rad]; negative where sin θ < 0
            (180° < θ < 360° modulo 360°).

    Validity: in-line slider-crank without pin offset; 0 < r < l.
    """
    r, l_rod = _check_rod(r, l_rod)
    th = as_float_array("theta", theta)
    return to_output(np.arcsin((r / l_rod) * np.sin(th)))
