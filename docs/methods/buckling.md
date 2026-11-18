# Column buckling (Phase 3)

Module: `efa.buckling`. SI units. Load P is positive in compression.

| ID | Equation | Symbols [units] / notes |
|---|---|---|
| C1 | σ_cr = π² E / (L_e/k)²; k = √(I/A); L_e = K L | Euler; E [Pa], I [m⁴], A [m²], L [m], K [-] *(verify)* |
| C2 | σ_cr = S_y − (S_y² / (4π² E)) (L_e/k)² | Johnson, for L_e/k < (L_e/k)₁ *(verify)* |
| C3 | (L_e/k)₁ = √(2π² E / S_y) | transition; σ_cr = S_y/2 there *(verify)* |

`column_check(A, I, L, K, E, S_y, P)` returns k, L_e/k, (L_e/k)₁, the regime
("Euler" or "Johnson"), σ_cr, P_cr = σ_cr A and n = P_cr / P. For P ≤ 0 the
column is not in compression and n = inf with a note.

## Validity limits

- Straight, prismatic, centrally loaded column; no eccentricity, initial
  crookedness or combined bending.
- Check each principal plane separately with its own I and K. For a
  connecting rod the effective-length factor differs between the plane of
  rotation and the perpendicular plane; K must be justified by the end
  conditions.
- Relations from [SRC-SHIGLEY](../sources.md) (verify).

Worked example: [WE-05](../worked_examples/WE-05.md).
