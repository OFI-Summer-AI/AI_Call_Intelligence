"""
Root launcher: ``streamlit run streamlit_app.py`` re-execs Streamlit on ``app/frontend/streamlit_app.py``.

Keeps one familiar command while the real multipage app lives next to ``app/frontend/pages/``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _run() -> None:
    root = Path(__file__).resolve().parent
    target = root / "app" / "frontend" / "streamlit_app.py"
    if not target.is_file():
        sys.stderr.write(f"Missing UI entry: {target}\n")
        raise SystemExit(2)
    os.execv(sys.executable, [sys.executable, "-m", "streamlit", "run", str(target)])


# Streamlit executes the entry script in a synthetic ``__main__`` module, so
# ``if __name__ == "__main__"`` never runs here — the launcher must run unconditionally.
_run()
