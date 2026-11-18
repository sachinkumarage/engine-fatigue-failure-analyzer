"""The core package must stay independent of the user interface."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "efa"


def _imports_streamlit(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[0] == "streamlit" for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] == "streamlit":
                return True
    return False


def test_source_files_exist():
    assert list(SRC.rglob("*.py"))


def test_core_package_does_not_import_streamlit():
    offenders = [
        str(path.relative_to(SRC))
        for path in SRC.rglob("*.py")
        if _imports_streamlit(ast.parse(path.read_text(encoding="utf-8")))
    ]
    assert offenders == []
