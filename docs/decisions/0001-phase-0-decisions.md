# 0001 — Phase 0 decisions

Status: accepted

## Decisions

- **Units:** internal units are SI (m, N, Pa, kg, s, rad); the user interface
  converts to display units.
- **Sign conventions:** crank angle θ: 0° = intake TDC, 360° = firing TDC,
  range 0–720°. Forces are positive toward the crank (rod compression
  positive). Inertia force F_i = −m_rec · a_p.
- **Crankcase pressure** is an input, default 1 atm.
- **Crankshaft v1:** statically determinate single-throw beam between two main
  bearings; separate bending and torsion K_t; von Mises equivalent stress.
- **Out of scope for v1:** torsional vibration, multi-cylinder torque
  superposition, rod whip bending, two-stroke engines, speed variation within
  a cycle.
- **Marin factors** k_a to k_f (k_f miscellaneous, used for cited
  surface-treatment factors only).
- **Residual stress** enters as effective mean stress, with a
  subsurface-initiation warning for hardened cases.
- **Compressive mean stress:** n = S_e / σ_a plus yield check.
- **Finite life:** Basquin with Morrow mean-stress correction.
- **Connecting-rod bolt joint model** (stiffness ratio, preload) in Phase 4.
- **Dependencies:** standard library, numpy, scipy; dataclasses for
  validation; `string.Template` for HTML reports.
- **Versioning:** Phase N → 0.N.0, release 1.0.0; one local commit per version.
