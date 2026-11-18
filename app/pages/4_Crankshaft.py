"""Crankshaft page: crankpin and main-journal fillet fatigue."""

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
from efa.components.crankshaft import (
    FILLETS,
    JOURNAL,
    PIN,
    CrankGeometry,
    FilletNotch,
    assess_crankshaft,
)
from efa.fatigue.marin import MarinFactor, endurance_limit, size_factor
from efa.loads.cycle import evaluate_cycle
from efa.provenance import Status
from efa.sources import SRC_SHIGLEY
from efa.units import mm_to_m, mpa_to_pa, pa_to_mpa, sqrt_mm_to_sqrt_m

st.title("Crankshaft")
st.caption(
    "Single-throw statically determinate beam between two main bearings. "
    "Defaults: WE-07 synthetic example (status: assumed)."
)


def fillet_inputs(label: str, key: str) -> FilletNotch:
    st.markdown(f"**{label}**")
    c1, c2, c3 = st.columns(3)
    ktb = c1.number_input("K_t bending", min_value=1.0, value=2.2, key=f"{key}_b")
    ktt = c2.number_input("K_t torsion", min_value=1.0, value=1.6, key=f"{key}_t")
    rho = c3.number_input("ρ [mm]", min_value=0.01, value=2.5, key=f"{key}_r")
    return FilletNotch(ktb, ktt, mm_to_m(rho))


try:
    spec = engine_spec()
    cycle = evaluate_cycle(spec)

    with st.expander("Geometry and fillets", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        l_b = c1.number_input("L_b [mm]", min_value=0.1, value=90.0)
        s_p = c2.number_input("s_p [mm]", min_value=0.01, value=12.0)
        d_pin = c3.number_input("d_pin [mm]", min_value=0.1, value=48.0)
        s_j = c4.number_input("s_j [mm]", min_value=0.01, value=10.0)
        d_j = c5.number_input("d_journal [mm]", min_value=0.1, value=55.0)
        pin_notch = fillet_inputs("Crankpin fillet", "pin")
        jou_notch = fillet_inputs("Main journal fillet (drive side)", "jou")
        sqrt_a = st.number_input("Neuber √a [mm^0.5]", min_value=1e-6, value=0.0600833,
                                 format="%.6f")  # fmt: skip
        st.caption("K_t values are inputs; FEA values replace them in Phase 5.")
        g_status, _ = provenance("crank_geo")
        geometry = CrankGeometry(
            mm_to_m(l_b), mm_to_m(s_p), mm_to_m(d_pin), mm_to_m(s_j), mm_to_m(d_j),
            pin_notch, jou_notch, sqrt_mm_to_sqrt_m(sqrt_a), g_status,
        )  # fmt: skip

    with st.expander("Material", expanded=True):
        c1, c2 = st.columns(2)
        s_ut = mpa_to_pa(c1.number_input("S_ut [MPa]", min_value=1.0, value=800.0))
        s_y = mpa_to_pa(c2.number_input("S_y [MPa]", min_value=1.0, value=600.0))
        m_status, m_src = provenance("crank_mat")
        material = Material("crankshaft material", s_ut, s_y, m_status, m_src)

    with st.expander("Endurance limit (combined bending and torsion)"):
        s_e_prime, common = common_marin_inputs("crank", s_ut, 1.58, -0.085)
        st.caption("k_b from F3 with each fillet diameter; k_c = 1 (von Mises, S3).")
        k_c = MarinFactor(1.0, "k_c = 1, combined loading via von Mises (S3)",
                          Status.CITED, SRC_SHIGLEY, True)  # fmt: skip
        marin = {
            name: endurance_limit(
                s_e_prime, {**common, "k_b": size_factor(d, "bending"), "k_c": k_c}
            )
            for name, d in ((PIN, geometry.d_pin), (JOURNAL, geometry.d_journal))
        }

    with st.expander("Basquin constants (finite life when n_Goodman < 1)"):
        basquin = basquin_inputs("crank")

    result = assess_crankshaft(cycle, geometry, material, marin, basquin)
except ValueError as exc:
    st.error(f"Invalid input: {exc}")
    st.stop()

name, n = result.governing
st.success(f"Governing: {name}, n = {n:.4g}")
for w in result.note.warnings:
    st.warning(w)

rows = {}
for f in result.fillets:
    loc, a = f.location, f.location.assessment
    rows[f.name] = {
        "q": f.q,
        "K_f,b": f.K_f_b,
        "K_f,t": f.K_f_t,
        "S_e [MPa]": pa_to_mpa(loc.S_e),
        "M max [N·m]": f.M_max,
        "M min [N·m]": f.M_min,
        "T max [N·m]": f.T_max,
        "T min [N·m]": f.T_min,
        "σ_a [MPa]": pa_to_mpa(loc.sigma_a),
        "σ_m [MPa]": pa_to_mpa(loc.sigma_m),
        "τ_a [MPa]": pa_to_mpa(loc.tau_a),
        "τ_m [MPa]": pa_to_mpa(loc.tau_m),
        "σ′_a [MPa]": pa_to_mpa(loc.sigma_eq_a),
        "σ′_m [MPa]": pa_to_mpa(loc.sigma_eq_m),
        "n Goodman": a.n_goodman,
        "n Gerber": a.n_gerber,
        "n Elliptic": a.n_elliptic,
        "n_y Langer": a.n_yield,
        "N_f": loc.life.N_f if loc.life else None,
    }
st.subheader("Results")
st.dataframe(pd.DataFrame(rows)[list(FILLETS)])

st.subheader("Notched stress histories")
hist = pd.DataFrame({"θ [deg]": result.theta_deg})
for f in result.fillets:
    hist[f"σ {f.name} [MPa]"] = pa_to_mpa(f.sigma_history)
    hist[f"τ {f.name} [MPa]"] = pa_to_mpa(f.tau_history)
st.line_chart(hist, x="θ [deg]")

show_note(result.note)
download_report(result, "crankshaft_assessment.md")
