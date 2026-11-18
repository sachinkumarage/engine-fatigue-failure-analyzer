"""Connecting Rod page: section fatigue and shank buckling."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui_common import (  # noqa: E402
    basquin_inputs,
    common_marin_inputs,
    download_report,
    engine_spec,
    provenance,
    show_note,
)

from efa.components.common import Material
from efa.components.conrod import BucklingPlane, RodBuckling, RodSection, assess_conrod
from efa.fatigue.marin import endurance_limit, load_factor, size_factor
from efa.loads.cycle import evaluate_cycle
from efa.units import (
    gpa_to_pa,
    mm2_to_m2,
    mm4_to_m4,
    mm_to_m,
    mpa_to_pa,
    pa_to_mpa,
    sqrt_mm_to_sqrt_m,
)

st.title("Connecting Rod")
st.caption(
    "Axial fatigue per section (R1, rod whip bending excluded) and shank "
    "buckling in two planes. Defaults: WE-06 synthetic example (status: assumed)."
)

SECTIONS = pd.DataFrame(
    {
        "Section": ["Shank", "Small-end transition"],
        "A [mm²]": [240.0, 200.0],
        "K_t": [1.0, 1.8],
        "ρ [mm]": [None, 3.0],
        "√a [mm^0.5]": [None, 0.0600833],
        "q (direct)": [None, None],
    }
)
PLANES = pd.DataFrame(
    {"Plane": ["plane 1", "plane 2"], "I [mm⁴]": [18000.0, 8000.0], "K": [1.0, 0.5]}
)


def opt(value, convert=float):
    return None if pd.isna(value) else convert(value)


try:
    spec = engine_spec()
    cycle = evaluate_cycle(spec)

    with st.expander("Material", expanded=True):
        c1, c2, c3 = st.columns(3)
        s_ut = mpa_to_pa(c1.number_input("S_ut [MPa]", min_value=1.0, value=900.0))
        s_y = mpa_to_pa(c2.number_input("S_y [MPa]", min_value=1.0, value=750.0))
        e_mod = gpa_to_pa(c3.number_input("E [GPa]", min_value=1.0, value=205.0))
        m_status, m_src = provenance("rod_mat")
        material = Material("rod material", s_ut, s_y, m_status, m_src, e_mod)

    with st.expander("Endurance limit (axial loading)"):
        s_e_prime, common = common_marin_inputs("rod", s_ut, 4.51, -0.265)
        st.caption("k_b = 1 and k_c = 0.85 for axial loading (F3, F4).")
        factors = {**common, "k_b": size_factor(1.0, "axial"),
                   "k_c": load_factor("axial")}  # fmt: skip
        marin = endurance_limit(s_e_prime, factors)

    st.subheader("Sections")
    edited = st.data_editor(SECTIONS, num_rows="dynamic", hide_index=True, key="sec")
    sec_status, _ = provenance("rod_sec")
    sections = [
        RodSection(
            str(row["Section"]),
            mm2_to_m2(row["A [mm²]"]),
            float(row["K_t"]),
            opt(row["ρ [mm]"], mm_to_m),
            opt(row["√a [mm^0.5]"], sqrt_mm_to_sqrt_m),
            opt(row["q (direct)"]),
            sec_status,
        )
        for _, row in edited.dropna(subset=["Section", "A [mm²]", "K_t"]).iterrows()
    ]

    st.subheader("Buckling")
    c1, c2 = st.columns(2)
    b_area = mm2_to_m2(c1.number_input("Shank A [mm²]", min_value=0.01, value=240.0))
    b_len = mm_to_m(c2.number_input("Length L [mm]", min_value=0.01, value=143.0))
    planes_df = st.data_editor(PLANES, num_rows="dynamic", hide_index=True, key="pl")
    b_status, _ = provenance("rod_buck")
    planes = tuple(
        BucklingPlane(str(r["Plane"]), mm4_to_m4(r["I [mm⁴]"]), float(r["K"]))
        for _, r in planes_df.dropna().iterrows()
    )
    buckling = RodBuckling(b_area, b_len, e_mod, planes, b_status)

    with st.expander("Basquin constants (finite life when n_Goodman < 1)"):
        basquin = basquin_inputs("rod")

    result = assess_conrod(cycle, sections, material, marin, basquin, buckling)
except ValueError as exc:
    st.error(f"Invalid input: {exc}")
    st.stop()

name, n = result.governing
st.success(f"Governing: {name}, n = {n:.4g}")
st.metric("S_e (axial)", f"{pa_to_mpa(marin.S_e):.2f} MPa")
for w in result.note.warnings:
    st.warning(w)

st.subheader("Fatigue results")
st.dataframe(
    pd.DataFrame(
        [
            {
                "Section": s.section.name,
                "K_f": s.K_f,
                "σ_max,nom [MPa]": pa_to_mpa(s.sigma_max_nom),
                "σ_min,nom [MPa]": pa_to_mpa(s.sigma_min_nom),
                "σ_a [MPa]": pa_to_mpa(s.location.sigma_a),
                "σ_m [MPa]": pa_to_mpa(s.location.sigma_m),
                "Regime": s.location.assessment.regime,
                "n Goodman": s.location.assessment.n_goodman,
                "n Gerber": s.location.assessment.n_gerber,
                "n Elliptic": s.location.assessment.n_elliptic,
                "n_y Langer": s.location.assessment.n_yield,
                "N_f": s.location.life.N_f if s.location.life else None,
            }
            for s in result.sections
        ]
    ),
    hide_index=True,
)
st.subheader("Buckling results")
st.dataframe(
    pd.DataFrame(
        [
            {"Plane": p, "L_e/k": c.slenderness, "(L_e/k)₁": c.transition_slenderness,
             "Regime": c.regime, "σ_cr [MPa]": pa_to_mpa(c.sigma_cr),
             "P_cr [N]": c.P_cr, "n": c.n}
            for p, c in result.buckling
        ]
    ),
    hide_index=True,
)  # fmt: skip

st.subheader("Notched stress history")
history = pd.DataFrame({"θ [deg]": result.theta_deg})
for s in result.sections:
    history[f"{s.section.name} [MPa]"] = pa_to_mpa(s.sigma_history)
st.line_chart(history, x="θ [deg]")

show_note(result.note)
download_report(result, "conrod_assessment.md")
