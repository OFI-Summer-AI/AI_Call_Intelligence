from __future__ import annotations

from pathlib import Path

import _aci_root  # noqa: F401

import streamlit as st

_P = Path(__file__).parent

from app.orchestrator.pipeline import Pipeline

st.markdown("## Preparing your meeting insights")
st.caption("Please keep this tab open — first-time analysis can take several minutes.")

path_str = st.session_state.get("pending_video_path")
if not path_str:
    st.warning("Nothing to process right now.")
    st.page_link(str(_P / "upload_recording.py"), label="Go to upload", icon="📤")
    st.stop()

path = Path(path_str)
if not path.exists():
    st.error("The uploaded file is no longer on disk. Please upload again.")
    st.session_state.pop("pending_video_path", None)
    st.session_state.pop("processing_inflight_path", None)
    st.stop()

if st.session_state.get("processing_complete_path") == path_str:
    report_name = st.session_state.get("processing_report_name")
    if report_name:
        st.session_state["selected_report"] = report_name
        st.query_params["report"] = report_name
        st.session_state.pop("pending_video_path", None)
        st.switch_page(str(_P / "meeting_dashboard.py"))
    st.stop()

if st.session_state.get("processing_inflight_path") == path_str:
    st.info("Analysis is already running for this file. Please keep this tab open.")
    st.stop()

st.session_state["processing_inflight_path"] = path_str
try:
    with st.spinner("Working through audio, transcript, and insights…"):
        result = Pipeline().run(str(path.resolve()))
    ap = result.get("artifact_paths") or {}
    fr = ap.get("final_report")
    report_name = Path(fr).name if fr else f"{path.stem}_final_report.json"
    st.session_state["processing_complete_path"] = path_str
    st.session_state["processing_report_name"] = report_name
    st.session_state["selected_report"] = report_name
    st.session_state.pop("pending_video_path", None)
    st.session_state.pop("processing_inflight_path", None)
    st.query_params["report"] = report_name
    st.switch_page(str(_P / "meeting_dashboard.py"))
except Exception as exc:  # noqa: BLE001
    st.session_state.pop("processing_inflight_path", None)
    st.error("Something went wrong while analyzing this file.")
    st.code(str(exc))
    st.session_state.pop("pending_video_path", None)
    if st.button("Try another upload"):
        st.switch_page(str(_P / "upload_recording.py"))
