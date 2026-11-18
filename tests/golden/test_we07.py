"""WE-07: crankshaft, single throw (docs/worked_examples/WE-07.md)."""

import numpy as np
import pytest

from efa.components.common import Material
from efa.components.crankshaft import (
    JOURNAL,
    PIN,
    CrankGeometry,
    FilletNotch,
    assess_crankshaft,
)
from efa.fatigue.basquin import BasquinConstants
from efa.fatigue.marin import (
    MarinFactor,
    endurance_limit,
    reliability_factor,
    size_factor,
    surface_factor,
)
from efa.fatigue.mean_stress import LOCAL_YIELD_WARNING
from efa.provenance import Status, TracedValue
from efa.sources import SRC_SHIGLEY
from tests.golden._tol import close
from tests.golden._we02 import we02_cycle

MPA = 1.0e6
S_UT = 800 * MPA


def endurance(d):
    factors = {
        "k_a": surface_factor(S_UT, 1.58, -0.085, status=Status.ASSUMED),
        "k_b": size_factor(d, "bending"),
        "k_c": MarinFactor(1.0, "k_c = 1, combined loading via von Mises (S3)",
                           Status.CITED, SRC_SHIGLEY, True),
        "k_d": MarinFactor(1.0, "WE-07 k_d = 1", Status.ASSUMED),
        "k_e": reliability_factor(2.326),
        "k_f": MarinFactor(1.0, "WE-07 k_f = 1", Status.ASSUMED),
    }  # fmt: skip
    return endurance_limit(TracedValue(400 * MPA, "WE-07", Status.ASSUMED), factors)


@pytest.fixture(scope="module")
def result():
    notch = FilletNotch(2.2, 1.6, 0.0025)
    geometry = CrankGeometry(0.090, 0.012, 0.048, 0.010, 0.055, notch, notch, 0.0019)
    material = Material("synthetic", S_UT, 600 * MPA, Status.ASSUMED)
    basquin = BasquinConstants(1200 * MPA, -0.09, 1e3, 1e6, "WE-07", Status.ASSUMED)
    marin = {PIN: endurance(0.048), JOURNAL: endurance(0.055)}
    return assess_crankshaft(we02_cycle(), geometry, material, marin, basquin)


def test_loads_over_cycle(result):
    cyc = we02_cycle()
    assert cyc.F_c == close("2988.887377")
    assert result.F_R.max() == close("24063.464740")
    assert int(np.argmax(result.F_R)) == 370
    assert result.F_R.min() == close("-9707.487477")
    assert int(np.argmin(result.F_R)) == 0
    assert cyc.F_t.max() == close("10993.348660")
    assert int(np.argmax(cyc.F_t)) == 390
    assert cyc.F_t.min() == close("-3686.359624")
    assert int(np.argmin(cyc.F_t)) == 333


def test_common(result):
    f = result.fillet(PIN)
    marin = endurance(0.048)
    assert marin.factors["k_a"].value == close("0.8951471598")
    for fil in result.fillets:
        assert fil.q == close("0.9633911368")
        assert fil.K_f_b == close("2.1560693642")
        assert fil.K_f_t == close("1.5780346821")
    assert f.d == 0.048


EXPECTED = {
    PIN: dict(
        k_b="0.8194621008", S_e="238.81688121", M=("397.047168", "-160.173543"),
        T=("236.356996", "-79.256732"), s=("55.32690509", "23.51937802"),
        t=("11.46803029", "5.70834038"), eq=("58.78446719", "25.51306709"),
        n=("3.5966042", "3.9965874", "4.0032908", "7.1176459"), d=0.048,
    ),
    JOURNAL: dict(
        k_b="0.8048964372", S_e="234.57199135", M=("120.317324", "-48.537437"),
        T=("472.713992", "-158.513464"), s=("11.14443565", "4.73748160"),
        t=("15.24594928", "7.58884183"), eq=("28.66208915", "13.97194663"),
        n=("7.1605635", "8.0233515", "8.0393574", "14.073263"), d=0.055,
    ),
}  # fmt: skip


@pytest.mark.parametrize("name", [PIN, JOURNAL])
def test_fillet(result, name):
    e = EXPECTED[name]
    f = result.fillet(name)
    loc = f.location
    a = loc.assessment
    assert endurance(e["d"]).factors["k_b"].value == close(e["k_b"])
    assert loc.S_e / MPA == close(e["S_e"])
    assert (f.M_max, f.M_min) == (close(e["M"][0]), close(e["M"][1]))
    assert (f.T_max, f.T_min) == (close(e["T"][0]), close(e["T"][1]))
    assert loc.sigma_a / MPA == close(e["s"][0])
    assert loc.sigma_m / MPA == close(e["s"][1])
    assert loc.tau_a / MPA == close(e["t"][0])
    assert loc.tau_m / MPA == close(e["t"][1])
    assert loc.sigma_eq_a / MPA == close(e["eq"][0])
    assert loc.sigma_eq_m / MPA == close(e["eq"][1])
    assert a.n_goodman == close(e["n"][0])
    assert a.n_gerber == close(e["n"][1])
    assert a.n_elliptic == close(e["n"][2])
    assert a.n_yield == close(e["n"][3])
    assert a.regime == "tensile_mean"
    assert LOCAL_YIELD_WARNING not in loc.note.warnings
    assert loc.life is None


def test_governing_and_note(result):
    name, n = result.governing
    assert name == f"{PIN} fatigue"
    assert n == close("3.5966042")
    text = " ".join(result.note.validity_notes)
    for phrase in (
        "Single-throw statically determinate beam",
        "Torsional vibration excluded",
        "counterweight masses excluded",
        "σ and τ extrema taken independently",
        "non-proportional loading not modelled",
        "to be replaced by FEA results in Phase 5",
    ):
        assert phrase in text
    assert {"X1", "X2", "X3", "X4", "X5", "S3"} <= set(result.note.equation_ids)
    assert not result.note.warnings
