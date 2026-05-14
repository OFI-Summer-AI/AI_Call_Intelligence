"""Extract executive-friendly snippets from final_report JSON (dedupe, no giant dumps)."""

from __future__ import annotations

import ast
import re
from typing import Any


def _safe_snip(s: str, n: int = 220) -> str:
    t = str(s or "").strip().replace("\n", " ")
    return (t[: n - 1] + "…") if len(t) > n else t


def executive_bullets(summary: str, *, max_n: int = 5) -> list[str]:
    """Up to ``max_n`` short bullets from the packaged summary only (single source)."""
    t = str(summary or "").strip()
    if not t:
        return []
    parts = re.split(r"(?<=[.!?])\s+", t)
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if len(p) < 28:
            continue
        out.append(_safe_snip(p, 200))
        if len(out) >= max_n:
            break
    if not out and t:
        out = [_safe_snip(t, 240)]
    return out[:max_n]


def guess_meeting_datetime(meeting_id: str) -> str:
    m = re.search(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", meeting_id)
    if not m:
        return "—"
    y, mo, d, hh, mm, ss = m.groups()
    return f"{y}-{mo}-{d} {hh}:{mm}"


def format_duration_hms(data: dict[str, Any]) -> str:
    vm = data.get("video_metadata") or {}
    sec = vm.get("duration_seconds")
    if isinstance(sec, (int, float)) and sec > 0:
        total = int(round(float(sec)))
    else:
        tr = data.get("transcript") or []
        if not tr:
            return "—"
        from app.frontend.chart_helpers import parse_ts

        total = int(max(parse_ts(s.get("end", "0")) for s in tr))
    mm, ss = divmod(total, 60)
    hh, mm = divmod(mm, 60)
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


def budget_label(ef: dict[str, Any], cq: dict[str, Any]) -> str:
    b = str(ef.get("budget") or "").strip().lower()
    if not b:
        return "Not captured"
    if "no explicit" in b or ("not" in b and "discuss" in b):
        return "No"
    if "not" in b and "budget" in b:
        return "No"
    return "Discussed"


def engagement_label(data: dict[str, Any]) -> str:
    from app.frontend.chart_helpers import sentiment_curve

    curve = sentiment_curve(data.get("transcript") or [], n_bins=14)
    if curve.empty or curve["tone"].abs().sum() < 1e-6:
        return "Medium"
    m = float(curve["tone"].mean())
    if m > 0.08:
        return "High"
    if m < -0.06:
        return "Low"
    return "Medium"


def decision_clarity_label(cq: dict[str, Any]) -> str:
    cf = cq.get("call_assessment") if isinstance(cq.get("call_assessment"), dict) else {}
    v = str(cf.get("budget_and_eta_captured") or "").lower()
    if "lacking" in v or "not" in v and "budget" in v:
        return "Medium"
    if "clear" in v or "captured" in v:
        return "High"
    return "Medium"


def recommendation_banner_text(cq: dict[str, Any]) -> str:
    raw = str(cq.get("recommendation") or "").strip()
    if not raw:
        raw = "review"
    pretty = raw.replace("_", " ").strip().title()
    return f"Recommendation: {pretty} - align sales and delivery on agreed next steps."


def parse_polished_list(val: Any) -> list[str]:
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    if isinstance(val, str):
        s = val.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                out = ast.literal_eval(s)
                if isinstance(out, list):
                    return [str(x).strip() for x in out if str(x).strip()]
            except (SyntaxError, ValueError, TypeError):
                pass
        return [s] if s else []
    return []


def pain_points_from_polished(pt: dict[str, Any]) -> list[str]:
    """Short pain cards (no full narrative dump)."""
    keys = (
        "client_problem",
        "client_pain_points",
        "main_discussion",
    )
    seen: set[str] = set()
    out: list[str] = []
    for k in keys:
        t = str(pt.get(k) or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(_safe_snip(t, 280))
        if len(out) >= 4:
            break
    return out


def risk_severity_prefix(text: str) -> str:
    low = text.lower()
    if any(x in low for x in ("legal", "gdpr", "compliance", "security breach", "blocker")):
        return "[HIGH] "
    if any(x in low for x in ("budget", "delay", "uncertain", "pending")):
        return "[WATCH] "
    return "[INFO] "


def compliance_mentions(ef: dict[str, Any], risks: list[str]) -> list[str]:
    blob = " ".join(
        [
            str(ef.get("risks") or ""),
            str(ef.get("client_problem") or ""),
            " ".join(risks),
        ]
    ).lower()
    tags = []
    for label, needle in (
        ("Recording / storage", "recording"),
        ("Data sharing", "data sharing"),
        ("GDPR / privacy", "gdpr"),
        ("Vendor / security review", "security"),
    ):
        if needle in blob and label not in tags:
            tags.append(label)
    return tags[:6]


def transcript_highlights(transcript: list[dict[str, Any]], *, max_n: int = 4) -> list[str]:
    """Short quoted moments (keyword-rich lines)."""
    keys = ("compliance", "budget", "security", "recording", "integration", "timeline")
    picks: list[str] = []
    for seg in transcript:
        tx = str(seg.get("text") or "")
        low = tx.lower()
        if not any(k in low for k in keys):
            continue
        role = seg.get("role") or seg.get("speaker") or "Speaker"
        picks.append(f"'{_safe_snip(tx, 140)}' at {seg.get('start', '')} ({role})")
        if len(picks) >= max_n:
            break
    return picks
