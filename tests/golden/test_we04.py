"""WE-04: Basquin with Morrow (docs/worked_examples/WE-04.md)."""

import pytest

from efa.fatigue.basquin import RANGE_WARNING, BasquinConstants, life, strength
from efa.provenance import Status
from tests.golden._tol import close

MPA = 1.0e6
CONSTS = BasquinConstants(1200 * MPA, -0.09, 1e3, 1e6, "WE-04", Status.ASSUMED)


@pytest.mark.parametrize(
    ("sigma_a", "sigma_m", "expected", "warn"),
    [
        (400, 0, "100073.082882", False),
        (400, 150, "22696.678850", False),
        (300, 0, "2446388.708405", True),
    ],
)
def test_life(sigma_a, sigma_m, expected, warn):
    res = life(sigma_a * MPA, sigma_m * MPA, CONSTS)
    assert res.N_f == close(expected)
    assert any(RANGE_WARNING in w for w in res.note.warnings) is warn


@pytest.mark.parametrize(
    ("sigma_m", "expected"), [(0, "400.026301"), (150, "350.023013")]
)
def test_strength(sigma_m, expected):
    res = strength(1e5, sigma_m * MPA, CONSTS)
    assert res.sigma_a / MPA == close(expected)
    assert not res.note.warnings
