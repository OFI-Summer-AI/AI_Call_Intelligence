from __future__ import annotations

from app.frontend.bootstrap import ensure_project_root

ensure_project_root()

import streamlit as st

from app.frontend.meeting_dashboard import list_report_paths, render_recording_kpi_card
from app.frontend.meeting_registry import get_entry, meeting_id_from_report_filename
from app.frontend.product_theme import apply_product_theme, centered_narrow
from app.frontend.streamlit_nav import query_report_name, sidebar_nav

st.set_page_config(page_title="Meetings library", layout="wide")
apply_product_theme()
sidebar_nav()

_, center, _ = centered_narrow()
with center:
    st.markdown("## Your meetings")
    st.caption("Open a meeting for the full insight layout.")

    paths = list_report_paths()
    if not paths:
        st.warning("No meetings yet.")
        st.page_link("pages/02_Upload_Recording.py", label="Upload recording", icon="📤")
        st.stop()

    f1, f2 = st.columns(2)
    with f1:
        q = st.text_input("Search", placeholder="Title, client, or file…", key="lib_search")
    with f2:
        client_f = st.text_input("Client", placeholder="Filter", key="lib_client")

    filtered: list[Path] = []
    for p in paths:
        mid = meeting_id_from_report_filename(p.name)
        meta = get_entry(mid)
        title = str(meta.get("display_title") or mid)
        client = str(meta.get("client_name") or "")
        blob = f"{title} {client} {p.name}".lower()
        if q and q.lower() not in blob:
            continue
        if client_f and client_f.lower() not in client.lower() and client_f.lower() not in title.lower():
            continue
        filtered.append(p)

    if not filtered:
        st.info("No matches — clear filters to see all meetings.")
        st.stop()

    for i, p in enumerate(filtered):
        render_recording_kpi_card(p, i)

qr = query_report_name()
if qr:
    st.session_state["selected_report"] = qr
