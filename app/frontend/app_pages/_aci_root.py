"""Run once per page: repo root on ``sys.path`` before ``import app``."""

from __future__ import annotations

import sys
from pathlib import Path

_FRONTEND = Path(__file__).resolve().parent.parent
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

from load_root import install_project_root

install_project_root(from_file=__file__)

from app.frontend.bootstrap import ensure_project_root

ensure_project_root()
