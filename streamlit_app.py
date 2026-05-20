"""
Root launcher: ``streamlit run streamlit_app.py`` delegates to ``app/frontend/streamlit_app.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_FRONTEND = _ROOT / "app" / "frontend"

for _p in (str(_ROOT), str(_FRONTEND)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.frontend.streamlit_app import main

main()
