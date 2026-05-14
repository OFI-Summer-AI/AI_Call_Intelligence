from __future__ import annotations

from app.frontend.bootstrap import ensure_project_root

ensure_project_root()

import streamlit as st

from app.frontend.meeting_dashboard import list_report_paths, load_meeting_json, render_meeting_dashboard, resolve_report_path
from app.frontend.product_theme import apply_product_theme
from app.frontend.streamlit_nav import query_report_name, sidebar_nav

st.set_page_config(page_title="Meeting insights", layout="wide")
apply_product_theme()
sidebar_nav()

name = query_report_name() or st.session_state.get("selected_report")
if isinstance(name, list):
    name = name[0] if name else None

path = resolve_report_path(name) if name else None

if name and path is None:
    st.error("We could not find that meeting.")
    st.session_state.pop("selected_report", None)
    if "report" in st.query_params:
        del st.query_params["report"]
    st.page_link("pages/06_Meetings_Library.py", label="Back to meetings", icon="📚")
    st.stop()

if name and query_report_name() != name:
    st.query_params["report"] = name

if not path:
    st.info("Pick a meeting from your library, or upload a new one.")
    labels = [p.name for p in list_report_paths()]
    if not labels:
        st.warning("No meetings yet.")
        st.page_link("pages/02_Upload_Recording.py", label="Upload a recording", icon="📤")
        st.stop()
    pick = st.selectbox("Choose a meeting", options=labels)
    if st.button("Open insights"):
        st.session_state["selected_report"] = pick
        st.query_params["report"] = pick
        st.rerun()
    st.stop()

data = load_meeting_json(str(path))
render_meeting_dashboard(data, path.name, report_path=path)
