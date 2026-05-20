from __future__ import annotations

from pathlib import Path

import _aci_root  # noqa: F401

import streamlit as st

_P = Path(__file__).parent

from app.frontend.meeting_dashboard import list_report_paths, render_recording_kpi_card
from app.frontend.meeting_registry import get_entry, meeting_id_from_report_filename
from app.frontend.product_theme import centered_narrow
from app.frontend.streamlit_nav import query_report_name

_, center, _ = centered_narrow()
with center:
    st.markdown("## Your meetings")
    st.caption("Open a meeting for the full insight layout.")

    paths = list_report_paths()
    if not paths:
        st.warning("No meetings yet.")
        st.page_link(str(_P / "upload_recording.py"), label="Upload recording", icon="📤")
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
