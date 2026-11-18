# Connecting-rod bolts (Phase 4)

Module: `efa.components.conrod_bolt`. SI units. Bolt and member forces are
tension positive.

## Equations

| ID | Equation | Symbols [units] / notes |
|---|---|---|
| J1 | C = k_b / (k_b + k_m) | stiffness ratio [-]; k_b bolt, k_m members [N/m] |
| J2 | F_b = C P + F_i; F_m = (1 − C) P − F_i | P external load per bolt [N], F_i preload [N] |
| J3 | σ_a = C P / (2 A_t); σ_m = σ_a + F_i / A_t | A_t tensile stress area [m²]; load cycles 0 → P |
| J4 | n_p = S_p A_t / (C P + F_i) | proof-load factor; S_p proof strength [Pa] *(verify)* |
| J5 | n_0 = F_i / (P (1 − C)) | joint separation factor *(verify)* |
| J6 | n_f = S_e (S_ut − σ_i) / (S_ut σ_a + S_e (σ_m − σ_i)), σ_i = F_i/A_t | Goodman along the preload load line *(verify)* |
| J7 | P = [\|F_rod,min\| + (m_rot − m_cap) r ω²] / n_b | external load per big-end bolt at TDC *(verify)* |

All relations are from SRC-SHIGLEY (verify); J7 applies the bolt-joint model
to the big end.

## Load model (J7)

The big-end bolts are loaded in tension at gas-exchange TDC, where the rod
force is most tensile (F_rod,min, the most negative rod force of the cycle).
In addition, the rotating part of the rod outside the cap, m_rot − m_cap,
pulls on the cap with its centrifugal force. The cap's own inertia is carried
by the cap and not by the bolts. The total is shared equally by n_b bolts.

## Fatigue (J6)

The bolt endurance limit S_e is the fully corrected value for rolled or cut
threads from a cited table; no Marin factors or K_f are applied again. J6 is
the Goodman criterion along the preload load line, which starts at
σ_i = F_i/A_t; it replaces M1–M3 for bolts.

## Validity limits

- Linear-elastic joint, not separated (n_0 > 1); otherwise J2–J6 do not apply.
- Constant preload; no embedding loss or thermal effects.
- Bolt bending from big-end ovalisation and joint-face slip are not modelled.
- Bolt data (S_p, S_e, stiffnesses) must come from cited tables or tests.

Worked example: [WE-08](../worked_examples/WE-08.md).
