"""Shared Streamlit styling — client-ready, restrained SaaS look."""

from __future__ import annotations

import streamlit as st

PRODUCT_CSS = """
<style>
    :root {
        --accent: #4f46e5;
        --accent-soft: #eef2ff;
        --surface: #ffffff;
        --border: #e5e7eb;
        --muted: #6b7280;
        --text: #111827;
        --sidebar-bg0: #0b1220;
        --sidebar-bg1: #111827;
        --sidebar-bg2: #1e293b;
        --sidebar-text: #e2e8f0;
        --sidebar-muted: #94a3b8;
        --sidebar-hover: rgba(99, 102, 241, 0.28);
        --sidebar-edge: rgba(148, 163, 184, 0.22);
    }
    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 2rem !important;
        max-width: 1260px !important;
    }
    /* ---- Dark sidebar (collapsible rail) ---- */
    section[data-testid="stSidebar"] {
        min-height: 100vh !important;
        width: 17.5rem !important;
        min-width: 17rem !important;
        border-right: 1px solid var(--sidebar-edge) !important;
        box-shadow: 6px 0 28px rgba(2, 6, 23, 0.35) !important;
        background: linear-gradient(188deg, var(--sidebar-bg0) 0%, var(--sidebar-bg1) 38%, var(--sidebar-bg2) 100%) !important;
    }
    section[data-testid="stSidebar"] > div {
        background: transparent !important;
        padding-top: 1.1rem !important;
        padding-bottom: 2rem !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        background: transparent !important;
    }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.25rem !important;
    }
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] li,
    section[data-testid="stSidebar"] label {
        color: var(--sidebar-text) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: var(--sidebar-muted) !important;
    }
    section[data-testid="stSidebar"] a {
        color: #f8fafc !important;
        font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] a:hover {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] hr {
        margin: 0.65rem 0 !important;
        border: none !important;
        border-top: 1px solid rgba(148, 163, 184, 0.22) !important;
    }
    section[data-testid="stSidebar"] [data-testid^="stPageLink"] {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 10px !important;
        padding: 2px 0 !important;
        margin-bottom: 4px !important;
    }
    section[data-testid="stSidebar"] [data-testid^="stPageLink"]:hover {
        background: var(--sidebar-hover) !important;
        border-color: rgba(165, 180, 252, 0.45) !important;
    }
    section[data-testid="stSidebar"] [data-testid^="stPageLink"] a {
        color: #f1f5f9 !important;
    }
    section[data-testid="stSidebar"] p.sidebar-product {
        margin: 0 0 0.15rem 0;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #a5b4fc !important;
    }
    section[data-testid="stSidebar"] p.sidebar-tagline {
        margin: 0 0 0.5rem 0;
        font-size: 0.78rem;
        line-height: 1.35;
        color: #94a3b8 !important;
    }
    section[data-testid="stSidebar"] ::-webkit-scrollbar {
        width: 8px;
    }
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
        background: rgba(148, 163, 184, 0.35);
        border-radius: 8px;
    }
    section[data-testid="stSidebar"] ::-webkit-scrollbar-track {
        background: rgba(15, 23, 42, 0.5);
    }
    /* App canvas — slight tint so the home page feels fuller vs. flat white */
    .stApp {
        background: linear-gradient(165deg, #eef2ff 0%, #f8fafc 28%, #f1f5f9 100%) !important;
    }
    h1, h2, h3 { letter-spacing: -0.02em; color: var(--text) !important; font-weight: 600 !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
        border-color: var(--border) !important;
    }
    .app-hero {
        border-radius: 14px;
        padding: 1.35rem 1.25rem 1.5rem;
        border: 1px solid var(--border);
        background: var(--surface);
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.09);
        text-align: left;
        min-height: 0;
    }
    .app-hero h3 { margin: 0.35rem 0 0.5rem; font-size: 1.15rem; color: var(--text); }
    .app-hero p { margin: 0; color: var(--muted); font-size: 0.9rem; line-height: 1.5; }
    .app-hero .icon { font-size: 1.5rem; margin-bottom: 0.25rem; }
    .recent-row {
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        background: #ffffff;
    }
    .insight-section {
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.75rem 0.9rem;
        margin-bottom: 0.65rem;
        background: #fcfcfd;
    }
</style>
"""


def apply_product_theme() -> None:
    st.markdown(PRODUCT_CSS, unsafe_allow_html=True)


def centered_narrow():
    """Use as: _, content, _ = centered_narrow(); with content: ..."""
    return st.columns([0.12, 0.76, 0.12])
