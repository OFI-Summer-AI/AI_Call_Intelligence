from __future__ import annotations

import streamlit as st


def query_report_name() -> str | None:
    raw = st.query_params.get("report")
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw[0] if raw else None
    return str(raw)
