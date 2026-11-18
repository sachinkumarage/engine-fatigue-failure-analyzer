"""WE-08: connecting-rod bolts (docs/worked_examples/WE-08.md)."""

import pytest

from efa.components.conrod_bolt import BoltJoint, assess_bolts
from efa.provenance import Status
from tests.golden._tol import close
from tests.golden._we02 import we02_cycle, we02_spec

MPA = 1.0e6


@pytest.fixture(scope="module")
def result():
    joint = BoltJoint(
        n_b=2, A_t=61.2e-6, k_b=3.0e8, k_m=1.2e9, F_i=30e3, S_p=830 * MPA,
        S_ut=1040 * MPA, S_y=940 * MPA, S_e=162 * MPA, m_cap=0.10,
        status=Status.ASSUMED,
    )  # fmt: skip
    return assess_bolts(we02_cycle(), we02_spec(), joint)


@pytest.mark.parametrize(
    ("attr", "scale", "expected"),
    [
        ("F_rod_min_abs", 1.0, "6718.600100"),
        ("rotating_load", 1.0, "2234.410952"),
        ("P_total", 1.0, "8953.011052"),
        ("P", 1.0, "4476.505526"),
        ("C", 1.0, "0.2"),
        ("F_b_max", 1.0, "30895.301105"),
        ("F_m", 1.0, "-26418.795579"),
        ("sigma_a", MPA, "7.31455151"),
        ("sigma_m", MPA, "497.51062994"),
        ("n_p", 1.0, "1.64413351"),
        ("n_0", 1.0, "8.37706997"),
        ("n_f", 1.0, "10.13049525"),
    ],
)
def test_values(result, attr, scale, expected):
    assert getattr(result, attr) / scale == close(expected)


def test_note(result):
    assert result.governing[0] == "proof load"
    assert not result.note.warnings
    assert set(result.note.equation_ids) >= {"J1", "J2", "J3", "J4", "J5", "J6", "J7"}
    assert result.note.verify
    assert all(s is Status.ASSUMED for k, s in result.note.input_statuses.items())
