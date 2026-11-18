"""WE-05: column buckling (docs/worked_examples/WE-05.md)."""

import pytest

from efa.buckling import column_check
from tests.golden._tol import close

E, S_Y, A = 205e9, 750e6, 2.4e-4
P_ROD = 27763.169641

CASES = [
    ("Plane 1", 1.8e-8, 1.0, 0.143, P_ROD, "0.008660254", "16.512218",
     "73.453276", "Johnson", "731.04954", "175451.89", "6.3195915"),
    ("Plane 2", 8.0e-9, 0.5, 0.143, P_ROD, "0.0057735027", "12.384163",
     "73.453276", "Johnson", "739.34037", "177441.69", "6.3912619"),
    ("Slender", 8.0e-9, 1.0, 1.5, 2000.0, "0.0057735027", "259.80762",
     "73.453276", "Euler", "29.974354", "7193.845", "3.5969225"),
]  # fmt: skip


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_column(case):
    _, inertia, k_factor, length, load, k, s, s1, regime, s_cr, p_cr, n = case
    res = column_check(A, inertia, length, k_factor, E, S_Y, load)
    assert res.k == close(k)
    assert res.slenderness == close(s)
    assert res.transition_slenderness == close(s1)
    assert res.regime == regime
    assert res.sigma_cr / 1e6 == close(s_cr)
    assert res.P_cr == close(p_cr)
    assert res.n == close(n)
