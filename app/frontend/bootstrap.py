"""Put project root on ``sys.path`` once (Streamlit cwd can vary)."""

from __future__ import annotations

import sys
from pathlib import Path

_done = False


def ensure_project_root() -> None:
    """Idempotent: repo root contains ``app/`` (this file lives under ``app/frontend/``)."""
    global _done
    if _done:
        return
    root = Path(__file__).resolve().parents[2]
    rs = str(root)
    if rs not in sys.path:
        sys.path.insert(0, rs)
    _done = True
