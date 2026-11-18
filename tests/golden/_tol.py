"""Tolerance helper: rel 1e-7 for 8+ significant figures, else rel 1e-6."""

import pytest


def sig_figs(text: str) -> int:
    digits = text.lstrip("+-").split("e")[0].replace(".", "").lstrip("0")
    return len(digits)


def close(expected: str):
    value = float(expected)
    if value == 0.0:
        return pytest.approx(0.0, abs=1e-6)
    rel = 1e-7 if sig_figs(expected) >= 8 else 1e-6
    return pytest.approx(value, rel=rel, abs=0.0)
