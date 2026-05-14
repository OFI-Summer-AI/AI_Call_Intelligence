"""Lightweight display metadata for meetings (title, client, tags, source)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import DATA_DIR

_REGISTRY_PATH = DATA_DIR / "ui" / "meeting_registry.json"


def _safe_id(name: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:120] or "meeting"


def meeting_id_from_report_filename(filename: str) -> str:
    stem = Path(filename).stem
    for suf in ("_final_report", "_result"):
        if stem.endswith(suf):
            return stem[: -len(suf)]
    return stem


def load_registry() -> dict[str, Any]:
    if not _REGISTRY_PATH.exists():
        return {}
    try:
        raw = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_registry(data: dict[str, Any]) -> None:
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REGISTRY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_entry(meeting_id: str) -> dict[str, Any]:
    return dict(load_registry().get(meeting_id) or {})


def upsert_entry(
    meeting_id: str,
    *,
    display_title: str | None = None,
    client_name: str | None = None,
    tags: list[str] | None = None,
    language: str | None = None,
    source: str | None = None,
) -> None:
    reg = load_registry()
    cur = dict(reg.get(meeting_id) or {})
    if display_title is not None:
        cur["display_title"] = display_title
    if client_name is not None:
        cur["client_name"] = client_name
    if tags is not None:
        cur["tags"] = tags
    if language is not None:
        cur["language"] = language
    if source is not None:
        cur["source"] = source
    cur["updated_at"] = datetime.now(timezone.utc).isoformat()
    reg[meeting_id] = cur
    save_registry(reg)
