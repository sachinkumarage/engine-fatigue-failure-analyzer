import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_no_raw_data.py"
_spec = importlib.util.spec_from_file_location("check_no_raw_data", SCRIPT)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


def test_clean_list_passes():
    paths = ["README.md", "src/efa/__init__.py", "docs/data_policy.md"]
    assert guard.find_protected_paths(paths) == []


def test_raw_data_is_detected():
    paths = ["README.md", "data/raw/photo.jpg"]
    assert guard.find_protected_paths(paths) == ["data/raw/photo.jpg"]
