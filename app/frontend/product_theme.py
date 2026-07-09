"""Shared Streamlit styling — OFI brand (golden, yellow, black, white)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_LOGO_PATH = Path(__file__).parent / "assets" / "ofi_logo.png"

PRODUCT_CSS = """
<style>
    :root {
        --accent: #D4AF37;
        --accent-soft: #FFF9DB;
        --accent-light: #E6C567;
        --accent-hover: #C9A227;
        --surface: #ffffff;
        --bg: #E8E8E8;
        --border: #D4D4D4;
        --muted: #000000;
        --text: #000000;
        --text-subtle: #1a1a1a;
        --yellow-light: #FFF9DB;
        --yellow-border: #F5E6A3;
        --sidebar-bg0: #000000;
        --sidebar-bg1: #141414;
        --sidebar-bg2: #1f1f1f;
        --sidebar-text: #ffffff;
        --sidebar-muted: #E6C567;
        --sidebar-hover: rgba(230, 197, 103, 0.22);
        --sidebar-edge: rgba(230, 197, 103, 0.28);
        --sidebar-active: rgba(230, 197, 103, 0.34);
    }
    .block-container {
        padding-top: 1.25rem !important;
        padding-bottom: 2rem !important;
        max-width: 1260px !important;
    }
    /* ---- Sidebar toggle button — always visible ---- */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    /* ---- Dark sidebar (collapsible rail) ---- */
    section[data-testid="stSidebar"] {
        min-height: 100vh !important;
        border-right: 1px solid var(--sidebar-edge) !important;
        box-shadow: 6px 0 28px rgba(0, 0, 0, 0.35) !important;
        background: linear-gradient(188deg, var(--sidebar-bg0) 0%, var(--sidebar-bg1) 38%, var(--sidebar-bg2) 100%) !important;
    }
    section[data-testid="stSidebar"] > div {
        background: transparent !important;
        padding-top: 1.1rem !important;
        padding-bottom: 2rem !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        background: transparent !important;
        display: flex !important;
        flex-direction: column !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        order: 1 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.25rem !important;
    }
    /* Sidebar brand block — pinned above navigation */
    .ofi-sidebar-brand-wrap {
        text-align: center;
        padding: 0.15rem 0.35rem 0.35rem;
    }
    section[data-testid="stSidebar"] [data-testid="stImage"] {
        margin: 0 auto 0.35rem auto !important;
        max-width: 132px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stImage"] img {
        border-radius: 10px !important;
    }
    .ofi-sidebar-divider {
        margin: 0.55rem 0 0.15rem 0 !important;
        border: none !important;
        border-top: 1px solid rgba(230, 197, 103, 0.28) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
        order: 2 !important;
        margin-top: 0.15rem !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNavSeparator"] {
        display: none !important;
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
        color: #ffffff !important;
        font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] a:hover {
        color: var(--accent-light) !important;
    }
    section[data-testid="stSidebar"] hr {
        margin: 0.65rem 0 !important;
        border: none !important;
        border-top: 1px solid rgba(230, 197, 103, 0.22) !important;
    }
    section[data-testid="stSidebar"] [data-testid^="stPageLink"] {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(230, 197, 103, 0.12) !important;
        border-radius: 10px !important;
        padding: 2px 0 !important;
        margin-bottom: 4px !important;
    }
    section[data-testid="stSidebar"] [data-testid^="stPageLink"]:hover {
        background: var(--sidebar-hover) !important;
        border-color: rgba(230, 197, 103, 0.45) !important;
    }
    /* Active nav item — golden highlight */
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:has(p strong),
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:has(span strong),
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:has([data-testid="stMarkdownContainer"] strong) {
        background: var(--sidebar-active) !important;
        border: 1px solid rgba(230, 197, 103, 0.82) !important;
        box-shadow: inset 3px 0 0 var(--accent-light) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:has(p strong) [data-testid="stPageLink-NavLink"],
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:has(span strong) [data-testid="stPageLink-NavLink"],
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:has([data-testid="stMarkdownContainer"] strong) [data-testid="stPageLink-NavLink"] {
        background: transparent !important;
    }
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:has(p strong) a,
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:has(span strong) a,
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:has([data-testid="stMarkdownContainer"] strong) a,
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:has(p strong) p,
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:has(span strong) p,
    section[data-testid="stSidebar"] [data-testid="stPageLink"]:has([data-testid="stMarkdownContainer"] strong) p {
        color: var(--accent-light) !important;
        font-weight: 700 !important;
    }
    section[data-testid="stSidebar"] [data-testid^="stPageLink"] a {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] p.sidebar-product {
        margin: 0 0 0.15rem 0;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--accent-light) !important;
    }
    section[data-testid="stSidebar"] p.sidebar-tagline {
        margin: 0 0 0.5rem 0;
        font-size: 0.78rem;
        line-height: 1.35;
        color: var(--sidebar-muted) !important;
    }
    section[data-testid="stSidebar"] ::-webkit-scrollbar {
        width: 8px;
    }
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
        background: rgba(230, 197, 103, 0.35);
        border-radius: 8px;
    }
    section[data-testid="stSidebar"] ::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.5);
    }
    /* App canvas — light grey OFI background */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: var(--bg) !important;
        color: var(--text) !important;
    }
    h1, h2, h3, h4, h5, h6,
    [data-testid="stHeading"] h1, [data-testid="stHeading"] h2, [data-testid="stHeading"] h3,
    [data-testid="stHeading"] h4, [data-testid="stHeading"] h5, [data-testid="stHeading"] h6
    { letter-spacing: -0.02em; color: var(--text) !important; font-weight: 600 !important; }
    p, li, label, span, div,
    .stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown li, .stMarkdown div
    { color: var(--text) !important; }
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p,
    [data-testid="stCaptionContainer"] span,
    [data-testid="stCaptionContainer"] div,
    .stCaption, .stCaption p, .stCaption span, .stCaption div,
    [data-testid="stMarkdownContainer"] small
    {
        color: var(--text-subtle) !important;
        opacity: 1 !important;
        -webkit-text-fill-color: var(--text-subtle) !important;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stMetricDelta"]
    { color: var(--text) !important; }
    [data-testid="stAlert"] p,
    [data-testid="stAlert"] div,
    [data-testid="stAlert"] span,
    div[class*="stAlert"] p,
    div[class*="Alert"] p,
    div[class*="Alert"] div,
    div[class*="Alert"] span
    { color: var(--text) !important; font-weight: 500 !important; }
    [data-testid="stAlert"],
    div[class*="stAlert"] {
        background: var(--yellow-light) !important;
        border-color: var(--yellow-border) !important;
    }
    /* Primary buttons — light golden with black text */
    [data-testid="stBaseButton-primary"],
    [data-testid="stDownloadButton"] button[kind="primary"],
    [data-testid="stDownloadButton"] a[data-testid="stBaseButton-primary"] {
        background: var(--accent-light) !important;
        border-color: var(--accent) !important;
        color: #000000 !important;
    }
    [data-testid="stBaseButton-primary"]:hover,
    [data-testid="stBaseButton-primary"]:focus,
    [data-testid="stDownloadButton"] button[kind="primary"]:hover {
        background: var(--accent-hover) !important;
        border-color: var(--accent-hover) !important;
        color: #000000 !important;
    }
    [data-testid="stBaseButton-primary"]:active {
        background: var(--accent) !important;
        border-color: var(--accent) !important;
        color: #000000 !important;
    }
    [data-testid="stBaseButton-primary"] p,
    [data-testid="stBaseButton-primary"] span,
    [data-testid="stBaseButton-primary"]:hover p,
    [data-testid="stBaseButton-primary"]:hover span,
    [data-testid="stBaseButton-primary"]:focus p,
    [data-testid="stBaseButton-primary"]:active p,
    [data-testid="stDownloadButton"] button[kind="primary"] p,
    [data-testid="stDownloadButton"] button[kind="primary"] span
    { color: #000000 !important; }
    /* Secondary buttons — black background, white text */
    [data-testid="stBaseButton-secondary"] {
        background: #1a1a1a !important;
        border-color: #1a1a1a !important;
        color: #ffffff !important;
    }
    [data-testid="stBaseButton-secondary"]:hover {
        background: #333333 !important;
        border-color: #333333 !important;
        color: #ffffff !important;
    }
    [data-testid="stBaseButton-secondary"]:focus,
    [data-testid="stBaseButton-secondary"]:active {
        background: #000000 !important;
        border-color: #000000 !important;
        color: #ffffff !important;
    }
    [data-testid="stBaseButton-secondary"] p,
    [data-testid="stBaseButton-secondary"] span,
    [data-testid="stBaseButton-secondary"]:hover p,
    [data-testid="stBaseButton-secondary"]:hover span,
    [data-testid="stBaseButton-secondary"]:focus p,
    [data-testid="stBaseButton-secondary"]:active p { color: #ffffff !important; }
    /* Collapsible expanders — light yellow */
    [data-testid="stExpander"] {
        background: var(--yellow-light) !important;
        border: 1px solid var(--yellow-border) !important;
        border-radius: 10px !important;
    }
    [data-testid="stExpander"] details {
        background: var(--yellow-light) !important;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] [data-testid="stMarkdownContainer"] {
        background: var(--yellow-light) !important;
        color: var(--text) !important;
    }
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] p,
    [data-testid="stExpander"] span,
    [data-testid="stExpander"] li,
    [data-testid="stExpander"] label
    { color: var(--text) !important; }
    /* Main menu popover — keep Streamlit's own light text */
    [data-testid="stMainMenuPopover"] p,
    [data-testid="stMainMenuPopover"] li,
    [data-testid="stMainMenuPopover"] span,
    [data-testid="stMainMenuPopover"] div,
    [data-testid="stMainMenuPopover"] button,
    [data-testid="stMainMenuPopover"] a,
    ul[data-testid="stMainMenuList"] li,
    ul[data-testid="stMainMenuList"] p,
    ul[data-testid="stMainMenuList"] span { color: inherit !important; }
    ::selection { background: #E6C567; color: #000000; }
    ::-moz-selection { background: #E6C567; color: #000000; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
        border-color: var(--border) !important;
        background: var(--surface) !important;
    }
    .app-hero {
        border-radius: 14px;
        padding: 1.35rem 1.25rem 1.5rem;
        margin-bottom: 0.5rem;
        border: 1px solid var(--yellow-border);
        background: var(--surface);
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.06);
        text-align: left;
        min-height: 0;
    }
    .app-hero h3 { margin: 0.35rem 0 0.5rem; font-size: 1.15rem; color: var(--text); }
    .app-hero p { margin: 0; color: var(--text); font-size: 0.9rem; line-height: 1.5; }
    .app-hero .icon { font-size: 1.5rem; margin-bottom: 0.25rem; }
    .aci-info-box {
        background: var(--yellow-light);
        border: 1px solid var(--yellow-border);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        color: var(--text) !important;
        font-weight: 500;
        font-size: 0.95rem;
    }
    .aci-info-box p, .aci-info-box span, .aci-info-box div { color: var(--text) !important; }
    .recent-row {
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        background: var(--surface);
        color: var(--text);
    }
    .recent-row span { color: var(--text) !important; }
    .insight-section {
        border: 1px solid var(--yellow-border);
        border-radius: 10px;
        padding: 0.75rem 0.9rem;
        margin-bottom: 0.65rem;
        background: var(--yellow-light);
        color: var(--text);
    }
</style>
"""


def apply_product_theme() -> None:
    st.markdown(PRODUCT_CSS, unsafe_allow_html=True)


def render_sidebar_brand() -> None:
    """OFI logo and product title at the top of the sidebar."""
    with st.sidebar:
        if _LOGO_PATH.is_file():
            st.image(str(_LOGO_PATH), use_container_width=True)
        st.markdown(
            """
<div class="ofi-sidebar-brand-wrap">
  <p class="sidebar-product">Call Intelligence</p>
  <p class="sidebar-tagline">AI-powered meeting review</p>
</div>
<hr class="ofi-sidebar-divider" />
""",
            unsafe_allow_html=True,
        )


def centered_narrow():
    """Use as: _, content, _ = centered_narrow(); with content: ..."""
    return st.columns([0.12, 0.76, 0.12])
