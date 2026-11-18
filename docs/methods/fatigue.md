# Fatigue (Phase 3)

Modules: `efa.stress.nominal`, `efa.stress.notch`, `efa.fatigue.marin`,
`efa.fatigue.mean_stress`, `efa.fatigue.basquin`. SI units inside the package
(Pa, m, N). Tensile stress is positive.

Relations marked *(verify)* come from [SRC-SHIGLEY](../sources.md) and set a
verify flag in the result note until the owner has checked them.

## Equations

| ID | Equation | Symbols [units] / notes |
|---|---|---|
| S1 | σ = F/A; σ_b = M c / I; τ = T ρ / J | stresses [Pa]; F [N]; M, T [N·m]; A [m²]; I, J [m⁴]; c, ρ [m] |
| S2 | σ_a = (σ_max − σ_min)/2; σ_m = (σ_max + σ_min)/2 | from cycle extremes or from a history (max/min) |
| S3 | σ′ = √(σ² + 3τ²) | von Mises; applied separately to amplitude and mean (proportional loading) |
| N1 | K_f = 1 + q (K_t − 1) | K_t ≥ 1; 0 ≤ q ≤ 1 |
| N2 | q = 1 / (1 + √a / √ρ) | √a [m^0.5] from a cited source; ρ [m]; or q entered directly *(verify)* |
| F1 | S_e = k_a k_b k_c k_d k_e k_f S_e′ | every factor carries value, basis, status, source id, verify *(verify)* |
| F2 | k_a = a (S_ut / 1 MPa)^b | a, b from a cited table (MPa basis) *(verify)* |
| F3 | k_b = 1.24 d^−0.107 (2.79 ≤ d ≤ 51 mm); 1.51 d^−0.157 (51 < d ≤ 254 mm); 1 for axial | d in mm; raises outside range *(verify)* |
| F4 | k_c = 1 (bending), 0.85 (axial), 0.59 (torsion) | *(verify)* |
| F5 | k_e = 1 − 0.08 z_a | z_a standard normal variate *(verify)* |
| F6 | S_e′ = 0.5 S_ut (S_ut ≤ 1400 MPa); 700 MPa otherwise | steels, estimate only, status cited (verify) |
| M1 | n = 1 / (σ_a/S_e + σ_m/S_ut) | Goodman, σ_m > 0 *(verify)* |
| M2 | n = ½ (S_ut/σ_m)² (σ_a/S_e) [−1 + √(1 + (2 σ_m S_e / (S_ut σ_a))²)] | Gerber, σ_m > 0 *(verify)* |
| M3 | n = √(1 / ((σ_a/S_e)² + (σ_m/S_y)²)) | ASME elliptic, σ_m > 0 *(verify)* |
| M4 | n_y = S_y / (σ_a + \|σ_m\|) | Langer first-cycle yield, always reported *(verify)* |
| M5 | n = S_e / σ_a for σ_m ≤ 0 | all three criteria; decision D8 |
| B1 | σ_a = σ′_f (2N_f)^b | σ′_f [Pa], b < 0 |
| B2 | σ_a = (σ′_f − σ_m)(2N_f)^b; N_f = ½ (σ_a / (σ′_f − σ_m))^(1/b) | Morrow; σ_m < σ′_f *(verify)* |

## Procedure

1. Endurance limit: S_e′ (F6 estimate or test value) times the six Marin
   factors (F1). All six factors must be given; each carries its basis and
   status, and the result note lists them.
2. Notch: q from N2 or entered directly, K_f from N1.
3. Notched stresses: σ_a = K_f σ_a,nom and σ_m = K_f σ_m,nom (decision D9).
4. `mean_stress.assess` evaluates M1–M3 (σ_m > 0) or M5 (σ_m ≤ 0) and M4.
   If K_f and the largest absolute nominal stress σ_max are given and
   K_f |σ_max| > S_y, the note warns "local yielding at notch; mean-stress
   treatment needs review (verify)".
5. Finite life: `basquin.life` and `basquin.strength` (B1/B2). The constants
   carry their valid life range; outside it the value is kept and the note
   warns "outside the stated data range".

## Validity limits

- High-cycle, constant-amplitude, uniaxial or proportional loading.
- No cumulative damage, no multiaxial non-proportional criteria.
- F2–F6 apply to steels; F3 applies to round sections within 2.79–254 mm.
- K_f applied to the mean stress is conservative while the notch stays
  elastic; local yielding relaxes the mean stress (warning raised).
- Safety factors assume proportional increase of σ_a and σ_m.

Worked examples: [WE-03](../worked_examples/WE-03.md),
[WE-04](../worked_examples/WE-04.md).
