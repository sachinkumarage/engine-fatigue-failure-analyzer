"""Home page of the Engine Component Fatigue & Failure Analyzer app."""

import streamlit as st

import efa

st.set_page_config(page_title="Engine Component Fatigue & Failure Analyzer")

st.title("Engine Component Fatigue & Failure Analyzer")
st.caption(f"Version {efa.__version__}")

st.write(
    "A toolkit for fatigue life, safety factors and buckling of connecting rods, "
    "crankshafts and connecting-rod bolts, with a guided failure-analysis workflow "
    "and source-tracked material data."
)

st.subheader("Modules")
st.table(
    {
        "Module": [
            "Engine Loads",
            "Fatigue",
            "Connecting Rod",
            "Crankshaft",
            "Bolts",
            "Failure Analysis",
            "Materials",
        ],
        "Phase": [2, 3, 4, 4, 4, 6, 7],
        "Status": [
            "Available",
            "Available",
            "Planned",
            "Planned",
            "Planned",
            "Planned",
            "Planned",
        ],
    }
)
