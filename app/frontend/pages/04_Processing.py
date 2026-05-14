from __future__ import annotations

from app.frontend.bootstrap import ensure_project_root

ensure_project_root()

import streamlit as st

from app.orchestrator.pipeline import Pipeline
from app.frontend.product_theme import apply_product_theme
from app.frontend.streamlit_nav import sidebar_nav

st.set_page_config(page_title="Processing", layout="wide")
apply_product_theme()
sidebar_nav()

st.markdown("## Preparing your meeting insights")
st.caption("Please keep this tab open — first-time analysis can take several minutes.")

path_str = st.session_state.get("pending_video_path")
if not path_str:
    st.warning("Nothing to process right now.")
    st.page_link("pages/02_Upload_Recording.py", label="Go to upload", icon="📤")
    st.stop()

path = Path(path_str)
if not path.exists():
    st.error("The uploaded file is no longer on disk. Please upload again.")
    st.session_state.pop("pending_video_path", None)
    st.stop()

try:
    with st.spinner("Working through audio, transcript, and insights…"):
        result = Pipeline().run(str(path.resolve()))
    ap = result.get("artifact_paths") or {}
    fr = ap.get("final_report")
    report_name = Path(fr).name if fr else f"{path.stem}_final_report.json"
    st.session_state["selected_report"] = report_name
    st.session_state.pop("pending_video_path", None)
    st.query_params["report"] = report_name
    st.switch_page("pages/05_Meeting_Dashboard.py")
except Exception as exc:  # noqa: BLE001
    st.error("Something went wrong while analyzing this file.")
    st.code(str(exc))
    st.session_state.pop("pending_video_path", None)
    if st.button("Try another upload"):
        st.switch_page("pages/02_Upload_Recording.py")
