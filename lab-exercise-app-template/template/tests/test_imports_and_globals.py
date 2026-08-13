"""Every module imports, and every global name it looks up actually exists.

This test exists because of a real incident: `app.py` called `events.setup_logging()` while
`events` was never imported. The whole suite passed — nothing imported `app.py`, and the call
sits inside a function, so a plain import test would not have caught it either. The app then
crashed on its first page load in front of the deployer:

    NameError: name 'events' is not defined
      File "/app/app.py", line 37, in _bootstrap  ->  events.setup_logging()

Two checks, both cheap:

1. **Import smoke** — every module under `core/`, `ui/`, `exercise/` and `app.py` imports
   cleanly. Catches syntax errors, circular imports and missing dependencies.
2. **Global resolution** — for every function in those modules, disassemble the bytecode and
   confirm each `LOAD_GLOBAL` resolves to a module global or a builtin. This finds unimported
   names in code paths no test happens to execute, which is exactly the case above.

`LOAD_GLOBAL` is the right instrument: it fires only for genuine global lookups, so attribute
access (`events.setup_logging`) contributes `events` but not `setup_logging` — no false
positives from method names.

If this test ever fails on a name that is legitimately defined at runtime only (injected into
the module namespace from outside, say), add it to `RUNTIME_INJECTED` with a comment saying
who injects it. Do not delete the test.
"""
from __future__ import annotations

import builtins
import dis
import importlib
import pkgutil
import types
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent

# Names that are genuinely absent from the module namespace at import time. Empty by design —
# every entry needs a comment naming what puts the name there.
RUNTIME_INJECTED: set[str] = set()

BUILTIN_NAMES = set(dir(builtins))


def _module_names() -> list[str]:
    """Every importable module in the app: the packages plus the top-level entry point."""
    names = ["app"]
    for package in ("core", "ui", "exercise"):
        package_dir = APP_ROOT / package
        if not package_dir.is_dir():
            continue
        names.append(package)
        for info in pkgutil.iter_modules([str(package_dir)]):
            names.append(f"{package}.{info.name}")
    return sorted(names)


MODULES = _module_names()


def _code_objects(code: types.CodeType):
    """The code object and every code object nested in it (functions, comprehensions, lambdas)."""
    yield code
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            yield from _code_objects(const)


@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports(module_name: str):
    """Importing must not raise. `app.py` is safe to import: `main()` is under a
    `if __name__ == "__main__"` guard, which is how Streamlit runs it."""
    importlib.import_module(module_name)


@pytest.mark.parametrize("module_name", MODULES)
def test_every_global_lookup_resolves(module_name: str):
    module = importlib.import_module(module_name)
    source = getattr(module, "__file__", None)
    if source is None:                      # namespace package: nothing to disassemble
        return

    code = compile(Path(source).read_text(encoding="utf-8"), source, "exec")
    available = set(vars(module)) | BUILTIN_NAMES | RUNTIME_INJECTED

    missing: dict[str, int] = {}
    for block in _code_objects(code):
        for instruction in dis.get_instructions(block):
            if instruction.opname != "LOAD_GLOBAL":
                continue
            name = instruction.argval
            if name not in available and name not in missing:
                missing[name] = instruction.positions.lineno or 0

    assert not missing, (
        f"{module_name} looks up names that do not exist — this is a NameError waiting to "
        f"happen on whichever page hits that line first:\n"
        + "\n".join(f"  line {line}: {name}" for name, line in sorted(missing.items(),
                                                                     key=lambda kv: kv[1]))
        + "\n(usually a missing import; add it, don't suppress this test)"
    )


def test_the_check_would_catch_a_missing_import(tmp_path):
    """Guard the guard: prove the disassembly check fails on the exact bug it was written for."""
    module_file = tmp_path / "regression_probe.py"
    module_file.write_text("def boot():\n    events.setup_logging()\n", encoding="utf-8")

    code = compile(module_file.read_text(encoding="utf-8"), str(module_file), "exec")
    namespace: dict = {}
    exec(code, namespace)                   # noqa: S102 — deliberate, on a file we just wrote

    found = {
        instruction.argval
        for block in _code_objects(code)
        for instruction in dis.get_instructions(block)
        if instruction.opname == "LOAD_GLOBAL"
    }
    assert "events" in found, "the check must see the unimported name"
    assert "setup_logging" not in found, "attribute names must not be reported (no false alarms)"
    assert "events" not in set(namespace) | BUILTIN_NAMES
