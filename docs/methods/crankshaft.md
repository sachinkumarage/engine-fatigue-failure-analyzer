# Crankshaft (Phase 4)

Module: `efa.components.crankshaft`. SI units. Stress is tension positive.

## Model (decision D4)

A single crank throw between two main bearings A (free end) and B (drive
side), span L_b, statically determinate and symmetric about the crankpin
centre. The output torque is taken off at the drive-side journal beyond B.
The rod force acts at the crankpin centre with components F_r (radial,
toward the crank axis) and F_t (tangential) from L6; the rotating rod mass
adds F_c outward (L7).

## Equations

| ID | Equation | Symbols [units] / notes |
|---|---|---|
| X1 | F_R(θ) = F_r(θ) − F_c | total radial crankpin load, toward the crank axis [N]; web and counterweight masses excluded |
| X2 | M_pin(θ) = (F_R/2)(L_b/2 − s_p) | crankpin fillet bending moment [N·m]; s_p axial distance pin centre to fillet [m] |
| X3 | T_pin(θ) = F_t(θ) r / 2 | crankpin torsion [N·m] (derivation below) |
| X4 | M_j(θ) = (F_R/2) s_j; T_j(θ) = F_t(θ) r | drive-side main-journal fillet; s_j bearing centre to fillet [m] |
| X5 | σ_b = K_f,b · 32 M / (π d³); τ = K_f,t · 16 T / (π d³) | fillet point in the crank plane facing the crank axis |

## Derivation of X3

Bearing reactions. By symmetry each bearing carries half of the crankpin
load: F_R/2 radially and F_t/2 tangentially. Both reactions act on the crank
axis.

Free-end side of the crankpin. Cut the crankpin between the free-end web
and the load point and keep the free-end part (journal A and the web). The
only external load on it is the bearing reaction F_t/2 at the crank axis, at
distance r from the crankpin axis. Moment equilibrium about the crankpin
axis gives

    T_pin = (F_t / 2) · r.

Drive side of the crankpin. Keep the drive-side part (web, journal B and the
output shaft). It carries the bearing reaction F_t/2 at the crank axis and
the output (resisting) torque F_t r about the crank axis. About the crankpin
axis:

    T_pin = F_t r − (F_t / 2) r = F_t r / 2.

Both sides give the same torque, T_pin = F_t r / 2 (tested in
`tests/unit/test_components.py::test_x3_symmetry`). The drive-side journal
between the web and bearing B carries the full torque about the crank axis,
because the free-end reaction passes through the axis: T_j = F_t r (X4).

Bending. The bending moment at a crankpin fillet at distance s_p from the pin
centre is the bearing reaction times its lever arm: (F_R/2)(L_b/2 − s_p) (X2).
At the journal fillet, s_j from bearing B: (F_R/2) s_j (X4).

## Fillet point and stresses

The assessed point lies in the crank plane, at the fillet on the pin side
facing the crank axis. The tangential force gives bending about an axis
through this point, so its bending stress is zero there (neutral axis); only
the radial bending M and the torsion T act. X5 applies separate notch
factors K_f,b and K_f,t (D4), each from N1 with q from N2.

## Fatigue procedure

S2 is applied separately to the σ and τ histories, the amplitudes and means
are combined with S3 (von Mises), then `mean_stress.assess` (M1–M4) and, only
if n_Goodman < 1, Basquin/Morrow (B2). σ and τ extrema are taken
independently; non-proportional loading is not modelled.

## Validity limits

- Single throw, statically determinate; multi-throw continuity and bearing
  misalignment are not modelled.
- Torsional vibration is excluded.
- Crank-web and counterweight masses are excluded from F_R.
- K_t values are inputs, to be replaced by FEA results in Phase 5.
- Relations from SRC-SHIGLEY carry verify flags.

Worked example: [WE-07](../worked_examples/WE-07.md).
