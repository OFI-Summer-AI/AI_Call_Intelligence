from __future__ import annotations

import shutil
from pathlib import Path

import _aci_root  # noqa: F401

import streamlit as st

_P = Path(__file__).parent

from app.config import STREAMLIT_MAX_UPLOAD_MB, UPLOAD_DIR
from app.media_inputs import MEDIA_EXTENSIONS
from app.frontend.meeting_registry import upsert_entry
from app.frontend.product_theme import centered_narrow


def _safe_stem(name: str, fallback: str) -> str:
    base = "".join(c if c.isalnum() or c in "._-" else "_" for c in name.strip())[:80]
    return base or fallback


_, center, _ = centered_narrow()
with center:
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("## Upload a Meeting")
    _gib = STREAMLIT_MAX_UPLOAD_MB / 1024.0
    st.markdown(
        f"""<p style="color:#000000; font-size:0.95rem; line-height:1.7; margin-bottom:1rem;">
        Video or audio — <strong>MP4, MOV, MKV, WebM, WAV, MP3, M4A</strong>, and more.
        Per-file limit is <strong>{STREAMLIT_MAX_UPLOAD_MB:,} MB</strong> (about {_gib:.1f} GiB).
        Huge uploads still need enough RAM and free disk while the browser sends the file.
        For multi-hour raw recordings, copy the file into <code>data/uploads</code> and run
        <code>python -m app.main path/to/file.mp4</code>.
        </p>""",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        _uploader_types = sorted({e.lstrip(".").lower() for e in MEDIA_EXTENSIONS})
        up = st.file_uploader(
            "File",
            type=_uploader_types,
            label_visibility="collapsed",
            help=f"Max {STREAMLIT_MAX_UPLOAD_MB:,} MB per file (set STREAMLIT_MAX_UPLOAD_MB or .streamlit/config.toml).",
        )
        meeting_name = st.text_input("Meeting name", placeholder="e.g. Acme discovery call")
        client_name = st.text_input("Client or team", placeholder="Optional")
        tags = st.text_input("Tags", placeholder="sales, pilot, q1")
        language = st.selectbox("Language", ["English", "Hindi", "Spanish", "Other"], index=0)

        b1, b2, b3 = st.columns([1.2, 1, 1.2])
        with b2:
            go = st.button("Analyze meeting", type="primary", use_container_width=True)

    if go:
        if not up:
            st.warning("Choose a file first.")
            st.stop()
        suf = Path(up.name).suffix.lower()
        if suf not in MEDIA_EXTENSIONS:
            st.error("That file type is not supported.")
            st.stop()
        stem = _safe_stem(meeting_name, Path(up.name).stem)
        dest = UPLOAD_DIR / f"{stem}{suf}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            up.seek(0)
        except (OSError, AttributeError):
            pass
        with dest.open("wb") as out:
            shutil.copyfileobj(up, out, length=8 * 1024 * 1024)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        upsert_entry(
            stem,
            display_title=meeting_name.strip() or stem.replace("_", " ").title(),
            client_name=client_name.strip() or None,
            tags=tag_list or None,
            language=language,
            source="upload",
        )
        st.session_state.pop("processing_inflight_path", None)
        st.session_state.pop("processing_complete_path", None)
        st.session_state.pop("processing_report_name", None)
        st.session_state["pending_video_path"] = str(dest.resolve())
        st.switch_page(str(_P / "processing.py"))
