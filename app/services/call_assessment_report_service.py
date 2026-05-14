"""
Layered outputs (derived from raw evidence, never mutating it):

- Polished transcript (no timestamps in body; headings; topic grouping).
- Question-template evaluation + conformance score.
- Call assessment, lightweight individual assessment, insights, next actions,
  conclusions, dual summaries, recommendation enum.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from openai import OpenAI

from app.config import LLM_MODEL, OPENAI_API_KEY
from app.services.call_evaluation_template import DISCOVERY_QUESTIONS, template_for_prompt

_RECOMMENDATIONS = frozenset(
    {"proceed", "follow_up", "re_scope", "escalate", "validate_again"}
)

_POLISHED_KEYS = (
    "meeting_overview",
    "main_discussion",
    "technical_details",
    "non_technical_details",
    "quantitative_insights",
    "client_problem",
    "solution_discussion",
    "timeline",
    "budget",
    "risks",
    "next_steps",
)


def _strip_json_fence(raw: str) -> str:
    m = re.match(r"^\s*```(?:json)?\s*\n?(.*?)\n?```\s*$", raw, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else raw


def _build_timestamped_transcript(segments: List[Dict]) -> str:
    lines: List[str] = []
    for seg in segments:
        sp = seg.get("speaker", "Unknown")
        role = seg.get("role")
        label = f"{sp}" + (f" ({role})" if role else "")
        start = seg.get("start", "")
        end = seg.get("end", "")
        text = seg.get("text", "")
        conf_bits: List[str] = []
        if seg.get("avg_logprob") is not None:
            conf_bits.append(f"avg_logprob={seg.get('avg_logprob')}")
        if seg.get("no_speech_prob") is not None:
            conf_bits.append(f"no_speech_prob={seg.get('no_speech_prob')}")
        if seg.get("confidence") is not None:
            conf_bits.append(f"confidence={seg.get('confidence')}")
        tail = f" [{'; '.join(conf_bits)}]" if conf_bits else ""
        lines.append(f"[{start} – {end}] {label}: {text}{tail}")
    return "\n".join(lines)


def _normalize_question_status(raw: str) -> str:
    s = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "partial": "partially_answered",
        "not_addressed": "not_answered",
        "unclear": "unclear_conflicting",
        "unclear_or_conflicting": "unclear_conflicting",
    }
    s = aliases.get(s, s)
    if s in ("answered", "partially_answered", "not_answered", "unclear_conflicting"):
        return s
    return "not_answered"


def _status_weight(status: str) -> float:
    if status == "answered":
        return 1.0
    if status == "partially_answered":
        return 0.55
    if status == "unclear_conflicting":
        return 0.35
    return 0.0


def _merge_question_coverage(llm_rows: Any) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    if isinstance(llm_rows, list):
        for row in llm_rows:
            if not isinstance(row, dict):
                continue
            qid = str(row.get("question_id") or "").strip()
            if qid:
                by_id[qid] = row

    out: List[Dict[str, Any]] = []
    for q in DISCOVERY_QUESTIONS:
        qid = q["id"]
        row = by_id.get(qid, {})
        status = _normalize_question_status(str(row.get("status") or ""))
        conf = str(row.get("confidence") or "low").lower()
        if conf not in ("high", "medium", "low"):
            conf = "low"
        out.append(
            {
                **q,
                "status": status,
                "confidence": conf,
                "notes": str(row.get("notes") or "").strip(),
                "evidence": str(row.get("evidence") or "").strip(),
            }
        )
    return out


def _conformance_stats(coverage: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(coverage)
    if n == 0:
        return {
            "score_0_100": 0,
            "answered": 0,
            "partially_answered": 0,
            "not_answered": 0,
            "unclear_conflicting": 0,
            "weighted_coverage_0_100": 0,
        }
    answered = sum(1 for c in coverage if c.get("status") == "answered")
    partial = sum(1 for c in coverage if c.get("status") == "partially_answered")
    missing = sum(1 for c in coverage if c.get("status") == "not_answered")
    unclear = sum(1 for c in coverage if c.get("status") == "unclear_conflicting")
    weighted = sum(_status_weight(str(c.get("status"))) for c in coverage)
    score = int(round(100.0 * weighted / n))
    return {
        "score_0_100": score,
        "answered": answered,
        "partially_answered": partial,
        "not_answered": missing,
        "unclear_conflicting": unclear,
        "weighted_coverage_0_100": score,
    }


def weighted_conformance_percent(coverage: List[Dict[str, Any]]) -> float | None:
    """
    Weighted discovery coverage as a percentage (same basis as ``score_0_100``),
    without rounding to an integer — e.g. 81.875 → useful for explaining ~82/100.
    """
    if not coverage:
        return None
    n = len(coverage)
    weighted = sum(_status_weight(str(c.get("status") or "")) for c in coverage if isinstance(c, dict))
    if n <= 0:
        return None
    return 100.0 * weighted / n


def _empty_polished() -> Dict[str, str]:
    return {k: "" for k in _POLISHED_KEYS}


def _empty_package(note: str) -> Dict[str, Any]:
    cov = _merge_question_coverage([])
    conf = _conformance_stats(cov)
    return {
        "polished_transcript": _empty_polished(),
        "topic_wise_summary": [],
        "question_coverage": cov,
        "call_quality_report": _default_call_quality_report(note, conf, cov),
        "assessment_note": note,
    }


def _default_call_quality_report(
    note: str, conf: Dict[str, Any], cov: List[Dict[str, Any]]
) -> Dict[str, Any]:
    return {
        "conformance": {
            **conf,
            "narrative": note,
            "critical_gaps_summary": "",
        },
        "call_assessment": {
            "objective_met": "",
            "pain_points_identified": "",
            "solution_fit_discussed": "",
            "budget_and_eta_captured": "",
            "open_risks": "",
            "overall_judgment": note or "",
        },
        "individual_assessment": [],
        "insights": [],
        "next_actions": [],
        "conclusion": "",
        "recommendation": "follow_up",
        "call_level_summary": "",
        "user_level_summary": "",
        "participant_summaries": [],
        "legacy_assessment_of_call": "",
        "legacy_recommendations": [],
        "conformance_score_0_100": conf["score_0_100"],
        "questions_answered_fully": conf["answered"],
        "questions_partial": conf["partially_answered"],
        "questions_not_answered": conf["not_answered"],
        "questions_unclear": conf["unclear_conflicting"],
        "questions_total": len(cov),
        "conformance_summary": note,
        "assessment_of_call": "",
        "assessment_of_individuals": [],
        "conclusions": "",
        "recommendations": [],
    }


def _as_str_list(val: Any, max_items: int = 12) -> List[str]:
    if isinstance(val, str):
        val = val.strip()
        return [val] if val else []
    if not isinstance(val, list):
        return []
    out = [str(x).strip() for x in val if x is not None and str(x).strip()]
    return out[:max_items]


def _coerce_recommendation(val: Any) -> str:
    s = str(val or "").strip().lower()
    s = s.replace(" ", "_").replace("-", "_")
    if s in _RECOMMENDATIONS:
        return s
    return "follow_up"


def _finalize_polished(raw: Any) -> Dict[str, str]:
    base = _empty_polished()
    if not isinstance(raw, dict):
        return base
    for k in _POLISHED_KEYS:
        if k in raw and raw[k]:
            base[k] = str(raw[k]).strip()
    fallbacks = {
        "meeting_overview": ("discussion_overview",),
        "client_problem": ("client_pain_points",),
        "solution_discussion": ("proposed_direction_or_solution", "main_topics"),
        "timeline": (),
        "budget": (),
        "risks": (),
        "next_steps": (),
    }
    for canonical, legacy_keys in fallbacks.items():
        if base.get(canonical):
            continue
        for lk in legacy_keys:
            v = raw.get(lk)
            if v:
                base[canonical] = str(v).strip()
                break
    cp = str(raw.get("current_process_and_constraints") or "").strip()
    if cp:
        extra = "\n\nCurrent process / constraints:\n" + cp
        if base.get("solution_discussion"):
            base["solution_discussion"] = base["solution_discussion"] + extra
        else:
            base["solution_discussion"] = "Current process / constraints:\n" + cp
    return base


def _finalize_topic_wise(val: Any) -> List[Dict[str, str]]:
    if not isinstance(val, list):
        return []
    out: List[Dict[str, str]] = []
    for row in val:
        if not isinstance(row, dict):
            continue
        t = str(row.get("topic") or row.get("title") or "").strip()
        s = str(row.get("summary") or row.get("narrative") or "").strip()
        if t or s:
            out.append({"topic": t, "summary": s})
    return out[:24]


def snapshot_raw_evidence(segments: List[Dict]) -> List[Dict[str, Any]]:
    """
    Immutable audit slice: timestamps, speaker, text, optional STT diagnostics.
    Do not attach LLM-derived ``role`` here — that belongs in ``transcript``.
    """
    out: List[Dict[str, Any]] = []
    for seg in segments:
        row: Dict[str, Any] = {
            "start": seg.get("start"),
            "end": seg.get("end"),
            "text": seg.get("text", ""),
        }
        if seg.get("speaker") is not None:
            row["speaker"] = seg.get("speaker")
        for key in (
            "avg_logprob",
            "no_speech_prob",
            "compression_ratio",
            "temperature",
            "confidence",
        ):
            if key in seg and seg[key] is not None:
                row[key] = seg[key]
        out.append(row)
    return out


class CallAssessmentReportService:
    """One structured LLM pass: polished + topics + checklist + report."""

    def __init__(self) -> None:
        self._client: OpenAI | None = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    def build(
        self,
        transcript_with_roles: List[Dict],
        extracted_fields: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self._client:
            return _empty_package("OPENAI_API_KEY not set; skipped call assessment report.")

        checklist_json = json.dumps(template_for_prompt(), ensure_ascii=False, indent=2)
        fields_json = json.dumps(extracted_fields, ensure_ascii=False, indent=2)
        transcript_block = _build_timestamped_transcript(transcript_with_roles)

        prompt = f"""
You are a senior sales QA lead. Output ONE JSON object. Prioritize a **clear, polished
business narrative** of the meeting (not per-speaker attribution when labels are generic).

Structured extraction hints (may be incomplete):
{fields_json}

Discovery checklist (evaluate each id using timestamped evidence):
{checklist_json}

Transcript (timestamped; evidence only — never paste bracketed timestamps into polished prose):
{transcript_block}

Return ONLY valid JSON (no markdown fences) with this shape:
{{
  "polished_transcript": {{
    "meeting_overview": "2–6 sentences: purpose of the meeting and the headline outcome or tension.",
    "main_discussion": "Dense paragraph(s): what was actually discussed, major threads, decisions implied.",
    "technical_details": "Systems, platforms, integrations, APIs, security, data, tooling — or explicit 'Not meaningfully discussed'.",
    "non_technical_details": "Process, org dynamics, stakeholder concerns, commercial framing, change management — or explicit gaps.",
    "quantitative_insights": "Bullet-style lines (still a single string): every concrete number, date, duration, %, currency, SLA, volume, headcount, or version mentioned; if none, say 'No explicit figures stated in the call.'",
    "client_problem": "Pain, pressure, desired outcomes — prose only.",
    "solution_discussion": "What was explored or proposed — merged, non-repetitive.",
    "timeline": "Dates, milestones, ETA, urgency — quote any explicit dates/durations from the call.",
    "budget": "Budget, pricing, ROI, approval limits — quote explicit amounts if any; else gaps.",
    "risks": "Risks, blockers, compliance sensitivities discussed.",
    "next_steps": "Agreed or implied follow-ups (merged, no duplicate bullets)."
  }},
  "topic_wise_summary": [
    {{"topic": "Short topic label", "summary": "2–4 sentences, no timestamps"}}
  ],
  "question_coverage": [
    {{
      "question_id": "<must match checklist id>",
      "status": "answered|partially_answered|not_answered|unclear_conflicting",
      "confidence": "high|medium|low",
      "notes": "1–3 sentences",
      "evidence": "Very short paraphrase (no long quotes)"
    }}
  ],
  "conformance": {{
    "narrative": "2–4 sentences: how complete discovery was vs checklist.",
    "critical_gaps_summary": "What was weak or missing on critical threads."
  }},
  "call_assessment": {{
    "objective_met": "Did the call achieve its apparent objective?",
    "pain_points_identified": "Were client pains clear?",
    "solution_fit_discussed": "Was fit/scope discussed credibly?",
    "budget_and_eta_captured": "Budget + timeline signal quality.",
    "open_risks": "Residual risks.",
    "overall_judgment": "Short call-level judgment paragraph."
  }},
  "individual_assessment": [],
  "insights": ["Short bullet insights tied to gaps"],
  "next_actions": ["Operational follow-ups with implied owner when possible"],
  "conclusion": "Executive wrap-up.",
  "recommendation": "proceed|follow_up|re_scope|escalate|validate_again",
  "call_level_summary": "What the meeting was about, what was agreed, what is open (one block).",
  "user_level_summary": "Optional: organizational or process-level takeaways only — do NOT attribute behavior to unnamed speakers; may be a short neutral note if not appropriate.",
  "participant_summaries": []
}}

Rules:
- ``question_coverage``: exactly one row per checklist id, same order as checklist.
- Polished + topic summaries: NO ``[hh:mm:ss]`` strings; merge obvious repeated statements.
- ``recommendation`` must be exactly one of the five enum tokens.
- **Per-speaker / individual performance is out of scope:** keep ``individual_assessment`` as ``[]``
  and ``participant_summaries`` as ``[]`` until diarization provides reliable speakers.
  Still write a strong **call-level** narrative in polished fields and ``call_level_summary``.
- For ``quantitative_insights``, mine the transcript for any explicit figures (dates, money, durations).
- Cap lists at ~8 items each; topic_wise_summary at ~10 rows.
"""

        raw = ""
        try:
            response = self._client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You output only valid JSON for sales call QA, layered transcripts, and scoring.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            raw = (response.choices[0].message.content or "").strip()
            raw = _strip_json_fence(raw)
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            head = raw[:1200] if raw else ""
            return _empty_package(f"Assessment JSON parse failed: {e}. Head: {head!r}")
        except Exception as e:
            return _empty_package(f"Assessment request failed: {e!r}")

        if not isinstance(data, dict):
            return _empty_package("Assessment LLM returned non-object JSON.")

        polished = _finalize_polished(data.get("polished_transcript"))
        topics = _finalize_topic_wise(data.get("topic_wise_summary"))
        cov = _merge_question_coverage(data.get("question_coverage"))
        conf_stats = _conformance_stats(cov)

        conf_block = data.get("conformance")
        if not isinstance(conf_block, dict):
            conf_block = {}
        narrative = str(conf_block.get("narrative") or "").strip()
        gaps = str(conf_block.get("critical_gaps_summary") or "").strip()
        conformance_obj = {
            **conf_stats,
            "narrative": narrative,
            "critical_gaps_summary": gaps,
        }

        call_a = data.get("call_assessment")
        if not isinstance(call_a, dict):
            call_a = {}
        call_assessment = {
            "objective_met": str(call_a.get("objective_met") or "").strip(),
            "pain_points_identified": str(call_a.get("pain_points_identified") or "").strip(),
            "solution_fit_discussed": str(call_a.get("solution_fit_discussed") or "").strip(),
            "budget_and_eta_captured": str(call_a.get("budget_and_eta_captured") or "").strip(),
            "open_risks": str(call_a.get("open_risks") or "").strip(),
            "overall_judgment": str(call_a.get("overall_judgment") or "").strip(),
        }

        # Per-speaker scoring disabled until reliable diarization.
        individual_assessment: List[Dict[str, Any]] = []

        insights = _as_str_list(data.get("insights"))
        next_actions = _as_str_list(data.get("next_actions"))
        conclusion = str(data.get("conclusion") or "").strip()
        recommendation = _coerce_recommendation(data.get("recommendation"))
        call_level_summary = str(data.get("call_level_summary") or "").strip()
        user_level_summary = str(data.get("user_level_summary") or "").strip()

        participant_summaries: List[Dict[str, Any]] = []

        legacy_individuals: List[Dict[str, Any]] = []

        legacy_recs = [recommendation]
        if next_actions:
            legacy_recs.extend(next_actions[:5])

        report: Dict[str, Any] = {
            "conformance": conformance_obj,
            "call_assessment": call_assessment,
            "individual_assessment": individual_assessment,
            "insights": insights,
            "next_actions": next_actions,
            "conclusion": conclusion,
            "recommendation": recommendation,
            "call_level_summary": call_level_summary,
            "user_level_summary": user_level_summary,
            "participant_summaries": participant_summaries,
            "legacy_assessment_of_call": call_assessment.get("overall_judgment", ""),
            "legacy_recommendations": legacy_recs,
            "conformance_score_0_100": conf_stats["score_0_100"],
            "questions_answered_fully": conf_stats["answered"],
            "questions_partial": conf_stats["partially_answered"],
            "questions_not_answered": conf_stats["not_answered"],
            "questions_unclear": conf_stats["unclear_conflicting"],
            "questions_total": len(cov),
            "conformance_summary": narrative or conformance_obj.get("narrative", ""),
            "assessment_of_call": call_assessment.get("overall_judgment", ""),
            "assessment_of_individuals": legacy_individuals,
            "conclusions": conclusion,
            "recommendations": legacy_recs,
        }

        return {
            "polished_transcript": polished,
            "topic_wise_summary": topics,
            "question_coverage": cov,
            "call_quality_report": report,
            "assessment_note": "",
        }
