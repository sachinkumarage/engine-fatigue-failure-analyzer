"""Input helpers shared by the app pages (display units only; all
calculations are done by efa)."""

import pandas as pd
import streamlit as st

from efa.fatigue.basquin import BasquinConstants
from efa.fatigue.marin import (
    MarinFactor,
    reliability_factor,
    steel_endurance_estimate,
    surface_factor,
)
from efa.loads.cycle import EngineSpec
from efa.loads.gas import PressureTable
from efa.provenance import Status, TracedValue
from efa.sources import SRC_SHIGLEY
from efa.units import bar_to_pa, mm_to_m, mpa_to_pa

STATUSES = [s.value for s in Status]
THETA = "θ [deg]"
P_COL = "p_cyl absolute [bar]"
EXAMPLE_TABLE = pd.DataFrame(
    {
        THETA: [0, 180, 300, 340, 360, 370, 380, 400, 450, 540, 720],
        P_COL: [1.0, 1.0, 5.0, 25.0, 45.0, 60.0, 50.0, 30.0, 10.0, 3.0, 1.0],
    }
)
PRESSURE_TABLE_KEY = "pressure_table"

# name, label, default, min, format, conversion to SI
ENGINE_FIELDS = (
    ("bore", "Bore B [mm]", 86.0, 1.0, "%.2f", mm_to_m),
    ("stroke", "Stroke S [mm]", 86.0, 1.0, "%.2f", mm_to_m),
    ("rod_length", "Rod length l [mm]", 143.0, 1.0, "%.2f", mm_to_m),
    ("l_g", "Big-end centre to rod CG, l_G [mm]", 40.0, 0.1, "%.2f", mm_to_m),
    ("speed_rpm", "Speed n [rpm]", 4000.0, 1.0, "%.0f", float),
    ("m_piston", "Piston mass [kg]", 0.40, 0.001, "%.3f", float),
    ("m_pin", "Gudgeon pin mass [kg]", 0.10, 0.0, "%.3f", float),
    ("m_rings", "Ring mass [kg]", 0.03, 0.0, "%.3f", float),
    ("m_rod", "Connecting-rod mass [kg]", 0.55, 0.001, "%.3f", float),
    ("p_crankcase", "Crankcase pressure, absolute [bar]", 1.01325, 0.01, "%.5f",
     bar_to_pa),
)  # fmt: skip


def default_pressure_table() -> PressureTable:
    """WE-02 synthetic pressure table (status: assumed)."""
    return PressureTable(
        EXAMPLE_TABLE[THETA].to_numpy(dtype=float),
        bar_to_pa(EXAMPLE_TABLE[P_COL].to_numpy(dtype=float)),
        "synthetic-WE-02",
        Status.ASSUMED,
    )


def engine_inputs() -> dict:
    """Engine data in the sidebar; returns EngineSpec keyword arguments in SI.

    Values are kept in session state so all pages share the same engine.
    """
    kwargs = {}
    with st.sidebar:
        st.header("Engine data")
        for name, label, default, lo, fmt, to_si in ENGINE_FIELDS:
            store = f"engine_{name}"
            value = st.number_input(
                label, min_value=lo, value=st.session_state.get(store, default),
                format=fmt, key=f"w_{store}",
            )  # fmt: skip
            st.session_state[store] = value
            kwargs[name] = to_si(value)
    return kwargs


def engine_spec() -> EngineSpec:
    """EngineSpec from the sidebar and the pressure table of the Engine Loads
    page (or the synthetic WE-02 table)."""
    table = st.session_state.get(PRESSURE_TABLE_KEY) or default_pressure_table()
    spec = EngineSpec(**engine_inputs(), pressure_table=table)
    st.sidebar.caption(
        f"Pressure table: {table.source_id} (status: {table.status.value}); "
        "edit it on the Engine Loads page."
    )
    return spec


def provenance(key: str, status: str = "assumed", source: str = ""):
    """Status and source id inputs; returns (Status, source_id)."""
    c1, c2 = st.columns(2)
    s = c1.selectbox("Status", STATUSES, STATUSES.index(status), key=f"{key}_st")
    src = c2.text_input("Source id", source, key=f"{key}_src")
    return Status(s), src


def direct_factor(key: str, label: str, default: float, basis: str) -> MarinFactor:
    """A Marin factor entered directly with basis, status and source."""
    value = st.number_input(label, min_value=0.001, value=default, key=key,
                            format="%.4f")  # fmt: skip
    basis = st.text_input("Basis", basis, key=f"{key}_basis")
    status, src = provenance(key)
    return MarinFactor(value, basis, status, src, verify=False)


def common_marin_inputs(prefix: str, s_ut: float, a: float, b: float):
    """S_e′ and the Marin factors k_a, k_d, k_e, k_f.

    Returns:
        (S_e′ TracedValue, dict of MarinFactor without k_b and k_c).
    """
    st.markdown("**S_e′**")
    if st.radio("S_e′ from", ["F6 steel estimate", "Direct"], key=f"{prefix}_se",
                horizontal=True) == "Direct":  # fmt: skip
        v = st.number_input("S_e′ [MPa]", min_value=1.0, value=400.0,
                            key=f"{prefix}_sev")  # fmt: skip
        status, src = provenance(f"{prefix}_sep")
        s_e_prime = TracedValue(mpa_to_pa(v), "direct input", status, src)
    else:
        s_e_prime = steel_endurance_estimate(s_ut)
    st.markdown("**k_a surface (F2)**")
    c1, c2 = st.columns(2)
    a = c1.number_input("a [MPa basis]", min_value=0.001, value=a, key=f"{prefix}_a")
    b = c2.number_input("b [-]", value=b, format="%.3f", key=f"{prefix}_b")
    status, src = provenance(f"{prefix}_ka", "cited", SRC_SHIGLEY)
    k_a = surface_factor(s_ut, a, b, status=status, source_id=src)
    st.markdown("**k_d temperature**")
    k_d = direct_factor(f"{prefix}_kd", "k_d [-]", 1.0, "room temperature (assumed)")
    st.markdown("**k_e reliability (F5)**")
    z_a = st.number_input("z_a [-] (99 %: 2.326)", min_value=0.0, value=2.326,
                          key=f"{prefix}_za")  # fmt: skip
    k_e = reliability_factor(z_a)
    st.markdown("**k_f miscellaneous (cited surface treatments only)**")
    k_f = direct_factor(f"{prefix}_kf", "k_f [-]", 1.0, "no surface treatment")
    return s_e_prime, {"k_a": k_a, "k_d": k_d, "k_e": k_e, "k_f": k_f}


def basquin_inputs(prefix: str) -> BasquinConstants:
    """Basquin constants (synthetic WE-04 defaults)."""
    c1, c2, c3, c4 = st.columns(4)
    sf = c1.number_input("σ′_f [MPa]", min_value=1.0, value=1200.0, key=f"{prefix}_sf")
    b = c2.number_input("b [-]", max_value=-0.001, value=-0.09, format="%.4f",
                        key=f"{prefix}_bb")  # fmt: skip
    n_min = c3.number_input("N_min", min_value=1.0, value=1e3, format="%g",
                            key=f"{prefix}_nmin")  # fmt: skip
    n_max = c4.number_input("N_max", min_value=1.0, value=1e6, format="%g",
                            key=f"{prefix}_nmax")  # fmt: skip
    status, src = provenance(f"{prefix}_basq", "assumed", "synthetic-WE-04")
    return BasquinConstants(mpa_to_pa(sf), b, n_min, n_max, src or "unspecified",
                            status)  # fmt: skip


def show_note(note) -> None:
    with st.expander("Result note: equations, validity and data status"):
        st.markdown(note.as_markdown())


def download_report(result, file_name: str) -> None:
    st.download_button(
        "Download report (Markdown)", result.as_markdown(), file_name=file_name,
        mime="text/markdown",
    )  # fmt: skip
