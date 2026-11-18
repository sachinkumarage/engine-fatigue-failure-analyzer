"""Bolts page: connecting-rod big-end bolt joint."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui_common import download_report, engine_spec, provenance, show_note  # noqa: E402

from efa.components.conrod_bolt import BoltJoint, assess_bolts
from efa.loads.cycle import evaluate_cycle
from efa.units import mm2_to_m2, mpa_to_pa, pa_to_mpa

st.title("Bolts")
st.caption(
    "Big-end bolt joint: stiffness ratio, preload, proof load, separation and "
    "fatigue (J1–J7). Defaults: WE-08 synthetic example (status: assumed); "
    "verify bolt data against cited tables."
)

try:
    spec = engine_spec()
    cycle = evaluate_cycle(spec)
    c1, c2, c3, c4 = st.columns(4)
    n_b = c1.number_input("Number of bolts n_b", min_value=1, value=2, step=1)
    a_t = c2.number_input("A_t [mm²]", min_value=0.1, value=61.2)
    m_cap = c3.number_input("Cap mass m_cap [kg]", min_value=0.0, value=0.10,
                            format="%.3f")  # fmt: skip
    f_i = c4.number_input("Preload F_i [kN]", min_value=0.001, value=30.0)
    c1, c2 = st.columns(2)
    k_b = c1.number_input("Bolt stiffness k_b [N/m]", min_value=1.0, value=3.0e8,
                          format="%.4g")  # fmt: skip
    k_m = c2.number_input("Member stiffness k_m [N/m]", min_value=1.0, value=1.2e9,
                          format="%.4g")  # fmt: skip
    c1, c2, c3, c4 = st.columns(4)
    s_p = c1.number_input("S_p [MPa]", min_value=1.0, value=830.0)
    s_ut = c2.number_input("S_ut [MPa]", min_value=1.0, value=1040.0)
    s_y = c3.number_input("S_y [MPa]", min_value=1.0, value=940.0)
    s_e = c4.number_input("S_e (fully corrected) [MPa]", min_value=1.0, value=162.0)
    status, src = provenance("bolt")
    joint = BoltJoint(
        int(n_b), mm2_to_m2(a_t), k_b, k_m, f_i * 1e3, mpa_to_pa(s_p),
        mpa_to_pa(s_ut), mpa_to_pa(s_y), mpa_to_pa(s_e), m_cap, status,
        source_id=src,
    )  # fmt: skip
    result = assess_bolts(cycle, spec, joint)
except ValueError as exc:
    st.error(f"Invalid input: {exc}")
    st.stop()

name, n = result.governing
st.success(f"Governing: {name}, n = {n:.4g}")
for w in result.note.warnings:
    st.warning(w)
c1, c2, c3 = st.columns(3)
c1.metric("n_p (proof)", f"{result.n_p:.3f}")
c2.metric("n_0 (separation)", f"{result.n_0:.3f}")
c3.metric("n_f (fatigue, J6)", f"{result.n_f:.3f}")

st.dataframe(
    pd.DataFrame(
        {
            "Quantity": ["|F_rod,min| [N]", "(m_rot − m_cap) r ω² [N]",
                         "P total [N]", "P per bolt [N]", "C [-]", "F_b max [N]",
                         "F_m [N]", "σ_a [MPa]", "σ_m [MPa]"],
            "Value": [result.F_rod_min_abs, result.rotating_load, result.P_total,
                      result.P, result.C, result.F_b_max, result.F_m,
                      pa_to_mpa(result.sigma_a), pa_to_mpa(result.sigma_m)],
        }
    ),
    hide_index=True,
)  # fmt: skip
show_note(result.note)
download_report(result, "bolt_assessment.md")
