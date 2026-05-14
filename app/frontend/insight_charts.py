"""
AI-style intelligence visuals for the meeting insight page (matplotlib + Streamlit).

Charts that require real speaker labels are suppressed when the transcript is a
single Unknown bucket (typical for local Whisper without diarization).
"""

from __future__ import annotations

from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from app.frontend.chart_helpers import (
    segment_density,
    sentiment_curve,
    speaker_share,
)

# One physical canvas for every figure so exports and on-screen scaling stay consistent.
_CHART_FIGSIZE_IN = (8.5, 3.65)


def _low_quality_speaker_split(data: dict[str, Any], share: pd.Series) -> bool:
    """True when per-speaker visuals would be misleading (one unknown bucket, etc.)."""
    rm = str(data.get("role_method") or "").lower()
    if "skipped_no_diarization" in rm or "no_diarization" in rm:
        return True
    if share.empty:
        return True
    if len(share) >= 2:
        return False
    only = str(share.index[0]).strip().lower()
    return only in ("unknown", "unlabeled", "", "speaker")


def _fig_donut(share: pd.Series, title: str, *, figsize: tuple[float, float] = _CHART_FIGSIZE_IN) -> plt.Figure:
    fig, ax = plt.subplots(figsize=figsize, facecolor="#fafafa")
    ax.set_facecolor("#fafafa")
    if share.empty:
        ax.text(0.5, 0.5, "No speaker split yet", ha="center", va="center", fontsize=11, color="#64748b")
        ax.set_axis_off()
        ax.set_title(title, fontsize=12, fontweight="600", pad=12)
        fig.tight_layout()
        return fig
    colors = plt.cm.Spectral(np.linspace(0.15, 0.88, len(share)))
    _wedges, _t, autotexts = ax.pie(
        share.values,
        labels=share.index,
        autopct="%1.0f%%",
        colors=colors,
        startangle=120,
        pctdistance=0.72,
        textprops={"fontsize": 9},
    )
    for aut in autotexts:
        aut.set_color("#0f172a")
        aut.set_fontweight("600")
    ax.set_title(title, fontsize=12, fontweight="600", pad=12)
    ax.set_aspect("equal")
    fig.tight_layout()
    return fig


def _fig_engagement(
    dens: pd.DataFrame,
    title: str,
    *,
    figsize: tuple[float, float] = _CHART_FIGSIZE_IN,
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=figsize, facecolor="#fafafa")
    ax.set_facecolor("#fafafa")
    if dens.empty or dens["segments"].sum() == 0:
        ax.text(0.5, 0.5, "No timing data", ha="center", va="center", transform=ax.transAxes, color="#64748b")
    else:
        ax.fill_between(dens["minute"], dens["segments"], alpha=0.35, color="#6366f1")
        ax.plot(dens["minute"], dens["segments"], color="#4f46e5", linewidth=2.2)
        ax.set_xlabel("Minutes into meeting", fontsize=9, color="#475569")
        ax.set_ylabel("Activity (segments / min)", fontsize=9, color="#475569")
    ax.set_title(title, fontsize=12, fontweight="600", pad=10)
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def _fig_sentiment(
    curve: pd.DataFrame,
    title: str,
    *,
    figsize: tuple[float, float] = _CHART_FIGSIZE_IN,
) -> plt.Figure:
    fig, ax = plt.subplots(figsize=figsize, facecolor="#fafafa")
    ax.set_facecolor("#fafafa")
    if curve.empty:
        ax.text(0.5, 0.5, "No transcript", ha="center", va="center", transform=ax.transAxes, color="#64748b")
    else:
        y = curve["tone"].values
        x = curve["minute"].values
        ax.fill_between(x, y, 0, where=(y >= 0), alpha=0.35, color="#22c55e", interpolate=True)
        ax.fill_between(x, y, 0, where=(y < 0), alpha=0.35, color="#f97316", interpolate=True)
        ax.plot(x, y, color="#0f172a", linewidth=1.8, alpha=0.85)
        ax.axhline(0, color="#94a3b8", linewidth=0.8)
        ax.set_xlabel("Minutes", fontsize=9, color="#475569")
        ax.set_ylabel("Tone (approximate)", fontsize=9, color="#475569")
    ax.set_title(title, fontsize=12, fontweight="600", pad=10)
    ax.grid(True, alpha=0.22, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def render_meeting_intelligence_charts(
    data: dict[str, Any],
    key_prefix: str,
    *,
    outer_heading: bool = True,
) -> None:
    _ = key_prefix
    transcript = data.get("transcript") or []
    topics = data.get("topic_wise_summary") or []

    if outer_heading:
        st.markdown("##### Conversation intelligence")
        st.caption(
            "Activity and tone across the meeting. Speaking-time split appears only when multiple speakers are detected."
        )

    share = speaker_share(transcript)
    low_spk = _low_quality_speaker_split(data, share)

    if low_spk:
        st.markdown("**Who drove the conversation**")
        st.caption(
            "Chart omitted: the transcript does not separate multiple speakers, so a share-of-time pie would be misleading."
        )
    else:
        fig = _fig_donut(share, "Who drove the conversation")
        st.pyplot(fig, clear_figure=True, use_container_width=True)
        plt.close(fig)
        st.caption(
            "Estimated share of speaking time by speaker label from the transcript. "
            "Use it as a balance-of-airtime hint, not org-chart truth."
        )

    dens = segment_density(transcript, bin_sec=60)
    curve = sentiment_curve(transcript)
    ec1, ec2 = st.columns(2, gap="small")
    with ec1:
        fig2 = _fig_engagement(dens, "Energy across the meeting")
        st.pyplot(fig2, clear_figure=True, use_container_width=True)
        plt.close(fig2)
        st.caption(
            "Segments per minute over clock time — how dense the dialogue was in each segment."
        )
    with ec2:
        fig4 = _fig_sentiment(curve, "Tone over time (approximate)")
        st.pyplot(fig4, clear_figure=True, use_container_width=True)
        plt.close(fig4)
        st.caption(
            "Heuristic tone from transcript wording — useful for shape, not a clinical sentiment score."
        )

    if isinstance(topics, list) and topics:
        st.markdown("**Topics (from model summaries)**")
        st.caption("Structured topic rows from the pipeline — same theme count as the “Theme groups” KPI above.")
        rows = []
        for i, row in enumerate(topics[:12]):
            if isinstance(row, dict):
                rows.append(
                    {
                        "Topic": str(row.get("topic", f"Topic {i + 1}"))[:80],
                        "Summary": str(row.get("summary", ""))[:500],
                    }
                )
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=min(420, 120 + 36 * len(rows)))
