"""Fatigue page: endurance limit, notch, mean stress, finite life, buckling."""

import pandas as pd
import streamlit as st

from efa.buckling import column_check
from efa.fatigue.basquin import BasquinConstants, life, strength
from efa.fatigue.marin import (
    MarinFactor,
    endurance_limit,
    load_factor,
    reliability_factor,
    size_factor,
    steel_endurance_estimate,
    surface_factor,
)
from efa.fatigue.mean_stress import assess, haigh_curves
from efa.provenance import Status, TracedValue
from efa.sources import SRC_SHIGLEY
from efa.stress.nominal import peak_abs_stress
from efa.stress.notch import fatigue_notch_factor, notch_sensitivity, notched_stresses
from efa.units import (
    gpa_to_pa,
    mm2_to_m2,
    mm4_to_m4,
    mm_to_m,
    mpa_to_pa,
    pa_to_mpa,
    sqrt_mm_to_sqrt_m,
)

STATUSES = [s.value for s in Status]

st.title("Fatigue")
st.caption(
    "Default inputs are synthetic examples (status: assumed), not material data. "
    "Relations taken from SRC-SHIGLEY are flagged for verification."
)


def provenance(key: str, status: str = "cited", source: str = SRC_SHIGLEY):
    c1, c2 = st.columns(2)
    s = c1.selectbox("Status", STATUSES, STATUSES.index(status), key=f"{key}_st")
    src = c2.text_input("Source id", source, key=f"{key}_src")
    return Status(s), src


def direct_factor(key: str, default: float, basis: str) -> MarinFactor:
    value = st.number_input(
        "Value [-]", min_value=0.001, value=default, key=key, format="%.4f"
    )
    basis = st.text_input("Basis", basis, key=f"{key}_basis")
    status, src = provenance(key, "assumed", "")
    return MarinFactor(value, basis, status, src, verify=False)


def show_note(note) -> None:
    with st.expander("Result note: equations, validity and data status"):
        st.markdown(note.as_markdown())


tab_se, tab_notch, tab_mean, tab_life, tab_buck = st.tabs(
    ["Endurance limit", "Notch", "Mean stress", "Finite life", "Buckling"]
)

# --- Endurance limit ---------------------------------------------------------
with tab_se:
    c1, c2 = st.columns(2)
    s_ut = mpa_to_pa(c1.number_input("S_ut [MPa]", min_value=1.0, value=900.0))
    s_y = mpa_to_pa(c2.number_input("S_y [MPa]", min_value=1.0, value=750.0))
    endurance = None
    try:
        with st.expander("S_e′ (unmodified endurance limit)", expanded=True):
            if (
                st.radio(
                    "S_e′ from",
                    ["F6 steel estimate", "Direct"],
                    key="se_mode",
                    horizontal=True,
                )
                == "Direct"
            ):
                v = st.number_input("S_e′ [MPa]", min_value=1.0, value=450.0)
                basis = st.text_input("Basis", "rotating-beam test", key="se_basis")
                status, src = provenance("se", "assumed", "")
                s_e_prime = TracedValue(mpa_to_pa(v), basis, status, src)
            else:
                s_e_prime = steel_endurance_estimate(s_ut)
                st.write(f"S_e′ = {pa_to_mpa(s_e_prime.value):.1f} MPa (F6, verify)")
        with st.expander("k_a surface", expanded=True):
            if (
                st.radio(
                    "k_a from", ["F2 (a, b)", "Direct"], key="ka_mode", horizontal=True
                )
                == "Direct"
            ):
                k_a = direct_factor("ka", 1.0, "")
            else:
                c1, c2 = st.columns(2)
                a = c1.number_input("a [MPa basis]", min_value=0.001, value=4.51)
                b = c2.number_input("b [-]", value=-0.265, format="%.3f")
                status, src = provenance("ka", "assumed")
                k_a = surface_factor(s_ut, a, b, status=status, source_id=src)
        loading = st.selectbox(
            "Loading for k_b and k_c", ["bending", "torsion", "axial"]
        )
        with st.expander("k_b size", expanded=True):
            if (
                st.radio(
                    "k_b from", ["F3 (d)", "Direct"], key="kb_mode", horizontal=True
                )
                == "Direct"
            ):
                k_b = direct_factor("kb", 1.0, "")
            else:
                d = st.number_input("Diameter d [mm]", min_value=0.1, value=40.0)
                k_b = size_factor(mm_to_m(d), loading)
        with st.expander("k_c load"):
            if (
                st.radio(
                    "k_c from",
                    ["F4 (loading)", "Direct"],
                    key="kc_mode",
                    horizontal=True,
                )
                == "Direct"
            ):
                k_c = direct_factor("kc", 1.0, "")
            else:
                k_c = load_factor(loading)
        with st.expander("k_d temperature"):
            k_d = direct_factor("kd", 1.0, "room temperature, k_d = 1 (assumed)")
        with st.expander("k_e reliability"):
            if (
                st.radio(
                    "k_e from", ["F5 (z_a)", "Direct"], key="ke_mode", horizontal=True
                )
                == "Direct"
            ):
                k_e = direct_factor("ke", 1.0, "")
            else:
                z_a = st.number_input(
                    "z_a [-] (99 %: 2.326)", min_value=0.0, value=2.326
                )
                k_e = reliability_factor(z_a)
        with st.expander("k_f miscellaneous (cited surface treatments only)"):
            k_f_m = direct_factor("kf", 1.0, "no surface treatment, k_f = 1")
        factors = {
            "k_a": k_a,
            "k_b": k_b,
            "k_c": k_c,
            "k_d": k_d,
            "k_e": k_e,
            "k_f": k_f_m,
        }
        endurance = endurance_limit(s_e_prime, factors)
    except ValueError as exc:
        st.error(f"Invalid input: {exc}")
    if endurance is not None:
        st.metric("S_e", f"{pa_to_mpa(endurance.S_e):.2f} MPa")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Factor": n,
                        "Value": f.value,
                        "Basis": f.basis,
                        "Status": f.status.value,
                        "Source": f.source_id,
                        "Verify": f.verify,
                    }
                    for n, f in endurance.factors.items()
                ]
            ),
            hide_index=True,
        )
        show_note(endurance.note)

# --- Notch -------------------------------------------------------------------
with tab_notch:
    k_f = None
    k_t = st.number_input("K_t [-]", min_value=1.0, value=2.0)
    try:
        if st.radio("q from", ["N2 Neuber (√a, ρ)", "Direct q"], horizontal=True) == (
            "Direct q"
        ):
            q = st.number_input("q [-]", min_value=0.0, max_value=1.0, value=0.9)
        else:
            c1, c2 = st.columns(2)
            rho = c1.number_input("Notch radius ρ [mm]", min_value=0.001, value=2.0)
            sqrt_a = c2.number_input(
                "Neuber constant √a [mm^0.5]",
                min_value=1e-6,
                value=0.0600833,
                format="%.6f",
            )
            st.caption("√a must come from a cited source for the material (verify).")
            q = notch_sensitivity(sqrt_mm_to_sqrt_m(sqrt_a), mm_to_m(rho))
        k_f = fatigue_notch_factor(k_t, q)
        c1, c2 = st.columns(2)
        c1.metric("q", f"{q:.4f}")
        c2.metric("K_f", f"{k_f:.4f}")
        st.caption(
            "Equations: N1 K_f = 1 + q (K_t − 1); N2 Neuber (SRC-SHIGLEY, verify)."
        )
    except ValueError as exc:
        st.error(f"Invalid input: {exc}")

# --- Mean stress -------------------------------------------------------------
with tab_mean:
    c1, c2 = st.columns(2)
    sa_nom = mpa_to_pa(
        c1.number_input("Nominal σ_a [MPa]", min_value=0.001, value=150.0)
    )
    sm_nom = mpa_to_pa(c2.number_input("Nominal σ_m [MPa]", value=100.0))
    if endurance is None or k_f is None:
        st.info("Complete the Endurance limit and Notch tabs first.")
    else:
        try:
            sig_a, sig_m = notched_stresses(sa_nom, sm_nom, k_f)
            res = assess(
                sig_a,
                sig_m,
                endurance.S_e,
                s_ut,
                s_y,
                K_f=k_f,
                sigma_max=peak_abs_stress(sa_nom, sm_nom),
            )
        except ValueError as exc:
            st.error(f"Invalid input: {exc}")
        else:
            st.write(
                f"Notched stresses (× K_f = {k_f:.4f}): "
                f"σ_a = {pa_to_mpa(sig_a):.2f} MPa, "
                f"σ_m = {pa_to_mpa(sig_m):.2f} MPa; regime: {res.regime}"
            )
            for w in res.note.warnings:
                st.warning(w)
            st.dataframe(
                pd.DataFrame(
                    {
                        "Criterion": [
                            "Goodman",
                            "Gerber",
                            "ASME elliptic",
                            "Langer yield",
                        ],
                        "n": [res.n_goodman, res.n_gerber, res.n_elliptic, res.n_yield],
                    }
                ),
                hide_index=True,
            )
            rows = [
                {"criterion": name, "sigma_m": float(x), "sigma_a": float(y)}
                for name, (xs, ys) in haigh_curves(endurance.S_e, s_ut, s_y).items()
                for x, y in zip(pa_to_mpa(xs), pa_to_mpa(ys), strict=True)
            ]
            point = [{"sigma_m": pa_to_mpa(sig_m), "sigma_a": pa_to_mpa(sig_a)}]
            enc = {
                "x": {"field": "sigma_m", "type": "quantitative", "title": "σ_m [MPa]"},
                "y": {"field": "sigma_a", "type": "quantitative", "title": "σ_a [MPa]"},
            }
            spec = {
                "title": "Haigh diagram (failure lines at n = 1)",
                "width": "container",
                "layer": [
                    {
                        "data": {"values": rows},
                        "mark": "line",
                        "encoding": {
                            **enc,
                            "color": {
                                "field": "criterion",
                                "type": "nominal",
                                "title": "Criterion",
                            },
                        },
                    },
                    {
                        "data": {"values": point},
                        "mark": {
                            "type": "point",
                            "filled": True,
                            "size": 90,
                            "shape": "diamond",
                        },
                        "encoding": enc,
                    },
                ],
            }
            st.vega_lite_chart(None, spec)
            st.caption("Diamond: operating point (notched σ_m, σ_a).")
            show_note(res.note)

# --- Finite life -------------------------------------------------------------
with tab_life:
    st.caption("Default constants: synthetic example (assumed).")
    c1, c2, c3, c4 = st.columns(4)
    sf = mpa_to_pa(c1.number_input("σ′_f [MPa]", min_value=1.0, value=1200.0))
    b_exp = c2.number_input("b [-]", max_value=-0.001, value=-0.09, format="%.4f")
    n_min = c3.number_input("N_min [cycles]", min_value=1.0, value=1.0e3, format="%g")
    n_max = c4.number_input("N_max [cycles]", min_value=1.0, value=1.0e6, format="%g")
    status, src = provenance("basq", "assumed", "synthetic-WE-04")
    try:
        consts = BasquinConstants(sf, b_exp, n_min, n_max, src or "unspecified", status)
        st.subheader("Life")
        c1, c2 = st.columns(2)
        la = mpa_to_pa(
            c1.number_input("σ_a [MPa]", min_value=0.001, value=400.0, key="la")
        )
        lm = mpa_to_pa(c2.number_input("σ_m [MPa]", value=0.0, key="lm"))
        lres = life(la, lm, consts)
        st.metric("N_f", f"{lres.N_f:,.0f} cycles")
        for w in lres.note.warnings:
            st.warning(w)
        show_note(lres.note)
        st.subheader("Strength")
        c1, c2 = st.columns(2)
        sn = c1.number_input("N_f [cycles]", min_value=1.0, value=1.0e5, format="%g")
        sm = mpa_to_pa(c2.number_input("σ_m [MPa]", value=0.0, key="sm"))
        sres = strength(sn, sm, consts)
        st.metric("σ_a", f"{pa_to_mpa(sres.sigma_a):.2f} MPa")
        for w in sres.note.warnings:
            st.warning(w)
        show_note(sres.note)
    except ValueError as exc:
        st.error(f"Invalid input: {exc}")

# --- Buckling ----------------------------------------------------------------
with tab_buck:
    st.caption("Default: rod-like column of WE-05 (synthetic, assumed).")
    c1, c2, c3 = st.columns(3)
    area = mm2_to_m2(c1.number_input("A [mm²]", min_value=0.001, value=240.0))
    inertia = mm4_to_m4(c2.number_input("I [mm⁴]", min_value=0.001, value=18000.0))
    length = mm_to_m(c3.number_input("L [mm]", min_value=0.001, value=143.0))
    c1, c2, c3, c4 = st.columns(4)
    k_eff = c1.number_input("K [-]", min_value=0.01, value=1.0)
    e_mod = gpa_to_pa(c2.number_input("E [GPa]", min_value=0.1, value=205.0))
    s_y_b = mpa_to_pa(
        c3.number_input("S_y [MPa]", min_value=1.0, value=750.0, key="syb")
    )
    load = c4.number_input("P [N] (compression +)", value=27763.169641)
    try:
        col = column_check(area, inertia, length, k_eff, e_mod, s_y_b, load)
    except ValueError as exc:
        st.error(f"Invalid input: {exc}")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Regime", col.regime)
        c2.metric(
            "L_e/k",
            f"{col.slenderness:.2f}",
            f"(L_e/k)₁ = {col.transition_slenderness:.2f}",
            delta_color="off",
        )
        c3.metric("σ_cr", f"{pa_to_mpa(col.sigma_cr):.1f} MPa")
        c4.metric("P_cr", f"{col.P_cr:,.0f} N")
        st.metric(
            "Safety factor n = P_cr / P",
            "∞" if col.n == float("inf") else f"{col.n:.3f}",
        )
        show_note(col.note)
