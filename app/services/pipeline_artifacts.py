"""
Per-job paths under ``data/`` — one artifact per processing stage for audit,
resume, and partial reprocessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from app.config import DATA_DIR


@dataclass(frozen=True)
class JobArtifactPaths:
    """Stable filenames for ``job_stem`` (e.g. ``client_call_01``)."""

    stem: str

    @property
    def data_root(self) -> Path:
        return DATA_DIR

    @property
    def wav(self) -> Path:
        return self.data_root / "audio" / f"{self.stem}.wav"

    @property
    def raw_transcript(self) -> Path:
        return self.data_root / "transcripts" / "raw" / f"{self.stem}_raw_transcript.json"

    @property
    def diarization(self) -> Path:
        return self.data_root / "diarization" / f"{self.stem}_diarization.json"

    @property
    def merged_transcript(self) -> Path:
        return self.data_root / "transcripts" / "merged" / f"{self.stem}_speaker_transcript.json"

    @property
    def role_mapped_transcript(self) -> Path:
        return self.data_root / "transcripts" / "role_mapped" / f"{self.stem}_role_mapped.json"

    @property
    def extracted_fields(self) -> Path:
        return self.data_root / "extracted" / f"{self.stem}_extracted_fields.json"

    @property
    def question_assessment(self) -> Path:
        return self.data_root / "extracted" / f"{self.stem}_question_assessment.json"

    @property
    def risk_report(self) -> Path:
        return self.data_root / "reports" / f"{self.stem}_risk_report.json"

    @property
    def call_quality_report(self) -> Path:
        return self.data_root / "reports" / f"{self.stem}_call_quality_report.json"

    @property
    def polished_json(self) -> Path:
        return self.data_root / "polished" / f"{self.stem}_polished.json"

    @property
    def polished_md(self) -> Path:
        return self.data_root / "polished" / f"{self.stem}_polished.md"

    @property
    def final_report(self) -> Path:
        return self.data_root / "reports" / "final" / f"{self.stem}_final_report.json"

    @property
    def metadata(self) -> Path:
        return self.data_root / "metadata" / f"{self.stem}_metadata.json"

    def rel(self, path: Path) -> str:
        """Path relative to ``data/`` for embedding in JSON."""
        try:
            return path.relative_to(self.data_root).as_posix()
        except ValueError:
            return path.as_posix()


def polished_to_markdown(
    stem: str,
    polished: Dict[str, Any],
    topic_wise: Any,
    *,
    executive_summary: str = "",
    call_quality_report: Dict[str, Any] | None = None,
    question_coverage: list[Any] | None = None,
    discovery_template: list[Dict[str, Any]] | None = None,
) -> str:
    """Single Markdown document: scores, checklist, conformance, then polished narrative."""
    cq = call_quality_report if isinstance(call_quality_report, dict) else {}
    conf = cq.get("conformance") if isinstance(cq.get("conformance"), dict) else {}
    parts: list[str] = [f"# Overall report — `{stem}`\n"]

    es = str(executive_summary or "").strip()
    if es:
        parts.append("## Executive summary\n\n" + es + "\n")

    score = cq.get("conformance_score_0_100")
    wscore = conf.get("score_0_100")
    parts.append("## Conformance & checklist scores\n\n")
    if isinstance(score, (int, float)):
        parts.append(f"- **Checklist score (0–100):** {int(score)}\n")
    if isinstance(wscore, (int, float)):
        parts.append(f"- **Weighted coverage (0–100):** {int(wscore)}\n")
    for label, key in (
        ("Fully answered", "questions_answered_fully"),
        ("Partial", "questions_partial"),
        ("Not answered", "questions_not_answered"),
        ("Unclear / conflicting", "questions_unclear"),
        ("Checklist size", "questions_total"),
    ):
        v = cq.get(key)
        if isinstance(v, (int, float)):
            parts.append(f"- **{label}:** {int(v)}\n")
    rec = str(cq.get("recommendation") or "").strip()
    if rec:
        parts.append(f"- **Recommendation:** {rec}\n")
    parts.append("\n")

    narr = str(conf.get("narrative") or "").strip()
    gaps = str(conf.get("critical_gaps_summary") or "").strip()
    if narr or gaps:
        parts.append("## Conformance narrative\n\n")
        if narr:
            parts.append(narr + "\n\n")
        if gaps:
            parts.append("**Critical gaps**\n\n" + gaps + "\n\n")

    cov = question_coverage if isinstance(question_coverage, list) else []
    tmpl = discovery_template if isinstance(discovery_template, list) else []
    titles: Dict[str, str] = {}
    prompts: Dict[str, str] = {}
    for row in tmpl:
        if not isinstance(row, dict):
            continue
        qid = str(row.get("id") or "").strip()
        if qid:
            titles[qid] = str(row.get("title") or qid).strip()
            if row.get("eval_prompt"):
                prompts[qid] = str(row.get("eval_prompt")).strip()

    if cov:
        parts.append("## Discovery template — question coverage\n\n")
        parts.append(
            "| Question | Status | Confidence | Notes | Evidence |\n"
            "| --- | --- | --- | --- | --- |\n"
        )
        for row in cov:
            if not isinstance(row, dict):
                continue
            qid = str(row.get("question_id") or row.get("id") or "").strip()
            title = str(row.get("title") or titles.get(qid, qid)).strip()
            st = str(row.get("status") or "").strip()
            cf = str(row.get("confidence") or "").strip()
            notes = str(row.get("notes") or "").strip().replace("\n", " ")
            ev = str(row.get("evidence") or "").strip().replace("\n", " ")
            label = title or qid or "—"
            parts.append(f"| {label} | {st} | {cf} | {notes} | {ev} |\n")
        parts.append("\n")
        for row in cov:
            if not isinstance(row, dict):
                continue
            qid = str(row.get("question_id") or row.get("id") or "").strip()
            prompt = prompts.get(qid) or str(row.get("eval_prompt") or "").strip()
            if not prompt:
                continue
            t = str(row.get("title") or titles.get(qid, qid)).strip()
            parts.append(f"### {t or qid} — evaluation prompt\n\n{prompt}\n\n")

    cf_block = cq.get("call_assessment")
    if isinstance(cf_block, dict) and any(str(cf_block.get(k) or "").strip() for k in cf_block):
        parts.append("## Call quality assessment\n\n")
        for label, k in (
            ("Objective", "objective_met"),
            ("Pain points", "pain_points_identified"),
            ("Solution fit", "solution_fit_discussed"),
            ("Budget & ETA capture", "budget_and_eta_captured"),
            ("Open risks", "open_risks"),
            ("Overall judgment", "overall_judgment"),
        ):
            v = str(cf_block.get(k) or "").strip()
            if v:
                parts.append(f"**{label}**\n\n{v}\n\n")
    ins = cq.get("insights")
    if isinstance(ins, list) and ins:
        parts.append("## Insights\n\n")
        for x in ins:
            parts.append(f"- {x}\n")
        parts.append("\n")
    na = cq.get("next_actions")
    if isinstance(na, list) and na:
        parts.append("## Next actions\n\n")
        for x in na:
            parts.append(f"- {x}\n")
        parts.append("\n")
    concl = str(cq.get("conclusion") or cq.get("conclusions") or "").strip()
    if concl:
        parts.append("## Conclusion\n\n" + concl + "\n\n")

    parts.append("---\n\n## Polished meeting narrative\n\n")
    order = [
        ("Meeting overview", "meeting_overview"),
        ("What was discussed", "main_discussion"),
        ("Technical details", "technical_details"),
        ("Non-technical / process", "non_technical_details"),
        ("Numbers, dates, ETA, budget", "quantitative_insights"),
        ("Client problem / context", "client_problem"),
        ("Solution discussion", "solution_discussion"),
        ("Timeline", "timeline"),
        ("Budget", "budget"),
        ("Risks", "risks"),
        ("Next steps", "next_steps"),
    ]
    for heading, key in order:
        body = str(polished.get(key) or "").strip()
        if body:
            parts.append(f"### {heading}\n\n{body}\n\n")
    if isinstance(topic_wise, list) and topic_wise:
        parts.append("### Topics\n\n")
        for row in topic_wise:
            if not isinstance(row, dict):
                continue
            t = str(row.get("topic") or "").strip()
            s = str(row.get("summary") or "").strip()
            if t or s:
                parts.append(f"#### {t or 'Topic'}\n\n{s}\n\n")
    return "".join(parts).strip() + "\n"
