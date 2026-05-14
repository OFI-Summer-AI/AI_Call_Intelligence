"""
Landing — guided entry (sidebar is the only nav duplicate).
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from app.frontend.bootstrap import ensure_project_root

ensure_project_root()

import streamlit as st

from app.frontend.meeting_dashboard import list_report_paths
from app.frontend.meeting_registry import get_entry, meeting_id_from_report_filename
from app.frontend.product_theme import apply_product_theme, centered_narrow
from app.frontend.streamlit_nav import sidebar_nav


def main() -> None:
    st.set_page_config(
        page_title="Call Intelligence",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_product_theme()
    sidebar_nav()

    _, center, _ = centered_narrow()
    with center:
        st.markdown("## Meeting intelligence")
        st.caption(
            "Upload a recording for a full insight report — or explore past meetings from the sidebar."
        )

        h1, h2 = st.columns(2, gap="medium")
        with h1:
            st.markdown(
                """
<div class="app-hero">
  <div class="icon">📤</div>
  <h3>Upload a recording</h3>
  <p>Add a video or audio file. We transcribe, score discovery quality, and prepare a shareable PDF.</p>
</div>
""",
                unsafe_allow_html=True,
            )
            st.page_link(
                "pages/02_Upload_Recording.py",
                label="Go to upload",
                icon="👉",
            )
        with h2:
            st.markdown(
                """
<div class="app-hero">
  <div class="icon">🎙️</div>
  <h3>Live assistant</h3>
  <p>Google Meet and calendar connections are on the way. You can preview the setup flow anytime.</p>
</div>
""",
                unsafe_allow_html=True,
            )
            st.page_link(
                "pages/03_Live_Meeting_Setup.py",
                label="Live meeting setup",
                icon="👉",
            )

        st.divider()
        st.markdown("##### Recent meetings")
        paths = list_report_paths()[:6]
        if not paths:
            st.info("Analyzed meetings will appear here.")
            return
        for p in paths:
            mid = meeting_id_from_report_filename(p.name)
            meta = get_entry(mid)
            title = meta.get("display_title") or mid.replace("_", " ").title()
            when = datetime.fromtimestamp(p.stat().st_mtime).strftime("%b %d, %Y")
            uid = hashlib.md5(p.name.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
            st.markdown(
                f'<div class="recent-row"><b>{title}</b> · {when}<br/><span style="color:#6b7280;font-size:0.8rem;">{p.name}</span></div>',
                unsafe_allow_html=True,
            )
            if st.button("Open insights", key=f"hm_{uid}"):
                st.session_state["selected_report"] = p.name
                st.query_params["report"] = p.name
                st.switch_page("pages/05_Meeting_Dashboard.py")


main()
