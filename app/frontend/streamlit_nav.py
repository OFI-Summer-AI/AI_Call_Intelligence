from __future__ import annotations

import streamlit as st


def query_report_name() -> str | None:
    raw = st.query_params.get("report")
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw[0] if raw else None
    return str(raw)


def sidebar_nav() -> None:
    with st.sidebar:
        st.markdown(
            '<p class="sidebar-product">Call Intelligence</p>'
            '<p class="sidebar-tagline">Meeting quality, discovery coverage, and client-ready summaries.</p>',
            unsafe_allow_html=True,
        )
        st.divider()
        st.caption("Navigate")
        st.page_link("streamlit_app.py", label="Home", icon="🏠")
        st.page_link("pages/02_Upload_Recording.py", label="Upload", icon="📤")
        st.page_link("pages/03_Live_Meeting_Setup.py", label="Live meeting", icon="🎙️")
        st.page_link("pages/06_Meetings_Library.py", label="Meetings", icon="📚")
        st.page_link("pages/05_Meeting_Dashboard.py", label="Insights", icon="✨")
        st.page_link("pages/07_Settings.py", label="Settings", icon="⚙️")
        st.divider()
        st.caption("Tip: collapse the rail anytime with the chevron in the header.")
