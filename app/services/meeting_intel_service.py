"""
Executive summary + optional speaker role mapping for dashboard consumption.

Burst-based per-segment role inference (when all STT speakers are ``Unknown``)
is **on hold** until reliable diarization / video-backed speaker ID — the
previous implementation is kept below as commented reference code.

Polished narrative reports live in ``CallAssessmentReportService`` instead.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from openai import OpenAI

from app.config import LLM_MODEL, OPENAI_API_KEY


def _parse_ts_seconds(ts: str) -> float:
    try:
        parts = str(ts).strip().split(":")
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
            return h * 3600 + m * 60 + s
        if len(parts) == 2:
            m, s = int(parts[0]), float(parts[1])
            return m * 60 + s
    except (ValueError, TypeError):
        pass
    return 0.0


def _distinct_speakers(segments: List[Dict]) -> List[str]:
    labels = {str(seg.get("speaker") or "Unknown") for seg in segments}
    return sorted(labels)


def _strip_json_fence(raw: str) -> str:
    m = re.match(r"^\s*```(?:json)?\s*\n?(.*?)\n?```\s*$", raw, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else raw


def cluster_bursts(segments: List[Dict], gap_sec: float) -> List[Dict]:
    """Merge consecutive segments when silence gap between them is <= gap_sec."""
    if not segments:
        return []
    bursts: List[Dict] = []
    cur_indices: List[int] = [0]
    cur_start = segments[0].get("start", "00:00:00")
    cur_end = segments[0].get("end", "00:00:00")
    texts: List[str] = [str(segments[0].get("text", ""))]

    for i in range(1, len(segments)):
        prev_end = _parse_ts_seconds(segments[i - 1].get("end", "00:00:00"))
        cur_start_sec = _parse_ts_seconds(segments[i].get("start", "00:00:00"))
        gap = cur_start_sec - prev_end
        if gap > gap_sec:
            bursts.append(
                {
                    "id": len(bursts),
                    "start": cur_start,
                    "end": cur_end,
                    "text": " ".join(texts).strip(),
                    "indices": list(cur_indices),
                }
            )
            cur_indices = [i]
            cur_start = segments[i].get("start", "00:00:00")
            cur_end = segments[i].get("end", "00:00:00")
            texts = [str(segments[i].get("text", ""))]
        else:
            cur_indices.append(i)
            cur_end = segments[i].get("end", cur_end)
            texts.append(str(segments[i].get("text", "")))

    bursts.append(
        {
            "id": len(bursts),
            "start": cur_start,
            "end": cur_end,
            "text": " ".join(texts).strip(),
            "indices": list(cur_indices),
        }
    )
    return bursts


def _auto_bursts(segments: List[Dict], max_bursts: int = 42) -> List[Dict]:
    gap = 3.0
    while gap <= 15.0:
        bursts = cluster_bursts(segments, gap_sec=gap)
        if len(bursts) <= max_bursts:
            return bursts
        gap += 1.5
    return cluster_bursts(segments, gap_sec=15.0)


def _llm_burst_roles(bursts: List[Dict], extracted_fields: Dict[str, Any]) -> tuple[str, Dict[str, str], List[str]]:
    """Returns summary, speaker_map, burst_roles (parallel to bursts)."""
    fields_json = json.dumps(extracted_fields, ensure_ascii=False, indent=2)
    lines = []
    for b in bursts:
        t = b["text"]
        if len(t) > 240:
            t = t[:237] + "..."
        lines.append(f"{b['id']}. [{b['start']}–{b['end']}] {t}")
    burst_block = "\n".join(lines)

    prompt = f"""
You are annotating a B2B meeting transcript. There is NO reliable speaker diarization — each numbered block is a time-clustered *burst* of speech.

Structured hints (may be incomplete):
{fields_json}

Bursts (one line each):
{burst_block}

Return ONLY valid JSON (no markdown):
{{
  "summary": "Max 3 short sentences for executives.",
  "speaker_map": {{"Unknown": "Mixed speakers (roles inferred per burst)"}},
  "burst_roles": [
     "<role for burst 0>",
     "<role for burst 1>",
     ...
  ]
}}

Rules for burst_roles (same length as number of bursts = {len(bursts)}):
- Use compact labels: "Vendor / host", "Client / partner", "Back-and-forth", "Participant", "Q&A (client)", "Monologue (vendor)".
- Infer from content: who explains internal process/tools vs who asks questions or pushes back.
- Do NOT use phrases like "enable diarization" or "Unlabeled" — always assign a business-meaningful role guess.
- The array MUST have exactly {len(bursts)} strings in order burst 0..{len(bursts) - 1}.
"""

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "You output only compact JSON for meeting dashboards.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    raw = (response.choices[0].message.content or "").strip()
    raw = _strip_json_fence(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        head = raw[:800].replace("\n", " ")
        raise ValueError(f"burst_roles JSON parse failed: {e}; head={head!r}") from e
    if not isinstance(data, dict):
        raise ValueError("invalid json object")
    summary = str(data.get("summary") or "").strip()
    sm = data.get("speaker_map")
    speaker_map = {str(k): str(v) for k, v in sm.items()} if isinstance(sm, dict) else {}
    br = data.get("burst_roles")
    burst_roles: List[str] = []
    if isinstance(br, list):
        burst_roles = [str(x) for x in br]
    # Fix length
    while len(burst_roles) < len(bursts):
        burst_roles.append("Participant")
    burst_roles = burst_roles[: len(bursts)]
    return summary, speaker_map, burst_roles


def _llm_summary_only(
    transcript_segments: List[Dict],
    extracted_fields: Dict[str, Any],
) -> str:
    """Short executive summary only — no speaker roles or participant labels."""
    lines = []
    for seg in transcript_segments[:400]:
        ts = seg.get("start", "")
        lines.append(f"[{ts}] {seg.get('text', '')}")
    transcript_text = "\n".join(lines)
    if len(transcript_segments) > 400:
        transcript_text += "\n[... transcript truncated for summary ...]"
    fields_json = json.dumps(extracted_fields, ensure_ascii=False, indent=2)

    prompt = f"""
You summarize a B2B meeting transcript for an executive dashboard.

Structured hints (may be incomplete):
{fields_json}

Transcript (timestamped lines; use only for factual summary):
{transcript_text}

Return ONLY valid JSON (no markdown):
{{ "summary": "Max 3 short sentences: what the meeting was for and the main outcome or thread." }}

Rules:
- Do NOT assign roles (vendor/client), do NOT name unidentified speakers as parties.
- No bullet points inside the summary string; plain sentences only.
"""

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You output only compact JSON with a single summary field."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    raw = (response.choices[0].message.content or "").strip()
    raw = _strip_json_fence(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    if isinstance(data, dict):
        return str(data.get("summary") or "").strip()
    return ""


def _llm_speaker_map_only(
    transcript_segments: List[Dict],
    extracted_fields: Dict[str, Any],
    speakers: List[str],
) -> tuple[str, Dict[str, str]]:
    transcript_lines = []
    for seg in transcript_segments:
        sp = seg.get("speaker", "Unknown")
        ts = seg.get("start", "")
        transcript_lines.append(f"[{ts}] {sp}: {seg.get('text', '')}")
    transcript_text = "\n".join(transcript_lines)
    fields_json = json.dumps(extracted_fields, ensure_ascii=False, indent=2)

    prompt = f"""
You are analyzing a B2B meeting. Distinct speaker labels: {json.dumps(speakers)}

Structured extraction:
{fields_json}

Transcript:
{transcript_text}

Return ONLY valid JSON:
{{
  "summary": "Max 3 short sentences.",
  "speaker_map": {{ "<each label>": "<role like Client / Vendor / Technical>" }}
}}
Every label in the distinct list must be a key in speaker_map.
"""

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You output only compact JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    raw = (response.choices[0].message.content or "").strip()
    raw = _strip_json_fence(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        head = raw[:800].replace("\n", " ")
        raise ValueError(f"speaker_map JSON parse failed: {e}; head={head!r}") from e
    summary = str(data.get("summary") or "").strip()
    sm = data.get("speaker_map")
    speaker_map = {str(k): str(v) for k, v in sm.items()} if isinstance(sm, dict) else {}
    return summary, speaker_map


def meeting_intel_without_diarization(
    transcript_segments: List[Dict],
    extracted_fields: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Executive summary only — no role-mapped transcript artifact.

    Used when there is no usable diarization (single ``Unknown`` speaker, empty
    diarization segments, non-diarized Whisper).
    """
    if not OPENAI_API_KEY:
        return {
            "summary": "",
            "speaker_map": {},
            "transcript_with_roles": [dict(s) for s in transcript_segments],
            "speaker_intel_note": "OPENAI_API_KEY not set; skipped meeting intel.",
            "role_method": "skipped_no_diarization",
        }

    try:
        summary = _llm_summary_only(transcript_segments, extracted_fields)
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        summary = ""

    out_segments: List[Dict] = []
    for seg in transcript_segments:
        row = dict(seg)
        row.pop("role", None)
        out_segments.append(row)

    return {
        "summary": summary,
        "speaker_map": {},
        "transcript_with_roles": out_segments,
        "role_method": "skipped_no_diarization",
        "speaker_intel_note": (
            "Role mapping skipped: no diarization. See polished / call quality report "
            "for narrative and checklist coverage."
        ),
    }


def enrich_meeting_intel(
    transcript_segments: List[Dict],
    extracted_fields: Dict[str, Any],
) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        return {
            "summary": "",
            "speaker_map": {},
            "transcript_with_roles": apply_roles_to_transcript(transcript_segments, {}),
            "speaker_intel_note": "OPENAI_API_KEY not set; skipped meeting intel.",
            "role_method": "none",
        }

    speakers = _distinct_speakers(transcript_segments)
    single_unknown = len(speakers) == 1 and speakers[0] == "Unknown"

    try:
        if single_unknown and transcript_segments:
            # ------------------------------------------------------------------
            # ON HOLD: burst-based LLM roles (re-enable when diarization / video
            # supports reliable speaker separation — avoids bogus per-line labels.)
            #
            # bursts = _auto_bursts(transcript_segments)
            # summary, speaker_map, burst_roles = _llm_burst_roles(bursts, extracted_fields)
            # out_segments: List[Dict] = []
            # for i, seg in enumerate(transcript_segments):
            #     out_segments.append(dict(seg))
            # for b in bursts:
            #     role = burst_roles[b["id"]] if b["id"] < len(burst_roles) else "Participant"
            #     for idx in b["indices"]:
            #         if 0 <= idx < len(out_segments):
            #             out_segments[idx]["role"] = role
            # return {
            #     "summary": summary,
            #     "speaker_map": speaker_map,
            #     "transcript_with_roles": out_segments,
            #     "role_method": "burst_llm",
            #     "burst_count": len(bursts),
            # }
            # ------------------------------------------------------------------
            try:
                summary = _llm_summary_only(transcript_segments, extracted_fields)
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                summary = ""
            out_segments: List[Dict] = []
            for seg in transcript_segments:
                row = dict(seg)
                row.pop("role", None)
                out_segments.append(row)
            return {
                "summary": summary,
                "speaker_map": {
                    "Unknown": "Unlabeled (per-speaker roles pending diarization / better source media)"
                },
                "transcript_with_roles": out_segments,
                "role_method": "summary_only_no_roles",
                "speaker_intel_note": (
                    "Burst LLM role mapping is disabled. Use ``call_quality_report`` / "
                    "``polished_transcript`` for descriptive meeting narrative."
                ),
            }

        summary, speaker_map = _llm_speaker_map_only(transcript_segments, extracted_fields, speakers)
        twr = apply_roles_to_transcript(transcript_segments, speaker_map)
        return {
            "summary": summary,
            "speaker_map": speaker_map,
            "transcript_with_roles": twr,
            "role_method": "speaker_label_llm",
        }
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        return {
            "summary": "",
            "speaker_map": {},
            "transcript_with_roles": apply_roles_to_transcript(transcript_segments, {}),
            "raw_meeting_intel_output": str(e),
            "role_method": "error",
        }


def apply_roles_to_transcript(
    segments: List[Dict],
    speaker_map: Dict[str, str],
) -> List[Dict]:
    """Attach human-readable ``role`` on each segment from ``speaker_map``."""
    out: List[Dict] = []
    for seg in segments:
        sp = str(seg.get("speaker") or "Unknown")
        role = speaker_map.get(sp) or speaker_map.get("Unknown") or "Participant"
        row = {**seg, "role": role}
        out.append(row)
    return out
