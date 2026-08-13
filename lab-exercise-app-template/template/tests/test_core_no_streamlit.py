"""LOAD-BEARING (§B1, §B10): core/ must never import streamlit.

This keeps the UI swappable and makes core/ reusable as a library later — a single stray
import defeats the architecture. Two independent proofs:

  1. a static scan of every core/*.py source file, and
  2. a real import of every core module with streamlit BLOCKED by an import hook
     (equivalent to "core imports and its tests pass with no Streamlit installed").
"""
from __future__ import annotations

import ast
import pkgutil
import subprocess
import sys
from pathlib import Path

import pytest

import core

CORE_DIR = Path(core.__file__).parent
CORE_MODULES = sorted(m.name for m in pkgutil.iter_modules([str(CORE_DIR)]))


def test_core_has_modules():
    assert CORE_MODULES, "core/ should contain modules"


@pytest.mark.parametrize("module_name", CORE_MODULES)
def test_core_source_never_imports_streamlit(module_name: str):
    """Static scan: no `import streamlit` / `from streamlit ...` anywhere in core/."""
    tree = ast.parse((CORE_DIR / f"{module_name}.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.split(".")[0] == "streamlit", (
                    f"core/{module_name}.py imports streamlit")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root != "streamlit", f"core/{module_name}.py imports from streamlit"


def test_core_imports_with_streamlit_blocked():
    """Import every core module in a subprocess where importing streamlit raises."""
    code = f"""
import sys
class Block:
    def find_spec(self, name, path=None, target=None):
        if name == "streamlit" or name.startswith("streamlit."):
            raise ImportError("streamlit unavailable")
        return None
sys.meta_path.insert(0, Block())
import importlib
for m in {CORE_MODULES!r}:
    importlib.import_module("core." + m)
assert "streamlit" not in sys.modules, "core pulled in streamlit"
print("OK")
"""
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          cwd=str(CORE_DIR.parent))
    assert proc.returncode == 0, f"core failed to import without streamlit:\n{proc.stderr}"
    assert "OK" in proc.stdout


def test_importing_core_does_not_pull_in_streamlit():
    """Even when streamlit IS installed, importing core must not load it."""
    code = """
import sys, importlib, pkgutil
import core
for m in [x.name for x in pkgutil.iter_modules(core.__path__)]:
    importlib.import_module("core." + m)
assert "streamlit" not in sys.modules, "importing core loaded streamlit"
print("OK")
"""
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          cwd=str(CORE_DIR.parent))
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout


def test_exercise_schema_is_framework_free():
    """core imports exercise.schema, so the schema module must also avoid streamlit."""
    import exercise.schema as schema_mod

    tree = ast.parse(Path(schema_mod.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ""])
            assert not any(n.split(".")[0] == "streamlit" for n in names), (
                "exercise/schema.py must stay framework-free (core imports it)")
