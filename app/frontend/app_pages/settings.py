from __future__ import annotations

import _aci_root  # noqa: F401

import streamlit as st

from app.config import DATA_DIR, REPORTS_FINAL_DIR, UPLOAD_DIR
from app.frontend.product_theme import centered_narrow

_, center, _ = centered_narrow()
with center:
    st.markdown("## Settings")
    st.caption("Preferences and where your files are stored on this computer.")

    with st.container(border=True):
        st.markdown("##### Account")
        st.text_input("Your name", placeholder="Optional", disabled=True)
        st.text_input("Email", placeholder="Optional", disabled=True)

        st.divider()
        st.markdown("##### Google")
        st.button("Connect Google Calendar", disabled=True, help="Coming soon")
        st.caption("Calendar is required for the live meeting assistant.")

        st.divider()
        st.markdown("##### AI preferences")
        st.selectbox("Summary length", ["Short", "Standard", "Detailed"], index=1, disabled=True)
        st.selectbox("Report language", ["English", "Hindi", "Spanish"], index=0, key="settings_report_lang")

        st.divider()
        st.markdown("##### Storage (this project)")
        st.text_input("Uploads folder", value=str(UPLOAD_DIR), disabled=True)
        st.text_input("Reports folder", value=str(REPORTS_FINAL_DIR), disabled=True)
        st.text_input("Data root", value=str(DATA_DIR), disabled=True)
