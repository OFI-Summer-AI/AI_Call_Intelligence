"""
Call Intelligence — single entrypoint with ``st.navigation`` (no duplicate page runs).
"""

from __future__ import annotations

from pathlib import Path

from load_root import install_project_root

install_project_root(from_file=__file__)

from app.frontend.bootstrap import ensure_project_root

ensure_project_root()

import sys

import streamlit as st

from app.frontend.product_theme import apply_product_theme, render_sidebar_brand

_PAGES_DIR = Path(__file__).parent / "app_pages"

# Make app_pages importable so pages can `import _aci_root`
if str(_PAGES_DIR) not in sys.path:
    sys.path.insert(0, str(_PAGES_DIR))


def _page(name: str, *, title: str, icon: str) -> st.Page:
    return st.Page(str(_PAGES_DIR / name), title=title, icon=icon)


def main() -> None:
    st.set_page_config(
        page_title="Call Intelligence",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_product_theme()
    render_sidebar_brand()

    nav = st.navigation(
        [
            _page("home.py", title="Home", icon="🏠"),
            _page("upload_recording.py", title="Upload", icon="📤"),
            _page("live_meeting_setup.py", title="Live meeting (coming soon)", icon="🎙️"),
            _page("meetings_library.py", title="Meetings", icon="📚"),
            _page("meeting_dashboard.py", title="Insights", icon="✨"),
            _page("settings.py", title="Settings", icon="⚙️"),
            _page("processing.py", title="Processing", icon="⏳"),
        ],
        position="sidebar",
    )
    nav.run()


if __name__ == "__main__" or not __name__.startswith("app."):
    main()
