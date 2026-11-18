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
