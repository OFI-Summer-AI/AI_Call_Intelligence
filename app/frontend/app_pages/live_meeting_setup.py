from __future__ import annotations

import _aci_root  # noqa: F401

from pathlib import Path
import streamlit as st

_P = Path(__file__).parent

st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
st.markdown("## Live Meeting Assistant")
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
    st.toggle("Record meeting", value=True, disabled=True, key="opt_record")
    st.toggle("Live summaries", value=True, disabled=True, key="opt_summaries")
    st.toggle("Catch-up mode", value=False, disabled=True, key="opt_catchup")
    st.toggle("Auto-create PDF when done", value=True, disabled=True, key="opt_pdf")

    open_preview = st.button("Open insight preview (sample layout)", use_container_width=True)

if open_preview:
    st.switch_page(str(_P / "meeting_dashboard.py"))
