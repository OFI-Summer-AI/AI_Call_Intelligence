"""Load ``install_root`` via importlib (no ``app`` package required yet)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def install_project_root(*, from_file: str | Path) -> None:
    start = Path(from_file).resolve().parent
    candidates = [
        start / "install_root.py",
        start.parent / "install_root.py",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location("_aci_install_root", path)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.install()
        return
    raise RuntimeError(
        "Could not find install_root.py next to the Streamlit entry or under app/frontend/"
    )
