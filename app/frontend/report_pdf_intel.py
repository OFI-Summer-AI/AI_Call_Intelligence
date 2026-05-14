"""
Meeting-specific signals for executive PDF (tables + tactical copy; no extra LLM calls).
"""

from __future__ import annotations

import ast
import re
from typing import Any

from app.frontend.chart_helpers import parse_ts, sentiment_curve

_GENERIC_INSIGHT_PAT = re.compile(
    r"crucial for successful|important to remember|key to success|essential for|"
    r"plays? a vital role|cannot be overstated|moving forward|at the end of the day",
    re.I,
)


def topic_importance_matrix(
    topic_wise: list[Any],
    transcript: list[dict[str, Any]],
) -> list[tuple[str, str, str, str]]:
    """Rows: Topic | Importance | Sentiment | Discussion depth (heuristic from summary + transcript overlap)."""
    if not isinstance(topic_wise, list) or not topic_wise:
        return [("—", "—", "—", "Run pipeline for topic blocks")]
    blob = " ".join(str(s.get("text", "")) for s in transcript).lower()
    rows: list[tuple[str, str, str, str]] = []
    for row in topic_wise[:10]:
        if not isinstance(row, dict):
            continue
        topic = str(row.get("topic", "Topic"))[:48]
        summ = str(row.get("summary", ""))
        sl = len(summ)
        # Depth from summary substance
        if sl > 220:
            depth = "Deep"
        elif sl > 100:
            depth = "Medium"
        else:
            depth = "Light"
        # Importance: topic words in transcript + summary length
        hits = sum(1 for w in re.findall(r"[A-Za-z]{4,}", topic.lower()) if w in blob)
        if sl > 200 or hits >= 3:
            imp = "High"
        elif sl > 80 or hits >= 1:
            imp = "Medium"
        else:
            imp = "Low"
        # Sentiment from summary wording
        low = summ.lower()
        if any(x in low for x in ("concern", "risk", "challenge", "legal", "compliance", "delay", "uncertain")):
            sent = "Concerned"
        elif any(x in low for x in ("positive", "agree", "excited", "good", "clear", "resolved")):
            sent = "Positive"
        else:
            sent = "Neutral"
        rows.append((topic, imp, sent, depth))
    return rows or [("—", "—", "—", "—")]


def momentum_phases(transcript: list[dict[str, Any]], n_phases: int = 5) -> list[tuple[str, str, float]]:
    """
    Equal time phases with engagement score (segments + words per minute proxy).
    Returns list of (label, band label, score 0-1) for charting.
    """
    if not transcript:
        return [("Phase 1", "Low", 0.0)]
    max_end = max(parse_ts(s.get("end", "0")) for s in transcript) or 1.0
    edges = [max_end * i / n_phases for i in range(n_phases + 1)]
    scores: list[float] = []
    for i in range(n_phases):
        t0, t1 = edges[i], edges[i + 1]
        segs = 0
        words = 0
        for s in transcript:
            st = parse_ts(s.get("start", "0"))
            en = parse_ts(s.get("end", str(st)))
            mid = (st + en) / 2.0
            if t0 <= mid < t1 or (st < t1 and en > t0):
                segs += 1
                words += len(re.findall(r"\w+", str(s.get("text", ""))))
        dur = max(t1 - t0, 1.0)
        # Normalize vs global average
        scores.append(segs / dur * 60.0 + words / max(dur / 60.0, 1.0) * 0.01)
    mx = max(scores) or 1.0
    normed = [s / mx for s in scores]
    out: list[tuple[str, str, float]] = []
    for i, sc in enumerate(normed):
        m0 = int(edges[i] // 60)
        m1 = int(edges[i + 1] // 60)
        label = f"{m0}-{m1} min"
        if sc >= 0.78:
            band = "Very high"
        elif sc >= 0.55:
            band = "High"
        elif sc >= 0.35:
            band = "Medium"
        else:
            band = "Low"
        out.append((f"Segment {i + 1}", label, sc))
    return out


def discovery_checklist_pdf_rows(question_coverage: list[Any]) -> list[tuple[str, str, str, str]]:
    """Question | status + confidence | model notes | evidence (for PDF, Latin-1 safe via caller)."""
    if not isinstance(question_coverage, list) or not question_coverage:
        return [("—", "—", "No checklist rows in this export.", "—")]
    rows: list[tuple[str, str, str, str]] = []
    for row in question_coverage[:10]:
        if not isinstance(row, dict):
            continue
        q = str(row.get("title", row.get("id", "?")))[:52]
        st = str(row.get("status", "")).replace("_", " ").strip().title()
        conf = str(row.get("confidence", "")).strip().title()
        status_cell = f"{st} / {conf}" if conf else st
        notes = str(row.get("notes", "") or "").strip()
        ev = str(row.get("evidence", "") or "").strip()
        rows.append(
            (
                q,
                status_cell,
                notes if notes else "-",
                ev if ev else "-",
            )
        )
    return rows or [("—", "—", "—", "—")]


def missing_discussion_areas(question_coverage: list[Any]) -> list[str]:
    out: list[str] = []
    if not isinstance(question_coverage, list):
        return out
    for row in question_coverage:
        if not isinstance(row, dict):
            continue
        st = str(row.get("status", "")).lower()
        if st in ("not_answered", "partially_answered", "unclear"):
            t = str(row.get("title", "")).strip()
            if t:
                out.append(t)
    return out[:10]


def tactical_client_signals(
    cq: dict[str, Any],
    pt: dict[str, Any],
    transcript: list[dict[str, Any]],
    topic_wise: list[Any],
    question_coverage: list[Any] | None = None,
) -> list[str]:
    """Meeting-grounded lines (evidence-backed where possible)."""
    sig: list[str] = []
    cov = question_coverage if isinstance(question_coverage, list) else []
    for row in cov:
        if not isinstance(row, dict):
            continue
        st = str(row.get("status", "")).lower()
        title = str(row.get("title", ""))
        ev = str(row.get("evidence", "")).strip()
        if st == "not_answered" and "budget" in title.lower() and ev:
            sig.append(f"Budget maturity stayed open: {ev[:160]}")
        elif st == "partially_answered" and "decision" in title.lower() and ev:
            sig.append(f"Decision ownership still fuzzy: {ev[:160]}")
        elif st == "answered" and "system" in title.lower() and ev:
            sig.append(f"Systems footprint was pinned down: {ev[:140]}")
    # Risks from polished / extracted
    rs = str(pt.get("risks") or "").strip()
    if rs and len(rs) > 20:
        sig.append(f"Risk thread called out in narrative: {rs[:200]}")
    # Transcript: urgency words near compliance
    blob = ""
    for s in transcript[: min(len(transcript), 400)]:
        tx = str(s.get("text", ""))
        low = tx.lower()
        if any(k in low for k in ("compliance", "legal", "recording", "gdpr", "security")) and len(tx) > 40:
            blob = tx[:220]
            break
    if blob:
        sig.append(f"Compliance/recording theme surfaced in conversation: \"{blob}\"")
    # Topic reinforcement
    if isinstance(topic_wise, list):
        for row in topic_wise[:3]:
            if isinstance(row, dict):
                t = str(row.get("topic", ""))
                if "Recording" in t or "Compliance" in t:
                    summ = str(row.get("summary", ""))[:180]
                    if summ:
                        sig.append(f"{t}: {summ}")
                    break
    # De-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for s in sig:
        k = s[:60]
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out[:7]


def strategic_assessment_bullets(
    cq: dict[str, Any],
    ef: dict[str, Any],
    risk: dict[str, Any],
) -> list[str]:
    """CXO-style synthesis from existing structured fields only."""
    bullets: list[str] = []
    cf = cq.get("call_assessment") if isinstance(cq.get("call_assessment"), dict) else {}
    if cf.get("pain_points_identified"):
        bullets.append(f"Pain clarity: {str(cf.get('pain_points_identified'))[:200]}")
    if cf.get("solution_fit_discussed"):
        bullets.append(f"Solution fit: {str(cf.get('solution_fit_discussed'))[:200]}")
    if cf.get("budget_and_eta_captured"):
        bullets.append(f"Commercial capture: {str(cf.get('budget_and_eta_captured'))[:200]}")
    if cf.get("open_risks"):
        bullets.append(f"Open risks noted: {str(cf.get('open_risks'))[:200]}")
    conf = cq.get("conformance") if isinstance(cq.get("conformance"), dict) else {}
    if conf.get("critical_gaps_summary"):
        bullets.append(f"Critical gaps: {str(conf.get('critical_gaps_summary'))[:220]}")
    if conf.get("narrative"):
        bullets.append(f"Discovery narrative: {str(conf.get('narrative'))[:220]}")
    if risk.get("needs_review"):
        bullets.append("Human review was flagged for this meeting (see risk file).")
    if not bullets:
        bullets.append(str(cq.get("conclusion") or cq.get("conclusions") or "See call quality section in product.")[:300])
    return bullets[:8]


def filtered_insights(cq: dict[str, Any]) -> list[str]:
    """Drop generic one-liners; prefer checklist-backed notes."""
    ins = cq.get("insights")
    lines: list[str] = []
    if isinstance(ins, list):
        lines = [str(x).strip() for x in ins if str(x).strip()]
    elif isinstance(ins, str) and ins.strip():
        lines = [ins.strip()]
    out: list[str] = []
    for line in lines:
        if len(line) < 35:
            continue
        if _GENERIC_INSIGHT_PAT.search(line):
            continue
        out.append(line)
    if not out:
        # fall back to shorter list
        out = [x for x in lines if len(x) > 20][:5]
    return out[:6]


def cq_insights_list(cq: dict[str, Any]) -> list[str]:
    """Structured insights from call_quality (counts match Streamlit header strip)."""
    ins = cq.get("insights")
    if isinstance(ins, list):
        return [str(x).strip() for x in ins if str(x).strip()]
    if isinstance(ins, str) and ins.strip():
        return [ins.strip()]
    return []


def cq_conclusion_text(cq: dict[str, Any]) -> str:
    return str(cq.get("conclusion") or cq.get("conclusions") or "").strip()


def _parse_next_steps_blob(blob: str) -> list[str]:
    s = str(blob).strip()
    if not s:
        return []
    if s.startswith("[") and s.endswith("]"):
        try:
            v = ast.literal_eval(s)
            if isinstance(v, (list, tuple)):
                return [str(x).strip() for x in v if str(x).strip()]
        except (SyntaxError, ValueError, TypeError):
            pass
    return [p.strip() for p in re.split(r"[\n;]+", s) if p.strip()]


def merge_next_steps(actions: Any, polished: dict[str, Any]) -> list[str]:
    """Union of call_quality next_actions and polished next_steps (deduped)."""
    out: list[str] = []
    seen: set[str] = set()
    if isinstance(actions, list):
        for a in actions:
            t = str(a).strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                out.append(t)
    blob = polished.get("next_steps") if isinstance(polished, dict) else None
    for t in _parse_next_steps_blob(str(blob or "")):
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def _ascii_clip(s: str, max_chars: int = 200) -> str:
    t = (
        str(s)
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2026", "...")
        .replace('"', "'")
    )
    t = " ".join(t.split())
    if len(t) <= max_chars:
        return t
    cut = t[: max_chars + 1]
    sp = cut.rfind(" ")
    if sp > max_chars * 0.55:
        cut = cut[:sp]
    else:
        cut = cut[:max_chars]
    return cut.rstrip(",.;:") + "..."


def smart_quote_highlights(transcript: list[dict[str, Any]], *, max_n: int = 4) -> list[str]:
    """Score segments: commitments, scale, risk, decisions — not random keyword hits."""
    scored: list[tuple[float, str]] = []
    strong = re.compile(
        r"\b(terabyte|petabyte|gb|tb|must|will not|legal|compliance|gdpr|"
        r"deadline|christmas|q[1-4]|poc|contract|approve|blocker|scale|1500|agents)\b",
        re.I,
    )
    weak = re.compile(r"^(yeah|ok|okay|thanks|hello|hi|um|uh)\b", re.I)
    for seg in transcript:
        tx = str(seg.get("text", "")).strip()
        if len(tx) < 35 or len(tx) > 400:
            continue
        if weak.search(tx):
            continue
        score = float(len(re.findall(r"\w+", tx))) * 0.02
        score += len(strong.findall(tx)) * 2.5
        if "?" in tx:
            score -= 0.5
        if score < 1.2:
            continue
        role = str(seg.get("role") or seg.get("speaker") or "Speaker")
        ts = str(seg.get("start", ""))
        clipped = _ascii_clip(tx, 200)
        scored.append((score, f"{clipped}  (at {ts}, {role})"))
    scored.sort(key=lambda x: -x[0])
    return [t for _, t in scored[:max_n]]


def narrative_opening(pt: dict[str, Any], summary: str) -> str:
    mo = str(pt.get("meeting_overview") or "").strip()
    if len(mo) > 80:
        return mo[:900]
    return str(summary or "").strip()[:900]
