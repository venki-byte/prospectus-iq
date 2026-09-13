"""
Institutional Terminal CSS Styling & Design Tokens for ProspectusIQ.
"""
import streamlit as st

# Institutional Terminal Design Tokens
COLOR_BG = "#0B0F19"
COLOR_SIDEBAR = "#0F172A"
COLOR_CARD = "#151D2E"
COLOR_CARD_HOVER = "#1C263B"
COLOR_INPUT_BG = "#1E293B"
COLOR_BORDER = "#222F49"
COLOR_BORDER_LIGHT = "#334155"
COLOR_TEXT_PRIMARY = "#F8FAFC"
COLOR_TEXT_MUTED = "#94A3B8"
COLOR_ACCENT = "#6366F1"
COLOR_BLUE = "#3B82F6"
COLOR_GREEN = "#10B981"
COLOR_AMBER = "#F59E0B"
COLOR_ROSE = "#F43F5E"

TERMINAL_CSS = """
<style>
/* -------------------------------------------------------------------------
   Global Page & Typography Resets
   ------------------------------------------------------------------------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

.stApp {
    background-color: #0B0F19 !important;
    color: #F8FAFC !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

code, pre, .mono {
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}

.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1440px !important;
}

header[data-testid="stHeader"] {
    background: transparent !important;
}

/* -------------------------------------------------------------------------
   Sidebar Styling & Dark-Label Visibility (Eliminate Invisible Text)
   ------------------------------------------------------------------------- */
section[data-testid="stSidebar"] {
    background-color: #0F172A !important;
    border-right: 1px solid #1E293B !important;
}

section[data-testid="stSidebar"] .block-container {
    padding-top: 1.5rem !important;
    padding-left: 1.2rem !important;
    padding-right: 1.2rem !important;
}

/* Checkboxes text visibility */
section[data-testid="stSidebar"] div[data-testid="stCheckbox"] label {
    color: #E2E8F0 !important;
}

section[data-testid="stSidebar"] div[data-testid="stCheckbox"] label span p {
    color: #E2E8F0 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}

/* Radio buttons text visibility */
section[data-testid="stSidebar"] .stRadio label span p {
    color: #F8FAFC !important;
    font-weight: 500 !important;
    font-size: 14px !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label {
    background-color: #151D2E !important;
    border: 1px solid #222F49 !important;
    border-radius: 8px !important;
    padding: 9px 14px !important;
    margin-bottom: 8px !important;
    cursor: pointer !important;
    transition: all 0.15s ease-in-out !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
    border-color: #6366F1 !important;
    background-color: #1A2438 !important;
}

/* -------------------------------------------------------------------------
   Eliminate White Background Bleed on Inputs & Selects
   ------------------------------------------------------------------------- */
div[data-testid="stTextInput"] input {
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    font-size: 14px !important;
}

div[data-testid="stTextInput"] input:focus {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 1px #6366F1 !important;
}

div[data-testid="stTextInput"] input::placeholder {
    color: #64748B !important;
}

div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
}

div[data-testid="stSelectbox"] svg {
    fill: #94A3B8 !important;
}

div[data-baseweb="popover"],
ul[role="listbox"] {
    background-color: #1E293B !important;
    border: 1px solid #334155 !important;
    color: #F8FAFC !important;
}

li[role="option"] {
    background-color: #1E293B !important;
    color: #F8FAFC !important;
}

li[role="option"]:hover,
li[aria-selected="true"] {
    background-color: #2D3D58 !important;
    color: #FFFFFF !important;
}

/* -------------------------------------------------------------------------
   Table / Dataframe Dark Terminal Integration
   ------------------------------------------------------------------------- */
div[data-testid="stDataFrame"] {
    background-color: #151D2E !important;
    border: 1px solid #222F49 !important;
    border-radius: 8px !important;
    padding: 4px !important;
}

div[data-testid="stDataFrame"] div[data-testid="glide-cell"] {
    color: #F8FAFC !important;
    background-color: #151D2E !important;
}

div[data-testid="stDataFrame"] [role="grid"] {
    background-color: #151D2E !important;
}

/* -------------------------------------------------------------------------
   High-Contrast Metric & KPI Cards
   ------------------------------------------------------------------------- */
.terminal-card {
    background-color: #151D2E;
    border: 1px solid #222F49;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}

.terminal-kpi-card {
    background-color: #151D2E;
    border: 1px solid #222F49;
    border-radius: 8px;
    padding: 14px 18px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    height: 100%;
}

.metric-title {
    color: #94A3B8;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.metric-value-lg {
    font-size: 26px;
    font-weight: 800;
    color: #F8FAFC;
    margin-top: 4px;
    line-height: 1.15;
}

.metric-sub {
    font-size: 12px;
    color: #64748B;
    margin-top: 2px;
}

/* -------------------------------------------------------------------------
   Clean Button States
   ------------------------------------------------------------------------- */
button[kind="primary"] {
    background-color: #6366F1 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    transition: all 0.15s ease-in-out !important;
}

button[kind="primary"]:hover {
    background-color: #4F46E5 !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35) !important;
}

button[kind="secondary"] {
    background-color: #1E293B !important;
    color: #E2E8F0 !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}

button[kind="secondary"]:hover {
    border-color: #6366F1 !important;
    color: #FFFFFF !important;
    background-color: #24324A !important;
}

/* -------------------------------------------------------------------------
   Institutional Verdict Badges
   ------------------------------------------------------------------------- */
.badge-compounder {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10B981;
    border: 1px solid #10B981;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.82rem;
    letter-spacing: 0.3px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

.badge-listing {
    background-color: rgba(59, 130, 246, 0.15);
    color: #3B82F6;
    border: 1px solid #3B82F6;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.82rem;
    letter-spacing: 0.3px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

.badge-speculative {
    background-color: rgba(245, 158, 11, 0.15);
    color: #F59E0B;
    border: 1px solid #F59E0B;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.82rem;
    letter-spacing: 0.3px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

.badge-avoid {
    background-color: rgba(244, 63, 94, 0.18);
    color: #F43F5E;
    border: 1px solid #F43F5E;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.82rem;
    letter-spacing: 0.3px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

.badge-pending {
    background-color: rgba(148, 163, 184, 0.12);
    color: #94A3B8;
    border: 1px solid #475569;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.82rem;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

/* -------------------------------------------------------------------------
   Lifecycle Badges
   ------------------------------------------------------------------------- */
.lifecycle-active {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10B981;
    border: 1px solid rgba(16, 185, 129, 0.4);
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    display: inline-block;
}

.lifecycle-upcoming {
    background-color: rgba(245, 158, 11, 0.15);
    color: #F59E0B;
    border: 1px solid rgba(245, 158, 11, 0.4);
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    display: inline-block;
}

.lifecycle-closed {
    background-color: rgba(244, 63, 94, 0.12);
    color: #F43F5E;
    border: 1px solid rgba(244, 63, 94, 0.35);
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    display: inline-block;
}

/* -------------------------------------------------------------------------
   Executive Brief & Content Blocks
   ------------------------------------------------------------------------- */
.executive-brief-container {
    background-color: #151D2E;
    border: 1px solid #222F49;
    border-left: 4px solid #6366F1;
    border-radius: 0 8px 8px 0;
    padding: 16px 20px;
    margin-bottom: 20px;
}

.brief-header {
    font-size: 0.8rem;
    font-weight: 700;
    color: #6366F1;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 6px;
}

.brief-text {
    font-size: 0.96rem;
    line-height: 1.65;
    color: #E2E8F0;
}

/* Balance Sheet (Pros & Cons) */
.balance-sheet-bull {
    background-color: rgba(16, 185, 129, 0.04);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 8px;
    padding: 16px 18px;
    height: 100%;
}

.balance-sheet-bear {
    background-color: rgba(244, 63, 94, 0.04);
    border: 1px solid rgba(244, 63, 94, 0.25);
    border-radius: 8px;
    padding: 16px 18px;
    height: 100%;
}

.column-header-bull {
    color: #10B981;
    font-weight: 700;
    font-size: 0.95rem;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.column-header-bear {
    color: #F43F5E;
    font-weight: 700;
    font-size: 0.95rem;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.bullet-item {
    font-size: 0.88rem;
    line-height: 1.55;
    color: #CBD5E1;
    margin-bottom: 8px;
    padding-left: 4px;
}

/* Divergence Split */
.divergence-card {
    background-color: #151D2E;
    border: 1px solid #222F49;
    border-radius: 8px;
    padding: 16px 18px;
    height: 100%;
}

.divergence-header-crowd {
    color: #F59E0B;
    font-weight: 700;
    font-size: 0.9rem;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.divergence-header-filing {
    color: #3B82F6;
    font-weight: 700;
    font-size: 0.9rem;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.divergence-text {
    font-size: 0.88rem;
    line-height: 1.55;
    color: #CBD5E1;
}

/* 12-Factor Forensic Rubric Items */
.factor-card {
    background-color: #121826;
    border: 1px solid #1E293B;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 12px;
}

.evidence-quote-box {
    background-color: #0B0F19;
    border-left: 3px solid #F59E0B;
    padding: 10px 14px;
    margin-top: 10px;
    border-radius: 0 6px 6px 0;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 0.82rem;
    color: #E2E8F0;
    line-height: 1.5;
}

.severity-pill-critical {
    font-size: 0.72rem;
    background-color: rgba(244, 63, 94, 0.2);
    color: #F43F5E;
    border: 1px solid #F43F5E;
    padding: 2px 7px;
    border-radius: 4px;
    font-weight: 700;
    display: inline-block;
}

.severity-pill-medium {
    font-size: 0.72rem;
    background-color: rgba(245, 158, 11, 0.2);
    color: #F59E0B;
    border: 1px solid #F59E0B;
    padding: 2px 7px;
    border-radius: 4px;
    font-weight: 600;
    display: inline-block;
}

.severity-pill-low {
    font-size: 0.72rem;
    background-color: rgba(16, 185, 129, 0.2);
    color: #10B981;
    border: 1px solid #10B981;
    padding: 2px 7px;
    border-radius: 4px;
    font-weight: 600;
    display: inline-block;
}

/* Streamlit Expander Overrides */
div[data-testid="stExpander"] {
    background-color: #151D2E !important;
    border: 1px solid #222F49 !important;
    border-radius: 8px !important;
    margin-bottom: 12px !important;
}

div[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: #F8FAFC !important;
    padding: 12px 16px !important;
}

div[data-testid="stExpander"] summary:hover {
    color: #6366F1 !important;
}

/* Status Pill */
.system-status-pill {
    background-color: rgba(16, 185, 129, 0.12);
    color: #10B981;
    border: 1px solid rgba(16, 185, 129, 0.3);
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}
</style>
"""

def apply_institutional_theme():
    """Injects the institutional dark terminal stylesheet."""
    st.markdown(TERMINAL_CSS, unsafe_allow_html=True)
