"""
Meeting insight — AI-powered meeting review document (text-first, appendix last).
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from app.services.call_assessment_report_service import weighted_conformance_percent
from app.frontend.chart_helpers import distinct_speakers
from app.frontend.meeting_registry import get_entry, meeting_id_from_report_filename
from app.frontend.report_artifacts import job_paths_for_report, merged_risk_view
from app.frontend.report_pdf_intel import (
    cq_conclusion_text,
    cq_insights_list,
    filtered_insights,
    merge_next_steps,
    missing_discussion_areas,
)


def _title_from_report(report_filename: str, meta: dict[str, Any]) -> str:
    if meta.get("display_title"):
        return str(meta["display_title"])
    stem = Path(report_filename).stem
    for suf in ("_final_report", "_result"):
        if stem.endswith(suf):
            stem = stem[: -len(suf)]
            break
    return stem.replace("_", " ").strip() or stem


def _conformance_score_display(cq: dict) -> str:
    sc = cq.get("conformance_score_0_100")
    if isinstance(sc, (int, float)):
        return f"{int(round(float(sc)))}"
    conf = cq.get("conformance") or {}
    if isinstance(conf, dict):
        sc2 = conf.get("score_0_100")
        if isinstance(sc2, (int, float)):
            return f"{int(round(float(sc2)))}"
    return "—"


def _h(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _kpi_card_html(label: str, value: str, hint: str, grad: str) -> str:
    """One equal-footprint tile: title, value, short meaning (HTML-escaped)."""
    return (
        f'<div style="background:{grad};border:1px solid #e5e7eb;border-radius:12px;'
        f'padding:12px 14px;box-shadow:0 1px 2px rgba(15,23,42,0.04);'
        f'min-height:124px;display:flex;flex-direction:column;justify-content:flex-start;">'
        f'<div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">{_h(label)}</div>'
        f'<div style="font-size:1.1rem;font-weight:700;color:#1e1b4b;margin-top:6px;line-height:1.2;word-break:break-word;">{_h(value)}</div>'
        f'<div style="font-size:0.7rem;color:#64748b;line-height:1.35;margin-top:auto;padding-top:8px;">{_h(hint)}</div>'
        "</div>"
    )


def _unified_kpi_grid_html(
    *,
    client: str,
    session: str,
    duration: str,
    parties: str,
    score_line: str,
    n_insights: int,
    n_next_actions: int,
    participant_tile: str,
    n_discovery_gaps: int,
    n_risks: int,
    n_themes: int,
) -> str:
    """All at-a-glance KPIs in one grid — equal minimum tile size, reading order top-to-bottom / left-to-right."""
    grads = [
        "linear-gradient(135deg,#eef2ff 0%,#ffffff 100%)",
        "linear-gradient(135deg,#ecfdf5 0%,#ffffff 100%)",
        "linear-gradient(135deg,#fff7ed 0%,#ffffff 100%)",
        "linear-gradient(135deg,#fce7f3 0%,#ffffff 100%)",
        "linear-gradient(135deg,#e0f2fe 0%,#ffffff 100%)",
        "linear-gradient(135deg,#f8fafc 0%,#ffffff 100%)",
        "linear-gradient(135deg,#f0fdf4 0%,#ffffff 100%)",
        "linear-gradient(135deg,#fffbeb 0%,#ffffff 100%)",
        "linear-gradient(135deg,#fdf4ff 0%,#ffffff 100%)",
        "linear-gradient(135deg,#eff6ff 0%,#ffffff 100%)",
        "linear-gradient(135deg,#fef2f2 0%,#ffffff 100%)",
    ]
    triples: list[tuple[str, str, str]] = [
        (
            "Client",
            client or "—",
            "Account or client name from your registry or extraction — who this artifact is for.",
        ),
        (
            "Session type",
            session,
            "How this recording entered the pipeline (for example upload vs connector).",
        ),
        (
            "Duration",
            duration,
            "Wall-clock length of the audio or transcript window analyzed.",
        ),
        (
            "Parties observed",
            parties,
            "Distinct speaker labels detected; a single bucket means diarization was not applied.",
        ),
        (
            "Discovery score",
            score_line,
            "Weighted coverage of your discovery checklist (0–100); aligns with stored conformance where present.",
        ),
        (
            "Insights on call",
            str(n_insights),
            "Number of structured insight lines attached to this meeting in the quality report.",
        ),
        (
            "Next actions",
            str(n_next_actions),
            "Merged count of model next_actions plus polished next steps, after removing duplicates.",
        ),
        (
            "Participant scorecards",
            participant_tile,
            "Per-person assessments when the pipeline has speaker-specific rows; otherwise a readiness note.",
        ),
        (
            "Open discovery gaps",
            str(n_discovery_gaps),
            "Checklist questions still open for follow-up (unanswered or partial, per pipeline rules).",
        ),
        (
            "Watch-out flags",
            str(n_risks),
            "Risk or review bullets merged from the call quality report and any linked risk file.",
        ),
        (
            "Theme groups",
            str(n_themes),
            "Count of AI topic-summary blocks produced for this meeting (agenda-style grouping).",
        ),
    ]
    cards = [_kpi_card_html(lab, val, hint, grads[i % len(grads)]) for i, (lab, val, hint) in enumerate(triples)]
    return (
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(172px,1fr));gap:10px;margin:0 0 1.1rem 0;">'
        + "".join(cards)
        + "</div>"
    )


def _friendly_recommendation(raw: str) -> str:
    s = str(raw or "").strip().lower()
    if not s or s == "—":
        return "No explicit recommendation in the report file."
    if s in ("proceed", "go", "yes"):
        return "Proceed — enough discovery signal to justify the next commercial or technical step."
    if "hold" in s or "pause" in s:
        return "Hold — gather more information before committing time or budget."
    if "risk" in s or "caution" in s:
        return "Proceed with caution — close identified gaps in a focused follow-up."
    return str(raw or "").strip().title()


def _party_count_label(data: dict[str, Any], participants: int) -> str:
    if data.get("has_diarization") and participants:
        return str(participants)
    if participants <= 1:
        return "Group session (speakers not split)"
    return str(participants)


def _friendly_checklist_status(status: str) -> str:
    s = str(status or "").lower().replace(" ", "_")
    mapping = {
        "answered": "Covered",
        "partially_answered": "Partial",
        "not_answered": "Missing",
        "unclear": "Unclear",
        "unclear_conflicting": "Unclear",
    }
    return mapping.get(s, str(status or "—").replace("_", " ").title())


def _discovery_unified_table(cov: list[Any]) -> pd.DataFrame | None:
    """One table: question, status, confidence, notes — no duplicate summary tables elsewhere."""
    if not isinstance(cov, list) or not cov:
        return None
    rows: list[dict[str, str]] = []
    for row in cov:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or row.get("id") or "Question").strip()
        st_raw = str(row.get("status") or "")
        st_label = _friendly_checklist_status(st_raw)
        conf = str(row.get("confidence") or "").strip().title() or "—"
        notes = str(row.get("notes") or "").strip() or "—"
        rows.append(
            {
                "Discovery question": title,
                "Status": st_label,
                "Confidence": conf,
                "What we captured": notes,
            }
        )
    return pd.DataFrame(rows) if rows else None


def _discovery_evidence_table(cov: list[Any]) -> pd.DataFrame | None:
    if not isinstance(cov, list) or not cov:
        return None
    rows = []
    for row in cov:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or row.get("id") or "Question").strip()
        ev = str(row.get("evidence") or "").strip()
        if ev and ev != "—":
            rows.append({"Discovery question": title, "Supporting detail": ev})
    return pd.DataFrame(rows) if rows else None


def _action_center_table(actions: list[str]) -> pd.DataFrame:
    rows = []
    for i, act in enumerate(actions[:14]):
        urg = "High" if i < 2 else "Medium"
        rows.append({"Action": act, "Owner": "TBD", "Priority": urg, "ETA": "TBD"})
    return pd.DataFrame(rows)


def _decisions_list(cq: dict) -> list[str]:
    raw = cq.get("recommendations")
    out: list[str] = []
    if isinstance(raw, list):
        for x in raw:
            s = str(x).strip()
            if not s:
                continue
            if s.lower() in ("proceed", "hold", "pause", "yes", "no"):
                continue
            out.append(s)
    return out[:8]


def _sentiment_summary(cf: dict, cq: dict) -> str:
    overall = str(cf.get("overall_judgment") or cq.get("assessment_of_call") or "").lower()
    if any(w in overall for w in ("productive", "positive", "strong", "clear", "good")):
        return "Overall tone reads constructive and forward-moving."
    if any(w in overall for w in ("uncertain", "caution", "risk", "gap", "missing", "absent")):
        return "Overall tone reads exploratory with open commercial or delivery questions."
    if overall:
        return "Mixed / neutral — validate with your own stakeholders."
    return "Not enough assessment text to label sentiment."


def render_meeting_insight_surface(
    *,
    data: dict[str, Any],
    report_filename: str,
    report_path: Path | None,
    duration: str,
    source_label: str,
    key_prefix: str,
) -> None:
    mid = meeting_id_from_report_filename(report_filename)
    paths = job_paths_for_report(report_filename)
    meta = get_entry(mid)
    ef = data.get("extracted_fields") or {}
    cq = data.get("call_quality_report") or {}
    transcript = data.get("transcript") or []
    risk_view = merged_risk_view(data, paths)
    pt = data.get("polished_transcript") or {}
    if not isinstance(pt, dict):
        pt = {}
    topics = data.get("topic_wise_summary") or []
    cov = data.get("question_coverage") or []

    title = _title_from_report(report_filename, meta)
    client = str(meta.get("client_name") or ef.get("client_name") or "—")
    when = "—"
    if report_path and report_path.exists():
        when = datetime.fromtimestamp(report_path.stat().st_mtime).strftime("%b %d, %Y · %H:%M")

    score_num = _conformance_score_display(cq)
    rec_raw = str(cq.get("recommendation") or "").strip()
    rec_friendly = _friendly_recommendation(rec_raw or "—")
    actions = cq.get("next_actions") or []
    if not isinstance(actions, list):
        actions = []
    actions = [str(a).strip() for a in actions if str(a).strip()]
    risks = list(risk_view.get("risks") or [])
    participants = distinct_speakers(transcript)
    party_label = _party_count_label(data, participants)
    conf_obj = cq.get("conformance") if isinstance(cq.get("conformance"), dict) else {}
    answered_n: int | None = None
    if isinstance(conf_obj.get("answered"), (int, float)):
        answered_n = int(conf_obj["answered"])
    if answered_n is None and isinstance(cov, list):
        answered_n = sum(
            1 for r in cov if isinstance(r, dict) and str(r.get("status", "")).lower() == "answered"
        )
    total_q = cq.get("questions_total")
    if not isinstance(total_q, (int, float)) and isinstance(cov, list):
        total_q = len(cov)

    summ = str(data.get("summary") or "").strip()
    overview = str(pt.get("meeting_overview") or "").strip()
    client_problem = str(pt.get("client_problem") or ef.get("client_problem") or "").strip()
    gaps_text = str(conf_obj.get("critical_gaps_summary") or "").strip()
    pending_areas = missing_discussion_areas(cov if isinstance(cov, list) else [])
    merged_steps = merge_next_steps(actions, pt)
    cf = cq.get("call_assessment") if isinstance(cq.get("call_assessment"), dict) else {}
    follow_recs = filtered_insights(cq)

    insights_list = cq_insights_list(cq)
    concl_text = cq_conclusion_text(cq)
    ind_raw = cq.get("individual_assessment") or []
    ind_list = [x for x in ind_raw if isinstance(x, dict)] if isinstance(ind_raw, list) else []
    ind_n = len(ind_list)
    participant_strip = str(ind_n) if ind_n else ("Needs speaker IDs" if not data.get("has_diarization") else "0")

    cov_rows = [c for c in cov if isinstance(c, dict)] if isinstance(cov, list) else []
    w_float = weighted_conformance_percent(cov_rows)

    st.markdown(f"# {title}")
    st.caption(f"AI-powered meeting review · {client} · {when}")

    score_line = (
        f"{w_float:.1f} / 100"
        if w_float is not None
        else (f"{score_num} / 100" if score_num != "—" else "—")
    )
    st.markdown(
        _unified_kpi_grid_html(
            client=client or "—",
            session=source_label,
            duration=duration,
            parties=party_label,
            score_line=score_line,
            n_insights=len(insights_list),
            n_next_actions=len(merged_steps),
            participant_tile=participant_strip,
            n_discovery_gaps=len(pending_areas),
            n_risks=len(risks),
            n_themes=len(topics) if isinstance(topics, list) else 0,
        ),
        unsafe_allow_html=True,
    )

    st.markdown("## Meeting charts")
    st.caption(
        "Each figure uses the same canvas size and scales to the page width. "
        "These charts summarize activity, balance of airtime, and tone from the transcript — "
        "use them alongside the discovery score and narrative in the executive summary."
    )
    from app.frontend.insight_charts import render_meeting_intelligence_charts

    render_meeting_intelligence_charts(data, key_prefix, outer_heading=False)

    st.markdown("## 1. Executive summary")
    st.caption("Quick read for leadership — was the conversation useful, complete, and commercially actionable?")

    st.markdown("**What this meeting was about**")
    st.write(overview or (summ[:520] + ("…" if len(summ) > 520 else "") if summ else "—"))

    st.markdown("**Main client concern**")
    st.write(client_problem or "—")

    st.markdown("**Major outcomes & agreements**")
    if merged_steps:
        for i, step in enumerate(merged_steps[:8], 1):
            st.markdown(f"{i}. {step}")
    elif summ:
        st.write(summ)
    else:
        st.caption("No consolidated outcomes yet.")

    st.markdown("**Overall recommendation**")
    rl = rec_raw.lower()
    if "hold" in rl or "pause" in rl or "stop" in rl:
        st.warning(rec_friendly)
    elif "caution" in rec_friendly.lower() or "caution" in rl:
        st.info(rec_friendly)
    else:
        st.success(rec_friendly)

    st.markdown("**Critical blockers**")
    blockers: list[str] = []
    if gaps_text:
        blockers.append(gaps_text)
    if risk_view.get("needs_review"):
        blockers.append("Flagged for human review before external sharing.")
    for p in pending_areas[:5]:
        blockers.append(f"Discovery gap: {p}")
    for r in risks[:6]:
        blockers.append(f"Review note: {r}")
    if blockers:
        for b in blockers:
            st.markdown(f"- {b}")
    else:
        st.caption("No critical blockers called out beyond normal follow-up.")

    st.markdown("### AI recommendation")
    st.write(rec_friendly)

    st.divider()

    # --- 2. Meeting conformance ---
    st.markdown("## 2. Meeting conformance analysis")
    st.caption("Whether the conversation covered the discovery template your team uses.")

    if w_float is not None and score_num != "—":
        st.markdown(
            f"**Weighted discovery coverage:** {w_float:.1f}% — stored on the report as **{score_num} / 100** "
            f"(standard rounding to a whole number)."
        )
    elif score_num != "—":
        st.markdown(f"**Discovery coverage score:** {score_num} / 100")
    else:
        st.caption("No conformance score on this file.")

    st.markdown("### Critical gaps")
    if gaps_text:
        st.warning(gaps_text)
    elif pending_areas:
        for p in pending_areas:
            st.markdown(f"- {p}")
    else:
        st.caption("No critical gaps summary for this meeting.")

    st.markdown("### AI narrative (discovery)")
    nar = str(conf_obj.get("narrative") or cq.get("conformance_summary") or "").strip()
    if nar:
        st.info(nar)
    else:
        st.caption("No conformance narrative on file.")

    uni = _discovery_unified_table(cov if isinstance(cov, list) else [])
    st.markdown("### Discovery checklist")
    if uni is not None and not uni.empty:
        n = len(uni)
        st.dataframe(
            uni,
            use_container_width=True,
            hide_index=True,
            height=min(480, 44 + 36 * n),
        )
        ev_df = _discovery_evidence_table(cov if isinstance(cov, list) else [])
        if ev_df is not None and not ev_df.empty:
            with st.expander("Supporting detail (per question)", expanded=False):
                st.dataframe(
                    ev_df,
                    use_container_width=True,
                    hide_index=True,
                    height=min(400, 44 + 34 * len(ev_df)),
                )
    else:
        st.caption("No discovery checklist rows in this export.")

    with st.expander("How the discovery score is calculated (SOP)", expanded=False):
        st.markdown(
            """
**Definition**

The score is a **weighted average** over every row in your discovery checklist (same count as template questions).

**Status weights** (each question earns one of these weights, then we average):

| Status | Weight |
| ------ | ------ |
| Covered (answered) | 1.00 |
| Partial | 0.55 |
| Unclear / conflicting | 0.35 |
| Missing (not answered) | 0.00 |

**Formula**

`score = round(100 × (sum of weights) ÷ (number of questions))`

The headline **X / 100** on the report is that rounded integer. The KPI row can show **one decimal** (e.g. 81.9%) from the same inputs before rounding — so **82** and **81.9%** describe the same run.

**Per-question confidence** (High / Medium / Low) is the model’s read of how solid the notes are; it **does not change** the numeric weight — only the **status** does.

**Example**

With 8 questions: 6 Covered, 1 Partial, 1 Missing →  
`(6×1 + 1×0.55 + 1×0) ÷ 8 = 0.81875` → **81.9%** before rounding → **82 / 100** after rounding.
            """.strip()
        )
        if isinstance(answered_n, (int, float)) and isinstance(total_q, (int, float)) and int(total_q) > 0:
            st.caption(
                f"This meeting’s checklist counts (from the report): "
                f"{int(answered_n)} fully covered, "
                f"{int(conf_obj.get('partially_answered') or cq.get('questions_partial') or 0)} partial, "
                f"{int(conf_obj.get('not_answered') or cq.get('questions_not_answered') or 0)} missing, "
                f"of {int(total_q)} questions."
            )

    st.divider()

    # --- 3. Call assessment ---
    st.markdown("## 3. Call assessment")
    st.caption("How strong the conversation was as a meeting — clarity, structure, and commercial signals.")

    st.markdown("### 3.1 Meeting quality")
    if cf:
        for label, key in (
            ("Objective achieved?", "objective_met"),
            ("Client pains surfaced?", "pain_points_identified"),
            ("Solution alignment discussed?", "solution_fit_discussed"),
            ("Budget & timing captured?", "budget_and_eta_captured"),
            ("Risks called out?", "open_risks"),
            ("Overall judgment", "overall_judgment"),
        ):
            v = str(cf.get(key) or "").strip()
            if v:
                st.markdown(f"**{label}**")
                st.write(v)
    else:
        st.write(str(cq.get("assessment_of_call") or cq.get("call_level_summary") or "—"))

    st.markdown("### 3.2 Conversation effectiveness")
    ce = str(cq.get("call_level_summary") or "").strip()
    org = str(cq.get("user_level_summary") or "").strip()
    if ce:
        st.markdown("**Call arc**")
        st.write(ce)
    if org:
        st.markdown("**Org / process read**")
        st.write(org)
    if not ce and not org:
        st.caption("No separate effectiveness summary — see meeting quality above.")

    st.markdown("### 3.3 Commercial readiness")
    st.markdown("**Assessment view (timeline & budget)**")
    st.write(str(cf.get("budget_and_eta_captured") or "—"))
    st.caption("For the underlying timeline and budget wording, see section 5 (business insights).")

    ins_block = cq.get("insights")
    st.markdown(f"### 3.4 Insights on this call ({len(insights_list)})")
    if insights_list:
        for x in insights_list:
            st.markdown(f"- {x}")
    elif isinstance(ins_block, str) and ins_block.strip():
        st.write(ins_block[:2000])
    else:
        st.caption("No insight lines on this report.")

    st.divider()

    # --- 4. Individual participants ---
    st.markdown(f"## 4. Individual participant assessment ({ind_n})")
    st.caption("When the system can distinguish speakers, a per-person summary appears here.")
    ind = cq.get("individual_assessment")
    has_parties = bool(data.get("has_diarization")) and isinstance(ind, list) and len(ind) > 0
    if has_parties:
        for row in ind:
            if not isinstance(row, dict):
                continue
            st.markdown(f"### {row.get('role', 'Participant')}")
            st.caption(str(row.get("performance_signal") or "—"))
            for k, lab in (
                ("right_questions", "Discovery questions"),
                ("conversation_control", "Conversation control"),
                ("missed_discovery", "Missed discovery"),
                ("risks_clarified", "Risks clarified"),
                ("next_steps_conversion", "Next steps"),
            ):
                v = str(row.get(k) or "").strip()
                if v:
                    st.markdown(f"**{lab}**")
                    st.write(v)
    else:
        st.caption(
            "Per-person scores are not available for this recording. The rest of this page still reflects the full conversation."
        )

    st.divider()

    # --- 5. Business insights ---
    st.markdown("## 5. Business insights & discovery findings")
    st.caption("Headline pain is in section 1; this section expands process, solution, systems, and risks.")
    st.markdown("### Current process & constraints")
    proc = str(pt.get("non_technical_details") or pt.get("current_process_and_constraints") or "").strip()
    st.write(proc or "—")
    st.markdown("### Solution expectations")
    st.write(str(pt.get("solution_discussion") or "—"))
    st.markdown("### Timeline & budget (from discussion)")
    st.markdown("**Timeline**")
    st.write(str(pt.get("timeline") or ef.get("timeline") or "—"))
    st.markdown("**Budget**")
    st.write(str(pt.get("budget") or ef.get("budget") or "—"))
    st.markdown("### Technical environment")
    st.write(str(pt.get("technical_details") or "—"))
    tech = list(ef.get("techstack_platform") or [])
    if tech:
        st.caption("Platforms / systems also tagged in extraction: " + ", ".join(str(t) for t in tech))
    st.markdown("### Risks & blockers")
    st.write(str(pt.get("risks") or "—"))
    if list(ef.get("risks") or []):
        for r in ef.get("risks") or []:
            st.markdown(f"- {r}")

    if isinstance(topics, list) and topics:
        st.markdown("### Theme map (AI grouping)")
        for row in topics[:8]:
            if not isinstance(row, dict):
                continue
            with st.container(border=True):
                st.markdown(f"**{str(row.get('topic', 'Topic'))[:56]}**")
                st.caption(str(row.get("summary", ""))[:480] + ("…" if len(str(row.get("summary", ""))) > 480 else ""))

    st.markdown("### Find a phrase in the conversation")
    st.caption("Jump to where something was said — results use the same transcript as the analysis.")
    ph = st.text_input(
        "Search the conversation",
        "",
        key=f"{key_prefix}_phrase_find",
        placeholder="Type a word or short phrase…",
    )
    if ph.strip():
        hits = [s for s in transcript if ph.lower() in str(s.get("text", "")).lower()]
        for seg in hits[:25]:
            role = seg.get("role") or seg.get("speaker", "Speaker")
            st.markdown(f"**{seg.get('start', '')}** · {role}")
            st.caption(str(seg.get("text", ""))[:400])
        if len(hits) > 25:
            st.caption(f"Showing 25 of {len(hits)} matches — narrow your phrase.")
        elif not hits:
            st.caption("No matches.")

    st.divider()

    # --- 6. Action center ---
    st.markdown("## 6. Action center")
    st.caption(
        f"{len(merged_steps)} next actions · {len(insights_list)} insights · "
        f"{ind_n} participant scorecards (when diarization provides rows)"
    )

    with st.container(border=True):
        st.markdown("### Written conclusion from analysis")
        if concl_text:
            st.write(concl_text)
        else:
            st.caption("No closing conclusion paragraph was written for this meeting.")

    st.markdown(f"### Agreed next actions ({len(merged_steps)})")
    if merged_steps:
        st.dataframe(_action_center_table(merged_steps), use_container_width=True, hide_index=True)
    else:
        st.caption("No actions captured.")

    decs = _decisions_list(cq)
    st.markdown("### Decisions & commitments")
    if decs:
        for d in decs:
            st.markdown(f"- {d}")
    else:
        st.caption("No separate decision lines beyond the recommendation.")

    st.markdown("### Pending discussions")
    pend = list(pending_areas)
    if pend:
        for p in pend[:10]:
            st.markdown(f"- {p}")
    else:
        st.caption("No open discovery areas flagged.")

    st.markdown("### Follow-up recommendations")
    if follow_recs:
        for x in follow_recs:
            st.markdown(f"- {x}")
    else:
        st.caption("No additional AI follow-up lines after filtering generic phrasing.")

    st.divider()

    # --- 7. Strategic read (sentiment only; avoids repeating section 2 / 3 bullets) ---
    st.markdown("## 7. Strategic read")
    st.caption("How the meeting reads overall, without repeating the discovery checklist.")
    st.markdown("### Meeting sentiment")
    st.write(_sentiment_summary(cf, cq))

    st.divider()

    # --- 8. Conclusion ---
    st.markdown("## 8. Conclusion")
    st.markdown("### Overall meeting outcome")
    st.write(str(cf.get("overall_judgment") or cq.get("assessment_of_call") or "—"))
    st.markdown("### Readiness for the next phase")
    ready = (
        "You can move forward with the next agreed actions while closing the gaps noted above."
        if "proceed" in rec_raw.lower()
        else "Align internally on the gaps above before the next client conversation."
    )
    st.write(ready)
    st.markdown("### Final recommendation")
    st.markdown(f"> {rec_friendly}")

    st.divider()

    # --- PDF + appendix ---
    st.markdown("## Shareable PDF")
    from app.frontend.report_pdf import build_meeting_pdf_bytes

    pdf_b: bytes | None = None
    pdf_err: str | None = None
    try:
        pdf_b = build_meeting_pdf_bytes(data, report_filename)
    except Exception as exc:  # noqa: BLE001
        pdf_err = str(exc)

    stem = Path(report_filename).stem
    if pdf_b is not None:
        st.download_button(
            "Download meeting review (PDF)",
            data=pdf_b,
            file_name=stem.replace("_final_report", "").replace("_result", "") + "_meeting_report.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            key=f"{key_prefix}_pdf",
        )
        st.caption(
            "Includes the same storyline, visuals, and long-form narrative as this page. "
            "Raw transcript lines are not attached to the PDF — export JSON from the product when you need the full recording text."
        )
    else:
        st.warning("The PDF could not be generated in this session.")
        if pdf_err:
            st.caption("You can try again in a moment, or contact your administrator if it keeps happening.")
