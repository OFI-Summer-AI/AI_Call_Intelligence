"""Home — overview cards, quick stats, and recent meetings only."""

from __future__ import annotations

import hashlib
from datetime import datetime

import _aci_root  # noqa: F401

from pathlib import Path
import streamlit as st

_P = Path(__file__).parent

from app.frontend.meeting_dashboard import list_report_paths
from app.frontend.meeting_registry import get_entry, meeting_id_from_report_filename
from app.frontend.product_theme import centered_narrow

_, center, _ = centered_narrow()
with center:
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("## Meeting Intelligence")
    st.caption(
        "Upload a recording for a full insight report — or explore past meetings from the sidebar."
    )

    paths = list_report_paths()
    c1, c2, c3 = st.columns(3)
    c1.metric("Meetings analyzed", len(paths))
    c2.metric("Reports ready", len(paths))
    c3.metric(
        "This week",
        sum(1 for p in paths if (datetime.now().timestamp() - p.stat().st_mtime) < 7 * 86400),
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
        if st.button("👉 Go to upload", key="home_upload", use_container_width=True):
            st.switch_page(str(_P / "upload_recording.py"))
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
        if st.button("👉 Live meeting setup", key="home_live", use_container_width=True):
            st.switch_page(str(_P / "live_meeting_setup.py"))

    st.divider()
    st.markdown("##### Recent meetings")
    recent = paths[:6]
    if not recent:
        st.markdown(
            "<div class='aci-info-box'>ℹ️ Analyzed meetings will appear here.</div>",
            unsafe_allow_html=True,
        )
    else:
        for p in recent:
            mid = meeting_id_from_report_filename(p.name)
            meta = get_entry(mid)
            title = meta.get("display_title") or mid.replace("_", " ").title()
            when = datetime.fromtimestamp(p.stat().st_mtime).strftime("%b %d, %Y")
            uid = hashlib.md5(p.name.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
            st.markdown(
                f'<div class="recent-row"><b>{title}</b> · {when}<br/>'
                f'<span style="color:#6b7280;font-size:0.8rem;">{p.name}</span></div>',
                unsafe_allow_html=True,
            )
            if st.button("Open insights", key=f"hm_{uid}"):
                st.session_state["selected_report"] = p.name
                st.query_params["report"] = p.name
                st.switch_page(str(_P / "meeting_dashboard.py"))
