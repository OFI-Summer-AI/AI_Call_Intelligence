"""
Streamlit dashboard for meeting JSON produced by the pipeline.

Run from project root:
  streamlit run streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app.config import OUTPUT_DIR, REPORTS_FINAL_DIR
from app.services.storage_service import StorageService


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


def _segment_density(transcript: list, bin_sec: int = 120) -> pd.DataFrame:
    if not transcript:
        return pd.DataFrame(columns=["Minutes", "Segments"])
    max_end = max(_parse_ts(s.get("end", "0")) for s in transcript)
    n_bins = max(1, int(max_end // bin_sec) + 1)
    counts = [0] * n_bins
    for s in transcript:
        start = _parse_ts(s.get("start", "0"))
        end = _parse_ts(s.get("end", str(start)))
        mid = (start + end) / 2.0
        b = min(int(mid // bin_sec), n_bins - 1)
        counts[b] += 1
    minutes = [(i * bin_sec) / 60.0 for i in range(n_bins)]
    return pd.DataFrame({"Minutes": minutes, "Segments": counts})


def _role_counts(transcript: list) -> pd.Series:
    roles = []
    for s in transcript:
        r = s.get("role") or s.get("speaker") or "Unknown"
        roles.append(str(r))
    return pd.Series(roles).value_counts()


def _barh_presence(ax, labels: list[str], title: str) -> None:
    if not labels:
        ax.set_axis_off()
        ax.text(0.5, 0.5, "—", ha="center", va="center", fontsize=14, color="#888")
        ax.set_title(title, fontsize=11)
        return
    y = range(len(labels))
    ax.barh(list(y), [1.0] * len(labels), color="#4C78A8", height=0.62)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xticks([])
    ax.invert_yaxis()
    ax.set_title(title, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)


def _barh_counts(ax, series: pd.Series, title: str) -> None:
    if series.empty:
        ax.set_axis_off()
        ax.text(0.5, 0.5, "—", ha="center", va="center", fontsize=14, color="#888")
        ax.set_title(title, fontsize=11)
        return
    top = series.head(12)
    y = range(len(top))
    ax.barh(list(y), list(top.values), color="#72B7B2", height=0.62)
    ax.set_yticks(list(y))
    ax.set_yticklabels(list(top.index), fontsize=9)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=11)
    ax.grid(axis="x", alpha=0.25)


@st.cache_data
def load_meeting_json(path_str: str) -> dict:
    return StorageService().load_json(path_str)


def main() -> None:
    st.set_page_config(page_title="Sales Call Intelligence", layout="wide")
    st.markdown("### Sales Call Intelligence")

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
    result_files = primary if primary else legacy
    labels = [p.name for p in result_files]
    if not labels:
        st.warning(
            f"No `*_final_report.json` in `{REPORTS_FINAL_DIR}` and no legacy bundle in "
            f"`{OUTPUT_DIR}`. Run `python -m app.main` first (final report is under "
            f"`data/reports/final/`; `data/outputs/` keeps `*_transcript.json` only)."
        )
        return

    choice = st.selectbox("Meeting file", options=labels)
    path_by_name = {p.name: p for p in result_files}
    path = path_by_name[choice]

    data = load_meeting_json(str(path))

    transcript = data.get("transcript") or []
    ef = data.get("extracted_fields") or {}
    rr = data.get("risk_report") or {}
    role_method = data.get("role_method") or ""
    burst_count = data.get("burst_count")

    segs = len(transcript)
    if transcript:
        dur_s = max(_parse_ts(s.get("end", "00:00:00")) for s in transcript)
        duration = _fmt_hms(dur_s)
    else:
        duration = "—"
    raw_labels = {str(s.get("speaker") or "") for s in transcript if s.get("speaker")}
    sp_count = len(raw_labels) if raw_labels else 0
    needs = bool(rr.get("needs_review"))

    m = st.columns(5)
    m[0].metric("Segments", f"{segs:,}")
    m[1].metric("Duration", duration)
    m[2].metric("STT speaker labels", sp_count)
    m[3].metric(
        "Burst groups (LLM)",
        str(int(burst_count)) if burst_count is not None else "—",
    )
    m[4].metric("Governance", "Review" if needs else "OK")

    hint = []
    if role_method:
        hint.append(f"intel={role_method}")
    if burst_count is not None:
        hint.append("roles mapped per burst when diarization is missing")
    if hint:
        st.caption(" · ".join(hint))

    cq = data.get("call_quality_report") or {}
    r2 = st.columns(4)
    sc = cq.get("conformance_score_0_100")
    r2[0].metric(
        "Checklist score (0–100)",
        f"{int(sc)}" if isinstance(sc, (int, float)) else "—",
    )
    qa = cq.get("questions_answered_fully")
    qp = cq.get("questions_partial")
    qt = cq.get("questions_total")
    r2[1].metric(
        "Fully answered",
        f"{int(qa)}" if isinstance(qa, (int, float)) else "—",
    )
    r2[2].metric(
        "Partial",
        f"{int(qp)}" if isinstance(qp, (int, float)) else "—",
    )
    r2[3].metric(
        "Checklist size",
        f"{int(qt)}" if isinstance(qt, (int, float)) else "—",
    )
    qn = cq.get("questions_not_answered")
    qu = cq.get("questions_unclear")
    r2b = st.columns(3)
    r2b[0].metric(
        "Not answered",
        f"{int(qn)}" if isinstance(qn, (int, float)) else "—",
    )
    r2b[1].metric(
        "Unclear / conflicting",
        f"{int(qu)}" if isinstance(qu, (int, float)) else "—",
    )
    rec = cq.get("recommendation") or "—"
    r2b[2].metric("Recommendation", str(rec))

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
        # Back-compat older result files
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
            st.caption("No topic blocks (re-run pipeline with latest code).")

    conf = cq.get("conformance") or {}
    with st.expander("Conformance (score + narrative)", expanded=False):
        if isinstance(conf, dict) and conf:
            st.metric("Weighted score", f"{conf.get('score_0_100', '—')}")
            st.write(conf.get("narrative") or "—")
            st.markdown("**Critical gaps**")
            st.write(conf.get("critical_gaps_summary") or "—")
        else:
            st.caption("No conformance object (legacy file).")
            st.write(cq.get("conformance_summary") or "—")

    with st.expander("Discovery checklist & coverage", expanded=False):
        cov = data.get("question_coverage") or []
        if cov:
            cdf = pd.DataFrame(cov)
            st.dataframe(cdf, use_container_width=True, hide_index=True)
        else:
            st.caption("No checklist rows (re-run pipeline to generate).")

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
                st.markdown(f"**{row.get('role', 'Participant')}** · `{row.get('performance_signal', '—')}`")
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
            st.caption(
                "Per-speaker / individual scoring is off until reliable diarization; "
                "see polished narrative and call assessment above."
            )

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

    with st.expander("Raw transcript (STT audit; timestamps + diagnostics)", expanded=False):
        raw = data.get("raw_transcript")
        if not raw:
            raw = [
                {k: v for k, v in s.items() if k != "role"}
                for s in (data.get("transcript") or [])
            ]
        ref = data.get("raw_evidence_file")
        st.caption(
            f"{len(raw)} segments · audit copy. "
            + (f"Also saved as `{ref}`." if ref else "")
        )
        if raw:
            st.dataframe(pd.DataFrame(raw).head(200), use_container_width=True, hide_index=True)
            if len(raw) > 200:
                st.caption("Showing first 200 rows; full list is in Raw JSON.")

    left, right = st.columns((1.05, 1.0), gap="large")

    with left:
        st.caption("Segments per ~2 minutes (when people talked)")
        dens = _segment_density(transcript, bin_sec=120)
        st.line_chart(dens.set_index("Minutes"))

        rc = _role_counts(transcript)
        fig_r, ax_r = plt.subplots(figsize=(7, 4.3))
        if rc.empty:
            ax_r.set_axis_off()
            ax_r.text(0.5, 0.5, "No transcript", ha="center", va="center")
        elif len(rc) <= 8:
            colors = plt.cm.Set3.colors
            ax_r.pie(
                rc.values,
                labels=rc.index,
                autopct=lambda p: f"{p:.0f}%" if p >= 8 else "",
                colors=[colors[i % len(colors)] for i in range(len(rc))],
                startangle=90,
                textprops={"fontsize": 8},
            )
            ax_r.set_title("Who spoke (by segment role)", fontsize=11)
        else:
            _barh_counts(ax_r, rc, "Who spoke (top roles, segment counts)")
        fig_r.tight_layout()
        st.pyplot(fig_r, clear_figure=True)
        plt.close(fig_r)

    with right:
        sm = data.get("speaker_map") or {}
        if sm:
            st.caption("Speaker label → role (LLM)")
            sm_df = pd.DataFrame([{"Label": k, "Role": v} for k, v in sm.items()])
            st.dataframe(
                sm_df,
                use_container_width=True,
                hide_index=True,
                height=min(200, 40 + 28 * len(sm_df)),
            )

        tech = list(ef.get("techstack_platform") or [])
        steps = list(ef.get("next_steps") or [])
        ex_risks = list(ef.get("risks") or [])
        gov = list(rr.get("risks") or [])
        reqs = list(ef.get("strict_requirements") or [])

        h_tech = max(2.0, 0.42 * max(len(tech), 1))
        fig_t, ax_t = plt.subplots(figsize=(8, h_tech))
        _barh_presence(ax_t, tech, "Platforms / systems")
        fig_t.tight_layout()
        st.pyplot(fig_t, clear_figure=True)
        plt.close(fig_t)

        h_steps = max(2.0, 0.42 * max(len(steps), 1))
        fig_s, ax_s = plt.subplots(figsize=(8, h_steps))
        _barh_presence(ax_s, steps, "Next steps")
        fig_s.tight_layout()
        st.pyplot(fig_s, clear_figure=True)
        plt.close(fig_s)

        r1, r2 = st.columns(2)
        with r1:
            h_er = max(1.8, 0.38 * max(len(ex_risks), 1))
            fig_e, ax_e = plt.subplots(figsize=(4.2, h_er))
            _barh_presence(ax_e, ex_risks, "Extraction risks")
            fig_e.tight_layout()
            st.pyplot(fig_e, clear_figure=True)
            plt.close(fig_e)
        with r2:
            h_g = max(1.8, 0.38 * max(len(gov), 1))
            fig_g, ax_g = plt.subplots(figsize=(4.2, h_g))
            _barh_presence(ax_g, gov, "Governance flags")
            fig_g.tight_layout()
            st.pyplot(fig_g, clear_figure=True)
            plt.close(fig_g)

        if reqs:
            h_r = max(1.6, 0.36 * len(reqs))
            fig_q, ax_q = plt.subplots(figsize=(8, h_r))
            _barh_presence(ax_q, reqs, "Strict requirements")
            fig_q.tight_layout()
            st.pyplot(fig_q, clear_figure=True)
            plt.close(fig_q)

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

    with st.expander("Transcript (paginated)", expanded=False):
        q = st.text_input("Filter", "")
        filt = [
            s
            for s in transcript
            if not q or q.lower() in str(s.get("text", "")).lower()
        ]
        page_size = 25
        pages = max(1, (len(filt) + page_size - 1) // page_size)
        page = st.slider("Page", 1, pages, 1)
        start = (page - 1) * page_size
        chunk = filt[start : start + page_size]
        for seg in chunk:
            role = seg.get("role") or seg.get("speaker", "")
            st.markdown(
                f"`{seg.get('start', '')}–{seg.get('end', '')}` · **{role}**"
            )
            st.caption(seg.get("text", ""))
        st.caption(f"{len(chunk)} lines · page {page}/{pages} · {len(filt)} matches")

    with st.expander("Raw JSON"):
        st.json(data)


main()
