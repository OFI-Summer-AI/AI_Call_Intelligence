from __future__ import annotations

import _aci_root  # noqa: F401

from pathlib import Path
import streamlit as st

_P = Path(__file__).parent

from app.frontend.meeting_dashboard import list_report_paths, load_meeting_json, render_meeting_dashboard, resolve_report_path
from app.frontend.streamlit_nav import query_report_name

name = query_report_name() or st.session_state.get("selected_report")
if isinstance(name, list):
    name = name[0] if name else None

path = resolve_report_path(name) if name else None

if name and path is None:
    st.error("We could not find that meeting.")
    st.session_state.pop("selected_report", None)
    if "report" in st.query_params:
        del st.query_params["report"]
    st.page_link(str(_P / "meetings_library.py"), label="Back to meetings", icon="📚")
    st.stop()

if name and query_report_name() != name:
    st.query_params["report"] = name

if not path:
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    st.info("Pick a meeting from your library, or upload a new one.")
    labels = [p.name for p in list_report_paths()]
    if not labels:
        st.markdown("<div style='background:#fefce8; border:1px solid #fde68a; border-radius:8px; padding:0.75rem 1rem; color:#92400e; font-weight:500;'>⚠️ No meetings yet. Upload a recording to get started.</div>", unsafe_allow_html=True)
        st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        if st.button("📤 Upload a recording", use_container_width=False):
            st.switch_page(str(_P / "upload_recording.py"))
        st.stop()
    pick = st.selectbox("Choose a meeting", options=labels)
    if st.button("Open insights"):
        st.session_state["selected_report"] = pick
        st.query_params["report"] = pick
        st.switch_page(str(_P / "meeting_dashboard.py"))
    st.stop()

data = load_meeting_json(str(path))
render_meeting_dashboard(data, path.name, report_path=path)
