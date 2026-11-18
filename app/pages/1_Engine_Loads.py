"""Engine Loads page: gas and inertia forces over the crank cycle."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui_common import (  # noqa: E402
    EXAMPLE_TABLE,
    P_COL,
    PRESSURE_TABLE_KEY,
    THETA,
    engine_inputs,
)

from efa.loads.cycle import EngineSpec, evaluate_cycle, peak_load
from efa.loads.gas import PressureTable
from efa.provenance import Status
from efa.units import bar_to_pa, pa_to_bar, rad_to_deg

st.title("Engine Loads")
st.caption(
    "Gas and inertia forces over the four-stroke cycle. "
    "θ = 0° intake TDC, 360° firing TDC; forces positive toward the crank "
    "(rod compression positive)."
)

spec_kwargs = engine_inputs()

mode = st.radio("Mode", ["Pressure table", "Peak only"], horizontal=True)

try:
    if mode == "Pressure table":
        st.subheader("Cylinder pressure table")
        st.caption("Default: synthetic example (assumed), not measured data.")
        c1, c2 = st.columns(2)
        source_id = c1.text_input("Source id", value="synthetic-WE-02")
        status = c2.selectbox("Status", [s.value for s in Status], index=2)
        edited = st.data_editor(EXAMPLE_TABLE, num_rows="dynamic", hide_index=True)
        edited = edited.dropna()
        table = PressureTable(
            edited[THETA].to_numpy(dtype=float),
            bar_to_pa(edited[P_COL].to_numpy(dtype=float)),
            source_id,
            Status(status),
        )
        st.session_state[PRESSURE_TABLE_KEY] = table
        result = evaluate_cycle(EngineSpec(**spec_kwargs, pressure_table=table))
    else:
        c1, c2 = st.columns(2)
        p_peak_bar = c1.number_input(
            "Peak pressure p_peak, absolute [bar]", min_value=0.01, value=60.0
        )
        theta_peak = c2.number_input("θ_peak [deg]", value=370.0)
        result = peak_load(EngineSpec(**spec_kwargs), bar_to_pa(p_peak_bar), theta_peak)
except ValueError as exc:
    st.error(f"Invalid input: {exc}")
    st.stop()

m1, m2, m3, m4 = st.columns(4)
m1.metric(
    "Max compressive F_rod",
    f"{result.F_rod_max_compression:,.0f} N",
    f"at {result.theta_max_compression_deg:.0f}°",
    delta_color="off",
)
m2.metric(
    "Max tensile F_rod",
    f"{result.F_rod_max_tension:,.0f} N",
    f"at {result.theta_max_tension_deg:.0f}°",
    delta_color="off",
)
m3.metric("Centrifugal F_c", f"{result.F_c:,.0f} N")
if mode == "Pressure table":
    m4.metric("Mean torque T", f"{result.T_mean:,.2f} N·m")

table_out = pd.DataFrame(
    {
        THETA: result.theta_deg,
        "p_cyl [bar]": pa_to_bar(result.p_cyl),
        "F_g [N]": result.F_g,
        "F_i [N]": result.F_i,
        "F_p [N]": result.F_p,
        "β [deg]": rad_to_deg(result.beta),
        "F_rod [N]": result.F_rod,
        "F_side [N]": result.F_side,
        "F_t [N]": result.F_t,
        "F_r [N]": result.F_r,
        "T [N·m]": result.T,
    }
)

if mode == "Pressure table":
    st.subheader("Cylinder pressure")
    st.line_chart(table_out, x=THETA, y="p_cyl [bar]")
    st.subheader("Forces along the cylinder axis and rod force")
    st.line_chart(table_out, x=THETA, y=["F_g [N]", "F_i [N]", "F_rod [N]"])
    st.subheader("Crank torque")
    st.line_chart(table_out, x=THETA, y="T [N·m]")
    with st.expander("Results table"):
        st.dataframe(table_out, hide_index=True)
else:
    st.subheader("Loads at θ_peak")
    st.dataframe(table_out, hide_index=True)

with st.expander("Result note: equations, validity and data status"):
    st.markdown(result.note.as_markdown())
