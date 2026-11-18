"""Slider-crank kinematics (equations K1 to K4 and K3e).

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


def piston_acceleration_exact(
    theta: ArrayLike, r: float, l_rod: float, omega: float
) -> FloatOrArray:
    """K3e: exact piston acceleration at constant crank speed.

    a_exact = r ω² [cos θ + λ cos 2θ / √(1 − λ² sin² θ)
                    + λ³ sin² 2θ / (4 (1 − λ² sin² θ)^(3/2))]

    Symbols:
        θ (theta): crank angle from TDC [rad].
        r: crank radius [m].
        l (l_rod): rod length, centre to centre [m].
        ω (omega): constant crank angular speed [rad/s].
        λ = r / l [-].
        a_exact: piston acceleration, positive toward the crank [m/s²].

    Validity: constant ω; in-line slider-crank without pin offset; 0 < r < l.
    Source: second time derivative of K2.
    """
    r, l_rod = _check_rod(r, l_rod)
    omega = require_positive("omega", omega)
    th = as_float_array("theta", theta)
    lam = r / l_rod
    root = 1.0 - (lam * np.sin(th)) ** 2
    bracket = (
        np.cos(th)
        + lam * np.cos(2.0 * th) / np.sqrt(root)
        + lam**3 * np.sin(2.0 * th) ** 2 / (4.0 * root**1.5)
    )
    return to_output(r * omega**2 * bracket)


def series_acceleration_deviation(
    theta: ArrayLike, r: float, l_rod: float, omega: float
) -> tuple[float, float, float]:
    """Largest deviation of the K3 series from the exact K3e acceleration.

    dev = max |a_exact − a_series| over the given angles;
    pct = 100 dev / max |a_exact|.

    Symbols:
        θ (theta): crank angles [rad], 1-D grid.
        r, l (l_rod): crank radius and rod length [m].
        ω (omega): crank angular speed [rad/s].

    Validity: the result describes only the evaluated grid.

    Returns:
        (dev [m/s²], pct [%], θ at the maximum deviation [rad]).
    """
    th = np.atleast_1d(as_float_array("theta", theta))
    exact = np.atleast_1d(piston_acceleration_exact(th, r, l_rod, omega))
    series = np.atleast_1d(piston_acceleration(th, r, l_rod, omega))
    diff = np.abs(exact - series)
    i = int(np.argmax(diff))
    peak = float(np.max(np.abs(exact)))
    return float(diff[i]), 100.0 * float(diff[i]) / peak, float(th[i])


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
