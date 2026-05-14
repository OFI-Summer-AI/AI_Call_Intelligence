from __future__ import annotations

from app.frontend.bootstrap import ensure_project_root

ensure_project_root()

import streamlit as st

from app.frontend.product_theme import apply_product_theme
from app.frontend.streamlit_nav import sidebar_nav

st.set_page_config(page_title="Live meeting", layout="wide")
apply_product_theme()
sidebar_nav()

st.markdown("## Live meeting assistant")
st.info("Calendar connection and auto-join are planned. You can still explore the insight layout below.")

with st.container(border=True):
    meet_url = st.text_input("Google Meet link", placeholder="https://meet.google.com/...")
    st.button("Join meeting", disabled=True, help="Coming soon")

    st.divider()
    st.markdown("##### Calendar")
    st.button("Connect Google Calendar", disabled=True, help="Coming soon")
    st.caption("When connected, you will see today’s meetings and choose auto-join or ask first.")

    st.divider()
    st.markdown("##### Assistant options")
    st.toggle("Record meeting", value=True, disabled=True)
    st.toggle("Live summaries", value=True, disabled=True)
    st.toggle("Catch-up mode", value=False, disabled=True)
    st.toggle("Auto-create PDF when done", value=True, disabled=True)

    open_preview = st.button("Open insight preview (sample layout)", use_container_width=True)

if open_preview:
    st.session_state["selected_report"] = st.session_state.get("selected_report")
    st.switch_page("pages/05_Meeting_Dashboard.py")
