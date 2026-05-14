"""Resolve on-disk polished markdown and risk JSON for a final report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.pipeline_artifacts import JobArtifactPaths
from app.frontend.meeting_registry import meeting_id_from_report_filename


def job_paths_for_report(report_filename: str) -> JobArtifactPaths:
    stem = meeting_id_from_report_filename(report_filename)
    return JobArtifactPaths(stem)


def load_polished_markdown(paths: JobArtifactPaths) -> str | None:
    p = paths.polished_md
    if p.is_file():
        return p.read_text(encoding="utf-8", errors="replace")
    return None


def load_risk_report_file(paths: JobArtifactPaths) -> dict[str, Any] | None:
    p = paths.risk_report
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def merged_risk_view(data: dict[str, Any], paths: JobArtifactPaths) -> dict[str, Any]:
    """Prefer standalone risk file; merge with embedded ``risk_report`` in final JSON."""
    from_disk = load_risk_report_file(paths) or {}
    embedded = data.get("risk_report") if isinstance(data.get("risk_report"), dict) else {}
    risks: list[str] = []
    for src in (embedded, from_disk):
        r = src.get("risks")
        if isinstance(r, list):
            risks.extend(str(x) for x in r if x)
    seen: set[str] = set()
    dedup: list[str] = []
    for x in risks:
        if x not in seen:
            seen.add(x)
            dedup.append(x)
    needs = bool(from_disk.get("needs_review")) or bool(embedded.get("needs_review"))
    return {"risks": dedup, "needs_review": needs}
