# Engine loads (Phase 2)

Module: `efa.loads` (`kinematics.py`, `gas.py`, `inertia.py`, `cycle.py`).
All quantities are in SI units inside the package.

## Conventions

- Crank angle θ: 0° = intake TDC, 360° = firing TDC, one cycle is 0–720°.
- Forces along the cylinder axis and the rod force are positive toward the
  crank, so rod compression is positive and rod tension is negative.
- Rod angle β = arcsin(λ sin θ); β is negative for 180° < θ < 360°
  (modulo 360°).
- Cylinder pressure tables hold absolute pressure. Crankcase pressure is an
  input with default 101 325 Pa (1 atm).
- F_t is positive in the direction of crank rotation (driving torque); F_r is
  positive toward the crank axis.

## Equations

| ID | Equation | Symbols [units] |
|---|---|---|
| K1 | r = S/2; λ = r/l; ω = 2πn/60 | S stroke [m], l rod length centre to centre [m], n speed [rpm], r crank radius [m], λ [-], ω [rad/s] |
| K2 | x = r(1 − cos θ) + l[1 − √(1 − λ² sin² θ)] | x piston distance from TDC [m] (exact) |
| K3 | a_p = r ω² (cos θ + λ cos 2θ) | piston acceleration, positive toward crank [m/s²]; second-order series in λ |
| K3e | a_exact = r ω² [cos θ + λ cos 2θ / √(1 − λ² sin² θ) + λ³ sin² 2θ / (4 (1 − λ² sin² θ)^(3/2))] | exact piston acceleration [m/s²]; second derivative of K2 |
| K4 | β = arcsin(λ sin θ) | rod angle [rad] |
| L1 | A_p = π B²/4; F_g = (p_cyl − p_cc) A_p | B bore [m], p_cyl absolute cylinder pressure [Pa], p_cc crankcase pressure [Pa] |
| L2 | m_rod,A = m_rod l_G / l; m_rec = m_piston + m_pin + m_rings + m_rod,A; m_rot = m_rod − m_rod,A | l_G distance from big-end centre to rod centre of gravity [m]; masses [kg] |
| L3 | F_i = −m_rec a_p | inertia force [N] |
| L4 | F_p = F_g + F_i | net piston force [N] |
| L5 | F_rod = F_p / cos β; F_side = F_p tan β | rod axial force, side thrust [N] |
| L6 | F_t = F_rod sin(θ + β); F_r = F_rod cos(θ + β); T = F_t r | crankpin tangential and radial force [N], torque [N·m] |
| L7 | F_c = m_rot r ω² | rotating-mass centrifugal force [N], constant at constant ω |

## Validity limits

- In-line slider-crank without piston-pin offset; l > r.
- Constant crank speed; speed variation within the cycle is not modelled.
- K3 is a second-order series in λ. Terms of order λ³ and higher are
  neglected, so the error grows with λ. `evaluate_cycle` uses K3 and reports
  in its result note the largest deviation from the exact acceleration K3e on
  the evaluated grid (absolute, in % of the peak exact acceleration, and its
  angle); the values are stored as `a_series_max_dev`,
  `a_series_max_dev_pct` and `a_series_max_dev_theta_deg`. At θ = 90° the
  series exceeds the exact value by r ω² λ (1/√(1 − λ²) − 1).
- Two-mass rod model (L2): total mass and centre of gravity are preserved,
  the rod moment of inertia is not. Rod whip bending is not included.
- The centrifugal force F_c (L7) acts on the crankpin in addition to F_r; it
  is reported separately and is not added to F_r.
- Pin and ring masses may be zero when lumped into the piston mass;
  m_piston and m_rod must be positive.
- Single cylinder, four-stroke. Torsional vibration and multi-cylinder torque
  superposition are out of scope.
- Friction and ring-pack leakage are neglected.
- Between pressure-table points the pressure is interpolated linearly; the
  table resolution limits the accuracy of peak values.

## Outputs

`evaluate_cycle(spec, theta_deg)` returns a `CycleResult` with arrays over θ
(default grid: integer degrees 0..719) and the extremes of F_rod. `peak_load`
evaluates one angle with a given peak pressure. Each result carries a
`ResultNote` with the equation ids, validity notes, verify flags and the status
of the cylinder-pressure input.

Worked examples: [WE-01](../worked_examples/WE-01.md),
[WE-02](../worked_examples/WE-02.md).
