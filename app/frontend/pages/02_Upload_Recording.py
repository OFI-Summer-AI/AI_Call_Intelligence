from __future__ import annotations

import shutil
from pathlib import Path

from app.frontend.bootstrap import ensure_project_root

ensure_project_root()

import streamlit as st

from app.config import STREAMLIT_MAX_UPLOAD_MB, UPLOAD_DIR
from app.media_inputs import MEDIA_EXTENSIONS
from app.frontend.meeting_registry import upsert_entry
from app.frontend.product_theme import apply_product_theme, centered_narrow
from app.frontend.streamlit_nav import sidebar_nav


def _safe_stem(name: str, fallback: str) -> str:
    base = "".join(c if c.isalnum() or c in "._-" else "_" for c in name.strip())[:80]
    return base or fallback


st.set_page_config(page_title="Upload recording", layout="wide")
apply_product_theme()
sidebar_nav()

_, center, _ = centered_narrow()
with center:
    st.markdown("## Upload a meeting")
    _gib = STREAMLIT_MAX_UPLOAD_MB / 1024.0
    st.caption(
        f"Video or audio — MP4, MOV, MKV, WebM, WAV, MP3, M4A, and more. "
        f"Per-file limit is **{STREAMLIT_MAX_UPLOAD_MB:,} MB** (about {_gib:.1f} GiB). "
        "Huge uploads still need enough RAM and free disk while the browser sends the file; "
        "for multi-hour raw recordings you can copy the file into `data/uploads` and run "
        "`python -m app.main path/to/file.mp4`."
    )
    with st.container(border=True):
        _uploader_types = sorted({e.lstrip(".").lower() for e in MEDIA_EXTENSIONS})
        up = st.file_uploader(
            "File",
            type=_uploader_types,
            label_visibility="collapsed",
            max_upload_size=STREAMLIT_MAX_UPLOAD_MB,
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
        st.session_state["pending_video_path"] = str(dest.resolve())
        st.switch_page("pages/04_Processing.py")
