"""Stdlib-only: put repo root on ``sys.path`` (safe before ``import app``)."""

from __future__ import annotations

import sys
from pathlib import Path

# app/frontend/install_root.py -> repo root is two levels up
ROOT = Path(__file__).resolve().parents[2]


def install() -> Path:
    rs = str(ROOT)
    if rs not in sys.path:
        sys.path.insert(0, rs)
    return ROOT
