"""
Meeting dashboard: load report JSON, render insight surface and analyst expanders.
"""

from __future__ import annotations

from pathlib import Path

from app.frontend.bootstrap import ensure_project_root

ensure_project_root()

import pandas as pd
import streamlit as st

from app.config import OUTPUT_DIR, REPORTS_FINAL_DIR
from app.services.storage_service import StorageService
from app.frontend.meeting_registry import get_entry, meeting_id_from_report_filename
from app.frontend.report_pdf import build_meeting_pdf_bytes


def list_report_paths() -> list[Path]:
    primary = sorted(
        REPORTS_FINAL_DIR.glob("*_final_report.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    legacy = sorted(
        OUTPUT_DIR.glob("*_result.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return primary if primary else legacy


def resolve_report_path(name: str) -> Path | None:
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    safe = Path(name).name
    for p in list_report_paths():
        if p.name == safe:
            return p
    return None


def _parse_ts(ts: str) -> float:
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


def _fmt_hms(total_sec: float) -> str:
    total_sec = int(round(total_sec))
    mm, ss = divmod(total_sec, 60)
    hh, mm = divmod(mm, 60)
    return f"{hh:02d}:{mm:02d}:{ss:02d}"


@st.cache_data
def load_meeting_json(path_str: str) -> dict:
    return StorageService().load_json(path_str)


def _recording_duration_label(transcript: list) -> str:
    if not transcript:
        return "—"
    dur_s = max(_parse_ts(s.get("end", "00:00:00")) for s in transcript)
    return _fmt_hms(dur_s)


def _recording_conformance_pct(cq: dict) -> str:
    sc = cq.get("conformance_score_0_100")
    if isinstance(sc, (int, float)):
        return f"{int(round(float(sc)))}%"
    conf = cq.get("conformance") or {}
    if isinstance(conf, dict):
        sc2 = conf.get("score_0_100")
        if isinstance(sc2, (int, float)):
            return f"{int(round(float(sc2)))}%"
    return "—"


def _recording_assessment_of_call_text(cq: dict) -> str:
    cf = cq.get("call_assessment")
    if isinstance(cf, dict) and cf:
        parts = []
        for label, k in (
            ("Objective", "objective_met"),
            ("Pain points", "pain_points_identified"),
            ("Solution fit", "solution_fit_discussed"),
            ("Budget & ETA capture", "budget_and_eta_captured"),
            ("Open risks", "open_risks"),
            ("Overall judgment", "overall_judgment"),
        ):
            v = str(cf.get(k) or "").strip()
            if v:
                parts.append(f"{label}: {v}")
        if parts:
            return "\n\n".join(parts)
    return str(cq.get("assessment_of_call") or "").strip()


def _recording_individual_text(cq: dict) -> str:
    ind = cq.get("individual_assessment")
    if isinstance(ind, list) and ind:
        lines: list[str] = []
        for row in ind:
            if not isinstance(row, dict):
                continue
            role = str(row.get("role", "Participant"))
            sig = str(row.get("performance_signal", "") or "").strip()
            head = f"{role} ({sig})" if sig else role
            lines.append(f"— {head}")
            for k, lab in (
                ("right_questions", "Discovery questions"),
                ("conversation_control", "Conversation control"),
                ("missed_discovery", "Missed discovery"),
                ("risks_clarified", "Risks clarified"),
                ("next_steps_conversion", "Next steps"),
            ):
                v = str(row.get(k) or "").strip()
                if v:
                    lines.append(f"  • {lab}: {v}")
        if lines:
            return "\n".join(lines)
    legacy = cq.get("assessment_of_individuals") or []
    if isinstance(legacy, list) and legacy:
        parts = []
        for row in legacy:
            if isinstance(row, dict):
                party = str(row.get("party", "Party"))
                overall = str(row.get("overall", "") or "").strip()
                parts.append(f"— {party} —\n{overall}" if overall else f"— {party} —")
        if parts:
            return "\n\n".join(parts)
    return ""


def _recording_insights_text(cq: dict) -> str:
    ins = cq.get("insights")
    if isinstance(ins, list) and ins:
        return "\n".join(f"• {x}" for x in ins)
    if isinstance(ins, str) and ins.strip():
        return ins.strip()
    return ""


def _recording_next_actions_text(cq: dict) -> str:
    na = cq.get("next_actions") or []
    if isinstance(na, list) and na:
        return "\n".join(f"• {x}" for x in na)
    return ""


def _recording_conclusion_text(cq: dict) -> str:
    c = cq.get("conclusion") or cq.get("conclusions") or ""
    return str(c).strip()


def render_recording_kpi_card(path: Path, index: int) -> None:
    from datetime import datetime

    data = load_meeting_json(str(path))
    cq = data.get("call_quality_report") or {}
    transcript = data.get("transcript") or []
    mid = meeting_id_from_report_filename(path.name)
    meta = get_entry(mid)
    title = str(meta.get("display_title") or mid.replace("_", " ").title())
    when = datetime.fromtimestamp(path.stat().st_mtime).strftime("%b %d, %Y")
    dur = _recording_duration_label(transcript)
    score = _recording_conformance_pct(cq)
    with st.container(border=True):
        row_a, row_b = st.columns([3.2, 1.1])
        with row_a:
            st.markdown(f"**{title}**")
            st.caption(f"{when} · {dur} · Quality {score}")
        with row_b:
            if st.button("Open insights", key=f"lib_open_{index}", type="primary", use_container_width=True):
                st.session_state["selected_report"] = path.name
                st.query_params["report"] = path.name
                st.switch_page("pages/05_Meeting_Dashboard.py")
            try:
                pdf_b = build_meeting_pdf_bytes(data, path.name)
                st.download_button(
                    "Download PDF",
                    data=pdf_b,
                    file_name=path.name.replace(".json", "_report.pdf"),
                    mime="application/pdf",
                    key=f"lib_pdf_{index}",
                    use_container_width=True,
                )
            except Exception:
                st.caption("PDF unavailable for this file.")


def _meeting_title_from_filename(report_filename: str) -> str:
    stem = Path(report_filename).stem
    for suffix in ("_final_report", "_result"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem.replace("_", " ").strip() or Path(report_filename).stem


def render_meeting_dashboard(
    data: dict, report_filename: str, report_path: Path | None = None
) -> None:
    transcript = data.get("transcript") or []
    ef = data.get("extracted_fields") or {}
    rr = data.get("risk_report") or {}

    if transcript:
        dur_s = max(_parse_ts(s.get("end", "00:00:00")) for s in transcript)
        duration = _fmt_hms(dur_s)
    else:
        duration = "—"
    cq = data.get("call_quality_report") or {}

    from app.frontend import insight_dashboard as _insight

    rp = report_path or resolve_report_path(report_filename)
    meta = get_entry(meeting_id_from_report_filename(report_filename))
    src = (
        "Live assistant session"
        if str(meta.get("source") or "").lower() == "live"
        else "Uploaded recording"
    )
    kpre = Path(report_filename).stem[:48]
    _insight.render_meeting_insight_surface(
        data=data,
        report_filename=report_filename,
        report_path=rp,
        duration=duration,
        source_label=src,
        key_prefix=kpre,
    )

    st.info(
        "Below: optional analyst detail (conformance tables, call-quality JSON fields). "
        "Clients usually stop at the sections above or the PDF."
    )

    with st.expander("Polished transcript (business headings, no timestamps)", expanded=False):
        pt = data.get("polished_transcript") or {}
        labels = {
            "meeting_overview": "Meeting overview",
            "main_discussion": "What was discussed",
            "technical_details": "Technical details",
            "non_technical_details": "Non-technical / process / org",
            "quantitative_insights": "Numbers, dates, ETA, budget signals",
            "client_problem": "Client problem / context",
            "solution_discussion": "Solution discussion",
            "timeline": "Timeline",
            "budget": "Budget",
            "risks": "Risks",
            "next_steps": "Next steps",
        }
        for key, title in labels.items():
            body = str(pt.get(key) or "").strip()
            if body:
                st.markdown(f"**{title}**")
                st.write(body)
        for key, title in (
            ("discussion_overview", "Meeting overview (legacy)"),
            ("main_topics", "Main topics (legacy)"),
            ("client_pain_points", "Client pain (legacy)"),
            ("current_process_and_constraints", "Process / constraints (legacy)"),
            ("proposed_direction_or_solution", "Proposed direction (legacy)"),
        ):
            if key not in labels and str(pt.get(key) or "").strip():
                st.markdown(f"**{title}**")
                st.write(pt.get(key))

    topics = data.get("topic_wise_summary") or []
    with st.expander("Topic-wise summary", expanded=False):
        if topics:
            st.dataframe(pd.DataFrame(topics), use_container_width=True, hide_index=True)
        else:
            st.caption("No topic summaries are available for this meeting yet.")

    with st.expander("Call quality report (assessments, insights, actions)", expanded=False):
        cf = cq.get("call_assessment")
        if isinstance(cf, dict) and cf:
            st.markdown("**Call assessment**")
            for label, k in (
                ("Objective", "objective_met"),
                ("Pain points", "pain_points_identified"),
                ("Solution fit", "solution_fit_discussed"),
                ("Budget & ETA capture", "budget_and_eta_captured"),
                ("Open risks", "open_risks"),
                ("Overall judgment", "overall_judgment"),
            ):
                v = str(cf.get(k) or "").strip()
                if v:
                    st.markdown(f"*{label}*")
                    st.write(v)
        else:
            st.markdown("**Assessment of the call**")
            st.write(cq.get("assessment_of_call") or "—")

        ind = cq.get("individual_assessment")
        if isinstance(ind, list) and ind:
            st.markdown("**Individual assessment (lightweight)**")
            for row in ind:
                if not isinstance(row, dict):
                    continue
                st.markdown(
                    f"**{row.get('role', 'Participant')}** · `{row.get('performance_signal', '—')}`"
                )
                for k, lab in (
                    ("right_questions", "Discovery questions"),
                    ("conversation_control", "Conversation control"),
                    ("missed_discovery", "Missed discovery"),
                    ("risks_clarified", "Risks clarified"),
                    ("next_steps_conversion", "Next steps"),
                ):
                    v = str(row.get(k) or "").strip()
                    if v:
                        st.caption(f"{lab}: {v}")
        else:
            st.caption("No per-person lines for this file — see the meeting review above.")

        st.markdown("**Insights**")
        ins = cq.get("insights")
        if isinstance(ins, list) and ins:
            for x in ins:
                st.markdown(f"- {x}")
        else:
            st.write(ins if isinstance(ins, str) else "—")

        st.markdown("**Next actions**")
        for x in cq.get("next_actions") or []:
            st.markdown(f"- {x}")

        st.markdown("**Conclusion**")
        st.write(cq.get("conclusion") or cq.get("conclusions") or "—")

        st.markdown("**Call-level summary**")
        st.write(cq.get("call_level_summary") or "—")
        st.markdown("**Org / process note (not per-speaker)**")
        st.write(cq.get("user_level_summary") or "—")

        st.markdown("**Participant summaries**")
        ps_rows = cq.get("participant_summaries") or []
        if ps_rows:
            for row in ps_rows:
                if isinstance(row, dict):
                    st.markdown(f"**{row.get('party', 'Party')}**")
                    st.write(row.get("summary") or "—")
        else:
            st.caption("No per-party summaries (disabled without diarization).")

        if cq.get("assessment_of_individuals") and not ind:
            st.markdown("**Assessment of individuals (legacy)**")
            for row in cq.get("assessment_of_individuals") or []:
                if isinstance(row, dict):
                    st.markdown(f"**{row.get('party', 'Party')}**")
                    st.write(row.get("overall") or "—")

        st.markdown("**Legacy recommendations list**")
        for x in cq.get("recommendations") or []:
            st.markdown(f"- {x}")

    with st.expander("Structured extraction (lists)", expanded=False):
        sm = data.get("speaker_map") or {}
        if sm:
            st.markdown("**Speaker label → role (LLM)**")
            sm_df = pd.DataFrame([{"Label": k, "Role": v} for k, v in sm.items()])
            st.dataframe(
                sm_df,
                use_container_width=True,
                hide_index=True,
                height=min(200, 40 + 28 * len(sm_df)),
            )
        else:
            st.caption("No speaker role map (usually empty until diarization labels exist).")

        tech = list(ef.get("techstack_platform") or [])
        steps = list(ef.get("next_steps") or [])
        ex_risks = list(ef.get("risks") or [])
        gov = list(rr.get("risks") or [])
        reqs = list(ef.get("strict_requirements") or [])

        st.markdown("**Platforms / systems**")
        if tech:
            for t in tech:
                st.markdown(f"- {t}")
        else:
            st.caption("—")

        st.markdown("**Extracted next steps**")
        if steps:
            for s in steps:
                st.markdown(f"- {s}")
        else:
            st.caption("—")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Extraction risks**")
            if ex_risks:
                for r in ex_risks:
                    st.markdown(f"- {r}")
            else:
                st.caption("—")
        with c2:
            st.markdown("**Governance flags**")
            if gov:
                for r in gov:
                    st.markdown(f"- {r}")
            else:
                st.caption("—")

        if reqs:
            st.markdown("**Strict requirements**")
            for r in reqs:
                st.markdown(f"- {r}")

    with st.expander("Executive summary & key facts (text)", expanded=False):
        st.markdown("**Summary**")
        st.write(data.get("summary") or "—")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Client**")
            st.write(ef.get("client_name") or "—")
            st.markdown("**Problem**")
            st.write(ef.get("client_problem") or "—")
        with c2:
            st.markdown("**Timeline**")
            st.write(ef.get("timeline") or "—")
            st.markdown("**Budget**")
            st.write(ef.get("budget") or "—")
