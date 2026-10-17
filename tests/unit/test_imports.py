"""Every module imports cleanly, and the ADN client stays free of Kodi."""
import ast
import importlib
from pathlib import Path

import pytest

LIB = Path(__file__).resolve().parents[2] / "resources" / "lib"
MODULES = sorted(
    ".".join(("resources", "lib", *path.relative_to(LIB).with_suffix("").parts))
    for path in LIB.rglob("*.py")
    if "vendor" not in path.parts and path.name != "__init__.py"
)


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    assert importlib.import_module(name) is not None


@pytest.mark.parametrize("path", sorted((LIB / "adn").glob("*.py")), ids=lambda p: p.name)
def test_adn_client_never_imports_kodi(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    kodi = {name for name in imported if name.startswith("xbmc") or name.startswith("kodi") or ".kodi" in name}
    assert not kodi, kodi
