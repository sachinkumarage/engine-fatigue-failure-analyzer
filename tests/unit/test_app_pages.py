"""Run every Streamlit page with default inputs and check for exceptions."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[2] / "app"
PAGES = [APP / "Home.py", *sorted((APP / "pages").glob("*.py"))]


@pytest.mark.parametrize("page", PAGES, ids=[p.name for p in PAGES])
def test_page_runs_without_exceptions(page):
    at = AppTest.from_file(str(page), default_timeout=60).run()
    assert not at.exception


def test_engine_loads_table_and_peak_modes():
    at = AppTest.from_file(str(APP / "pages" / "1_Engine_Loads.py"), default_timeout=60)
    at.run()
    assert not at.exception
    assert not at.error
    at.radio[0].set_value("Peak only").run()
    assert not at.exception
    assert not at.error


def test_fatigue_page_all_tabs_render_with_defaults():
    at = AppTest.from_file(str(APP / "pages" / "2_Fatigue.py"), default_timeout=60)
    at.run()
    assert not at.exception
    assert not at.error
    assert [t.label for t in at.tabs] == [
        "Endurance limit", "Notch", "Mean stress", "Finite life", "Buckling"
    ]  # fmt: skip
    labels = {m.label: m.value for m in at.metric}
    assert labels["S_e"] == "227.56 MPa"
    assert labels["K_f"] == "1.9592"
    assert labels["Regime"] == "Johnson"
    charts = at.get("vega_lite_chart")
    assert len(charts) == 1 and "Haigh" in charts[0].proto.spec


@pytest.mark.parametrize(
    ("page", "governing"),
    [
        ("3_Connecting_Rod.py", "Governing: Small-end transition fatigue, n = 1.514"),
        ("4_Crankshaft.py", "Governing: crankpin fillet fatigue, n = 3.597"),
        ("5_Bolts.py", "Governing: proof load, n = 1.644"),
    ],
)
def test_component_pages_with_defaults(page, governing):
    at = AppTest.from_file(str(APP / "pages" / page), default_timeout=60).run()
    assert not at.exception
    assert not at.error
    assert [s.value for s in at.success] == [governing]
    assert len(at.get("download_button")) == 1
