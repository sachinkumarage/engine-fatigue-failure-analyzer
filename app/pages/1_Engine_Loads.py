"""Engine Loads page: gas and inertia forces over the crank cycle."""

import pandas as pd
import streamlit as st

from efa.loads.cycle import EngineSpec, evaluate_cycle, peak_load
from efa.loads.gas import PressureTable
from efa.provenance import Status
from efa.units import bar_to_pa, mm_to_m, pa_to_bar, rad_to_deg

THETA = "θ [deg]"
P_COL = "p_cyl absolute [bar]"
EXAMPLE_TABLE = pd.DataFrame(
    {
        THETA: [0, 180, 300, 340, 360, 370, 380, 400, 450, 540, 720],
        P_COL: [1.0, 1.0, 5.0, 25.0, 45.0, 60.0, 50.0, 30.0, 10.0, 3.0, 1.0],
    }
)

st.title("Engine Loads")
st.caption(
    "Gas and inertia forces over the four-stroke cycle. "
    "θ = 0° intake TDC, 360° firing TDC; forces positive toward the crank "
    "(rod compression positive)."
)

with st.sidebar:
    st.header("Engine data")
    bore_mm = st.number_input("Bore B [mm]", min_value=1.0, value=86.0)
    stroke_mm = st.number_input("Stroke S [mm]", min_value=1.0, value=86.0)
    rod_mm = st.number_input("Rod length l [mm]", min_value=1.0, value=143.0)
    l_g_mm = st.number_input(
        "Big-end centre to rod CG, l_G [mm]", min_value=0.1, value=40.0
    )
    speed_rpm = st.number_input("Speed n [rpm]", min_value=1.0, value=4000.0)
    st.header("Masses [kg]")
    m_piston = st.number_input("Piston", min_value=0.001, value=0.40, format="%.3f")
    m_pin = st.number_input("Gudgeon pin", min_value=0.0, value=0.10, format="%.3f")
    m_rings = st.number_input("Rings", min_value=0.0, value=0.03, format="%.3f")
    m_rod = st.number_input(
        "Connecting rod", min_value=0.001, value=0.55, format="%.3f"
    )
    p_cc_bar = st.number_input(
        "Crankcase pressure, absolute [bar]", min_value=0.01, value=1.01325,
        format="%.5f",
    )  # fmt: skip

mode = st.radio("Mode", ["Pressure table", "Peak only"], horizontal=True)

try:
    spec_kwargs = dict(
        bore=mm_to_m(bore_mm),
        stroke=mm_to_m(stroke_mm),
        rod_length=mm_to_m(rod_mm),
        speed_rpm=speed_rpm,
        m_piston=m_piston,
        m_pin=m_pin,
        m_rings=m_rings,
        m_rod=m_rod,
        l_g=mm_to_m(l_g_mm),
        p_crankcase=bar_to_pa(p_cc_bar),
    )
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
