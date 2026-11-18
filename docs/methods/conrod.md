# Connecting rod (Phase 4)

Module: `efa.components.conrod`. SI units. Stress is tension positive; the rod
force F_rod is compression positive (Phase 2 convention).

## Equations

| ID | Equation | Symbols [units] / notes |
|---|---|---|
| R1 | σ(θ) = −F_rod(θ) / A_s | A_s section area [m²]; axial only (whip bending excluded, D5) |

Reused: N1, N2 (notch), S2 (amplitude and mean), M1–M5 (mean stress), B2
(finite life), C1–C3 (buckling), F1–F6 (endurance limit).

## Procedure (`assess_conrod`)

1. Cycle from `evaluate_cycle` on the 0..719 integer-degree grid.
2. For each section: nominal history R1 → K_f from N1 (q from N2 or entered
   directly) → notched history K_f σ(θ) (D9) → S2 → `mean_stress.assess`.
3. If n_Goodman < 1, Basquin/Morrow life (B2) with the given constants;
   otherwise "no finite-life calculation (n ≥ 1)".
4. Local-yield warning when the notched σ_a + |σ_m| > S_y.
5. Buckling: C1–C3 in every plane with the maximum compressive F_rod of the
   cycle, the shank area, length and E, and the plane's I and K.
6. Governing item: lowest of the section fatigue factors (Goodman, or M5 for
   compressive mean), the Langer yield factors and the buckling factors.

## Validity limits

- Axial stress only. Rod whip (inertia bending of the shank) is excluded (D5).
- The whole F_rod is applied at every section: the mass above the section is
  not removed, which is conservative in tension.
- Big-end and small-end bore stresses (ovalisation, interference fits) are not
  modelled.
- Buckling planes need their own effective-length factor K; it must be
  justified by the end conditions of the rod in that plane.
- Relations from SRC-SHIGLEY carry verify flags (docs/sources.md).

Worked example: [WE-06](../worked_examples/WE-06.md).
