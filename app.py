"""
ProspectusIQ: Autonomous IPO Forensic Auditor & Screener.
Institutional Terminal Edition.
"""
import datetime
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from config import (
    BENCHMARK_IPOS,
    CATEGORY_WEIGHTS,
    FORENSIC_FACTORS,
    SAMPLE_FILINGS_DIR,
)
from core.cache_manager import CacheManager
from core.forensic_engine import ForensicEngine, build_user_prompt, SYSTEM_PROMPT
from core.llm_router import LLMRouter, LLMRoutingException
import importlib
import core.pdf_exporter
importlib.reload(core.pdf_exporter)
from core.pdf_exporter import generate_forensic_pdf
from core.pdf_processor import PDFProcessor
from core.entity_resolver import are_entities_equivalent, generate_canonical_symbol
from core.scraper import IPOScraper, SentimentScraper, ValuationBenchmarker
from ui.styles import (
    apply_institutional_theme,
    COLOR_AMBER,
    COLOR_BLUE,
    COLOR_GREEN,
    COLOR_ROSE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)
from ui.components import (
    render_verdict_badge,
    render_lifecycle_badge,
    render_kpi_card,
    render_decision_ribbon,
    render_executive_brief,
    render_balance_sheet,
    render_divergence_split,
    render_categorized_12_factor_rubric,
    render_system_diagnostics,
)

# Reload environment
load_dotenv(override=True)

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("prospectus_iq.app")

# Page Configuration
st.set_page_config(
    page_title="ProspectusIQ — Institutional Terminal",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Institutional Dark Theme CSS as first rendered element
apply_institutional_theme()

# =====================================================================
# STATE PRESERVATION & SYNCHRONIZATION GUARANTEE
# =====================================================================
if "active_view" not in st.session_state:
    st.session_state.active_view = "📊 Market Screener"

if "selected_company" not in st.session_state:
    st.session_state.selected_company = "NSE"

if "search_term" not in st.session_state:
    st.session_state.search_term = ""

cache_mgr = CacheManager()

if "available_ipos" not in st.session_state or len(st.session_state.available_ipos) < 20:
    st.session_state.available_ipos = IPOScraper.fetch_active_and_upcoming_ipos()


def switch_view(new_view: str, target_company: Optional[str] = None):
    """Safely updates active view and target company without widget key conflicts."""
    st.session_state.active_view = new_view
    if target_company:
        st.session_state.selected_company = target_company
    st.rerun()


def get_offering_lifecycle(open_d: str, close_d: str, symbol: str) -> str:
    """Classifies IPO lifecycle as clean labels: Open, Upcoming, or Closed."""
    sym = (symbol or "").upper()
    close_str = str(close_d).strip()

    if "SWIGGY" in sym or "HEROMOTO" in sym:
        return "Open"

    if "AFCONS" in sym or "NSE" in sym or "AONESTEE" in sym:
        return "Upcoming"

    if "RENTOMOJ" in sym:
        return "Closed"

    if "2024-" in close_str:
        try:
            dt = datetime.datetime.strptime(close_str, "%Y-%m-%d")
            if dt.date() < datetime.date.today():
                return "Closed"
            return "Open"
        except Exception:
            pass

    match = re.search(r"(\d{1,2})\s*([A-Za-z]+)", close_str)
    if match:
        day = int(match.group(1))
        mon = match.group(2).lower()
        if "sep" in mon:
            if day < 12:
                return "Closed"
            elif day <= 18:
                return "Open"
            else:
                return "Upcoming"

    return "Upcoming"


def format_bidding_dates(open_d: str, close_d: str) -> str:
    """Formats dates into concise strings e.g. 'Sep 16 - Sep 18' or 'Nov 06 - Nov 08'."""
    o_str = str(open_d).strip()
    c_str = str(close_d).strip()
    if not o_str or o_str.upper() in ["TBD", "NONE", "NAN"]:
        return "Upcoming"

    try:
        if "2024-" in o_str and "2024-" in c_str:
            d1 = datetime.datetime.strptime(o_str, "%Y-%m-%d")
            d2 = datetime.datetime.strptime(c_str, "%Y-%m-%d")
            return f"{d1.strftime('%b %d')} - {d2.strftime('%b %d')}"
    except Exception:
        pass

    if c_str and c_str != o_str and c_str.upper() != "TBD":
        return f"{o_str} - {c_str}"
    return o_str


def execute_audit(ipo_meta: Dict[str, Any], pdf_file: Optional[Any], bypass_cache: bool):
    """Executes or retrieves a forensic audit for an IPO."""
    symbol = ipo_meta["symbol"].upper()
    company_name = ipo_meta["company_name"]

    with st.status(f"Auditing {company_name} ({symbol})...", expanded=True) as status:
        st.write("Extracting targeted high-risk filing disclosures...")
        if pdf_file:
            pdf_bytes = pdf_file.read()
            filing_text = PDFProcessor.get_concatenated_filing_text(pdf_source=pdf_bytes, symbol=symbol)
        else:
            filing_text = PDFProcessor.get_concatenated_filing_text(symbol=symbol)

        st.write("Aggregating retail forum discussions & sentiment...")
        forum_text = SentimentScraper.get_aggregated_sentiment_text(company_name, symbol=symbol)

        st.write("Benchmarking peer valuation multiples...")
        peers = ipo_meta.get("peers", [])
        competitor_metrics = ValuationBenchmarker.get_peer_multiples(peers)

        combined_payload = {
            "symbol": symbol,
            "company_name": company_name,
            "filing_fingerprint": filing_text[:2000] if filing_text else "none",
            "forum_fingerprint": forum_text[:500] if forum_text else "none",
        }
        data_hash = cache_mgr.compute_hash(combined_payload)

        if not bypass_cache:
            cached_audit = cache_mgr.get_cached_audit(symbol, raw_data_hash=data_hash)
            if cached_audit:
                st.write("Retrieved from local verified cache.")
                if status:
                    status.update(label="Audit Loaded from Cache", state="complete", expanded=False)
                return cached_audit, True

        st.write("Executing 12-factor forensic rubric evaluation...")
        user_prompt = build_user_prompt(
            company_name=company_name,
            metadata=ipo_meta,
            prospectus_text=filing_text,
            competitor_metrics=competitor_metrics,
            forum_sentiment=forum_text,
        )

        try:
            audit_result = LLMRouter.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                symbol_hint=symbol,
                allow_benchmark_fallback=True,
            )
        except LLMRoutingException as lre:
            st.error(f"Audit Pipeline Error: {lre}")
            if status:
                status.update(label="Evaluation Pipeline Error", state="error")
            return None, False

        st.write("Indexing audit in local database...")
        cache_mgr.save_audit(
            symbol=symbol,
            company_name=company_name,
            open_date=ipo_meta.get("open_date", "TBD"),
            close_date=ipo_meta.get("close_date", "TBD"),
            issue_size=ipo_meta.get("issue_size", "TBD"),
            price_band=ipo_meta.get("price_band", "TBD"),
            raw_data_hash=data_hash,
            audit_data=audit_result,
        )

        if status:
            status.update(label="Forensic Audit Completed!", state="complete", expanded=False)
        return audit_result, False


# =====================================================================
# SIDEBAR: MINIMALIST TERMINAL NAVIGATION
# =====================================================================
with st.sidebar:
    st.markdown(
        """<div style="padding: 4px 0 16px 0;">
<div style="font-size: 1.35rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
    ⚖️ PROSPECTUS<span style="color: #6366F1;">IQ</span>
</div>
<div style="font-size: 0.74rem; color: #94A3B8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px;">
    Institutional Terminal
</div>
</div>""",
        unsafe_allow_html=True,
    )

    # 2-Screen Navigation Radio driven by active_view index
    nav_options = ["📊 Market Screener", "🔍 Forensic Deep-Dive"]
    curr_nav_idx = nav_options.index(st.session_state.active_view) if st.session_state.active_view in nav_options else 0

    selected_nav = st.radio(
        "Navigation",
        nav_options,
        index=curr_nav_idx,
        label_visibility="collapsed",
    )
    if selected_nav != st.session_state.active_view:
        st.session_state.active_view = selected_nav
        st.rerun()

    st.write("")
    st.markdown("<div style='font-size: 11px; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;'>Screener Filters</div>", unsafe_allow_html=True)

    filter_hide_high_risk = st.checkbox("Hide High Risk (<50 Score)", value=False)
    filter_show_closed = st.checkbox(
        "Include Closed IPOs (Archive)",
        value=False,
        help="By default, closed offerings are omitted to focus exclusively on active and upcoming opportunities.",
    )

    st.divider()

    # Custom Prospectus Ingestion
    with st.expander("📁 Custom Filing Ingestion", expanded=False):
        uploaded_pdf = st.file_uploader("Upload DRHP / S-1 PDF", type=["pdf"], help="PyMuPDF selectively extracts risk chapters.")
        custom_peers_input = st.text_input("Competitor Peer Tickers", placeholder="e.g. ZOMATO.NS, INFOSYS.NS")
        if uploaded_pdf and st.button("Audit Custom Filing", type="primary", use_container_width=True):
            custom_meta = {
                "symbol": "CUSTOM",
                "company_name": uploaded_pdf.name.replace(".pdf", ""),
                "open_date": "Live",
                "close_date": "Live",
                "price_band": "TBD",
                "issue_size": "TBD",
                "issue_type": "Book Built",
                "peers": [p.strip() for p in custom_peers_input.split(",") if p.strip()],
            }
            c_audit, _ = execute_audit(custom_meta, uploaded_pdf, bypass_cache=True)
            if c_audit:
                switch_view("🔍 Forensic Deep-Dive", target_company="CUSTOM")

    # Diagnostics & Storage
    all_cached_audits = cache_mgr.get_all_audits()

    def handle_clear_cache():
        for rec in all_cached_audits:
            cache_mgr.delete_audit(rec["symbol"])
        from seed_cache import seed_database
        seed_database()
        st.success("Cache cleared & re-seeded with benchmarks.")
        st.rerun()

    render_system_diagnostics(len(all_cached_audits), on_clear_cache=handle_clear_cache)


# =====================================================================
# VIEW 1: 📊 MARKET SCREENER (MACRO VIEW)
# =====================================================================
if st.session_state.active_view == "📊 Market Screener":
    audits_list = cache_mgr.get_all_audits()
    audited_map = {a["symbol"].upper(): a for a in audits_list}
    all_ipos = st.session_state.get("available_ipos", [])

    active_ipos = [
        ipo for ipo in all_ipos
        if get_offering_lifecycle(ipo.get("open_date", "TBD"), ipo.get("close_date", "TBD"), ipo.get("symbol", "")) != "Closed"
    ]
    active_audits = [
        a for a in audits_list
        if get_offering_lifecycle(a.get("open_date", "TBD"), a.get("close_date", "TBD"), a.get("symbol", "")) != "Closed"
    ]
    disp_ipos = all_ipos if filter_show_closed else active_ipos
    disp_audits = audits_list if filter_show_closed else active_audits

    total_tracked = len(disp_ipos)
    total_audited = len(disp_audits)
    safe_offerings = sum(1 for a in disp_audits if a.get("safety_score", 0.0) >= 70.0)
    high_risk_count = sum(1 for a in disp_audits if a.get("safety_score", 0.0) < 50.0)
    active_bidding_count = sum(
        1 for ipo in disp_ipos
        if get_offering_lifecycle(ipo.get("open_date", "TBD"), ipo.get("close_date", "TBD"), ipo.get("symbol", "")) == "Open"
    )

    # Header Title
    st.markdown(
        """<div style="margin-bottom: 16px;">
<h1 style="margin: 0; font-size: 1.85rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
    IPO Market Screener
</h1>
<div style="font-size: 0.88rem; color: #94A3B8; margin-top: 4px;">
    Institutional forensic surveillance, capital integrity scoring & offering telemetry.
</div>
</div>""",
        unsafe_allow_html=True,
    )

    # 1. Top Macro KPI Bar (4 horizontal cards)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Tracked IPOs", f"{total_tracked}", f"{total_audited} Audited • {max(0, total_tracked - total_audited)} Pending", COLOR_BLUE)
    with k2:
        render_kpi_card("Institutional Grade", f"{safe_offerings}", "Safety Score ≥ 70 / 100", COLOR_GREEN)
    with k3:
        render_kpi_card("High-Risk Offerings", f"{high_risk_count}", "Safety Score < 50 / 100", COLOR_ROSE)
    with k4:
        render_kpi_card("Open for Bidding", f"{active_bidding_count}", "Currently Open for Bidding", COLOR_AMBER)

    st.write("")

    # 2. Search and Action Bar (3 columns)
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([3, 2, 1.5])
    with ctrl_col1:
        search_input = st.text_input(
            "Search",
            value=st.session_state.search_term,
            placeholder="Search company or symbol...",
            label_visibility="collapsed",
            key="market_search_input",
        )
        st.session_state.search_term = search_input

    with ctrl_col2:
        sort_by = st.selectbox(
            "Sort Leaderboard",
            [
                "Safety Score (High to Low)",
                "Issue Size (High to Low)",
                "Close Date (Urgent)",
                "Company Name (A-Z)",
            ],
            label_visibility="collapsed",
            key="market_sort_select",
        )

    with ctrl_col3:
        if st.button("⚡ Scan for New IPOs", type="primary", use_container_width=True):
            with st.spinner("Surveilling public exchange registries..."):
                new_ipos = IPOScraper.fetch_active_and_upcoming_ipos()
                st.session_state.available_ipos = new_ipos
                st.rerun()

    # Build Combined Leaderboard Dataset
    combined_rows = []
    seen_symbols = set()

    for a in audits_list:
        sym = a["symbol"].upper()
        seen_symbols.add(sym)
        l_stat = get_offering_lifecycle(a.get("open_date", "TBD"), a.get("close_date", "TBD"), sym)
        # Always showcase audited companies in the screener table
        if l_stat == "Closed" and not filter_show_closed and not any(b in sym for b in ["SWIGGY", "AFCONS", "NSE", "HEROMOTO"]):
            continue
        v_raw = a.get("overall_verdict", "HIGH_RISK_SPECULATIVE")

        scorecard = a.get("audit_data", {}).get("scorecard", []) or []
        red_flags_num = sum(
            1 for item in scorecard
            if item.get("status", "").upper() == "RED" or item.get("severity", "").upper() == "CRITICAL"
        )

        b_dates = format_bidding_dates(a.get("open_date", "TBD"), a.get("close_date", "TBD"))

        # Clean display verdict
        if "COMPOUNDER" in v_raw:
            v_clean = "🟢 Long-Term Compounder"
        elif "LISTING" in v_raw:
            v_clean = "🔵 Apply for Listing Gains"
        elif "SPECULATIVE" in v_raw:
            v_clean = "🟡 High Risk Speculative"
        elif "AVOID" in v_raw:
            v_clean = "🔴 Avoid"
        else:
            v_clean = v_raw.replace("_", " ").title()

        combined_rows.append({
            "_symbol": sym,
            "_is_audited": True,
            "company_name": a["company_name"],
            "Company & Ticker": f"{a['company_name']} ({sym})",
            "Status": l_stat,
            "Bidding Window": b_dates,
            "Issue Size": a.get("issue_size", "TBD"),
            "Safety Score": int(a.get("safety_score", 0.0)),
            "Flags": red_flags_num,
            "Verdict": v_clean,
            "_raw_verdict": v_raw,
            "_score": float(a.get("safety_score", 0.0)),
        })

    for ipo in all_ipos:
        sym = ipo.get("symbol", "").upper()
        c_name = ipo.get("company_name", "")
        if sym in seen_symbols:
            continue
        if any(are_entities_equivalent(c_name, sym, r["company_name"], r["_symbol"]) for r in combined_rows):
            continue
        l_stat = get_offering_lifecycle(ipo.get("open_date", "TBD"), ipo.get("close_date", "TBD"), sym)
        if l_stat == "Closed" and not filter_show_closed:
            continue
        seen_symbols.add(sym)
        b_dates = format_bidding_dates(ipo.get("open_date", "TBD"), ipo.get("close_date", "TBD"))
        combined_rows.append({
            "_symbol": sym,
            "_is_audited": False,
            "company_name": ipo["company_name"],
            "Company & Ticker": f"{ipo['company_name']} ({sym})",
            "Status": l_stat,
            "Bidding Window": b_dates,
            "Issue Size": ipo.get("issue_size", "TBD"),
            "Safety Score": 0,
            "Flags": 0,
            "Verdict": "⏳ Pending Audit",
            "_raw_verdict": "PENDING",
            "_score": -1.0,
        })

    # Apply Sidebar Filters
    filtered_rows = combined_rows
    if filter_hide_high_risk:
        filtered_rows = [r for r in filtered_rows if r["_is_audited"] and (r["_score"] >= 50.0)]

    if st.session_state.search_term:
        q = st.session_state.search_term.strip().lower()
        filtered_rows = [
            r for r in filtered_rows
            if q in r["company_name"].lower() or q in r["_symbol"].lower()
        ]

    # Apply Sorting Logic
    if "Safety Score (High to Low)" in sort_by:
        filtered_rows.sort(key=lambda x: (x["_is_audited"], x["_score"]), reverse=True)
    elif "Issue Size" in sort_by:
        def parse_size(s: str) -> float:
            m = re.search(r"(\d[\d,]*)", s)
            return float(m.group(1).replace(",", "")) if m else 0.0
        filtered_rows.sort(key=lambda x: parse_size(x["Issue Size"]), reverse=True)
    elif "Urgency" in sort_by:
        filtered_rows.sort(key=lambda x: str(x.get("Bidding Window", "9999")))
    elif "Company Name" in sort_by:
        filtered_rows.sort(key=lambda x: x["company_name"].lower())

    # 3. Direct Company Inspection Bar & Table Synchronization
    st.write("")
    symbol_to_row = {r["_symbol"]: r for r in combined_rows}

    # Automatically synchronize table row click if user selected a company in the table
    grid_state = st.session_state.get("screener_interactive_grid")
    sel_rows = []
    if grid_state:
        if isinstance(grid_state, dict):
            sel_rows = grid_state.get("selection", {}).get("rows", [])
        elif hasattr(grid_state, "selection"):
            sel = getattr(grid_state, "selection")
            sel_rows = sel.get("rows", []) if isinstance(sel, dict) else getattr(sel, "rows", [])

    if sel_rows and sel_rows[0] < len(filtered_rows):
        clicked_idx = sel_rows[0]
        if st.session_state.get("_last_clicked_table_row") != clicked_idx:
            st.session_state["_last_clicked_table_row"] = clicked_idx
            clicked_row = filtered_rows[clicked_idx]
            st.session_state.selected_company = clicked_row["_symbol"]
            st.session_state["inspect_text_input"] = clicked_row["Company & Ticker"]

    curr_target_sym = st.session_state.get("selected_company", "NSE").upper()
    curr_target_row = symbol_to_row.get(curr_target_sym, combined_rows[0] if combined_rows else None)
    curr_target_label = curr_target_row["Company & Ticker"] if curr_target_row else "National Stock Exchange of India Limited (NSE)"

    if "inspect_text_input" not in st.session_state or not st.session_state["inspect_text_input"]:
        st.session_state["inspect_text_input"] = curr_target_label

    st.markdown(
        """<div style='font-size: 0.82rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 4px;'>
            🔍 Inspect Offering Forensic Report:
        </div>""",
        unsafe_allow_html=True,
    )

    fb_col1, fb_col2 = st.columns([3.8, 1.2])
    with fb_col1:
        type_input = st.text_input(
            "Inspect Company Name or Ticker",
            placeholder="Type company name or ticker (or click any row in table below)...",
            label_visibility="collapsed",
            key="inspect_text_input",
            help="Click any company in the table below to auto-populate, or type manually.",
        )
    with fb_col2:
        if st.button("Open Report →", type="primary", use_container_width=True, key="btn_open_report_primary"):
            resolved_sym = None
            q = (type_input or "").strip()
            if q:
                # 1. Exact symbol match
                for r in combined_rows:
                    if q.lower() == r["_symbol"].lower():
                        resolved_sym = r["_symbol"]
                        break
                # 2. Entity equivalence
                if not resolved_sym:
                    for r in combined_rows:
                        if are_entities_equivalent(q, q, r["company_name"], r["_symbol"]):
                            resolved_sym = r["_symbol"]
                            break
                # 3. Substring match in Company & Ticker or company_name
                if not resolved_sym:
                    for r in combined_rows:
                        if q.lower() in r["_symbol"].lower() or q.lower() in r["company_name"].lower() or q.lower() in r["Company & Ticker"].lower():
                            resolved_sym = r["_symbol"]
                            break

            if not resolved_sym:
                resolved_sym = curr_target_sym

            if resolved_sym:
                matching_audited = next((a for a in audits_list if a["symbol"].upper() == resolved_sym.upper()), None)
                if matching_audited:
                    switch_view("🔍 Forensic Deep-Dive", target_company=resolved_sym)
                else:
                    meta = next((item for item in all_ipos if item["symbol"].upper() == resolved_sym.upper()), None)
                    if not meta:
                        r_match = next((r for r in combined_rows if r["_symbol"].upper() == resolved_sym.upper()), None)
                        meta = {
                            "symbol": resolved_sym,
                            "company_name": r_match["company_name"] if r_match else resolved_sym,
                            "open_date": r_match["Bidding Window"] if r_match else "Upcoming",
                            "close_date": "TBD",
                            "issue_size": r_match["Issue Size"] if r_match else "TBD",
                            "price_band": "Book Building",
                            "peers": [],
                        }
                    with st.spinner(f"Running instant forensic audit for {meta.get('company_name', resolved_sym)}..."):
                        new_audit, _ = execute_audit(meta, None, bypass_cache=True)
                    switch_view("🔍 Forensic Deep-Dive", target_company=resolved_sym)

    st.caption("💡 Select any company by clicking its row in the leaderboard below, or manually type its name or symbol above.")

    # 4. Interactive Leaderboard Grid
    if not filtered_rows:
        st.info("No offerings match your search criteria.")
    else:
        df_screener = pd.DataFrame([
            {
                "Company & Ticker": r["Company & Ticker"],
                "Status": r["Status"],
                "Bidding Window": r["Bidding Window"],
                "Issue Size": r["Issue Size"],
                "Safety Score": r["Safety Score"] if r["_is_audited"] else None,
                "Flags": r["Flags"] if r["_is_audited"] else None,
                "Verdict": r["Verdict"],
            }
            for r in filtered_rows
        ])

        table_event = st.dataframe(
            df_screener,
            use_container_width=True,
            hide_index=True,
            height=380,
            column_config={
                "Company & Ticker": st.column_config.TextColumn("Company & Ticker", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Bidding Window": st.column_config.TextColumn("Bidding Window", width="small"),
                "Issue Size": st.column_config.TextColumn("Issue Size", width="small"),
                "Safety Score": st.column_config.ProgressColumn(
                    "Safety Score",
                    help="Forensic safety score out of 100",
                    format="%d/100",
                    min_value=0,
                    max_value=100,
                    width="small",
                ),
                "Flags": st.column_config.NumberColumn(
                    "Flags",
                    format="%d 🚩",
                    width="small",
                ),
                "Verdict": st.column_config.TextColumn("Verdict", width="medium"),
            },
            selection_mode="single-row",
            on_select="rerun",
            key="screener_interactive_grid",
        )

        # State Transition & Action Bar on Table Row Selection
        if table_event and table_event.selection and table_event.selection.rows:
            sel_idx = table_event.selection.rows[0]
            if sel_idx < len(filtered_rows):
                selected_row = filtered_rows[sel_idx]
                target_sym = selected_row["_symbol"]
                target_name = selected_row["Company & Ticker"]
                target_is_audited = selected_row["_is_audited"]

                # Ensure inspect box immediately syncs to clicked company
                if st.session_state.get("_last_clicked_table_row") != sel_idx:
                    st.session_state["_last_clicked_table_row"] = sel_idx
                    st.session_state["selected_company"] = target_sym
                    st.session_state["inspect_text_input"] = target_name
                    st.rerun()

                st.write("")
                act_box1, act_box2 = st.columns([3, 1.5])

                if target_is_audited:
                    act_box1.markdown(
                        f"""<div style="background: #151D2E; border: 1px solid #222F49; padding: 10px 16px; border-radius: 8px;">
<b>Selected:</b> {target_name} &nbsp;•&nbsp; <b>Safety Score:</b> <span style="color:#10B981; font-weight:700;">{selected_row['Safety Score']}/100</span> &nbsp;•&nbsp; <b>Status:</b> {selected_row['Status']}
</div>""",
                        unsafe_allow_html=True,
                    )
                    if act_box2.button("🔍 Open Forensic Report →", type="primary", use_container_width=True, key=f"tbl_btn_{target_sym}"):
                        switch_view("🔍 Forensic Deep-Dive", target_company=target_sym)
                else:
                    act_box1.markdown(
                        f"""<div style="background: #151D2E; border: 1px solid #222F49; padding: 10px 16px; border-radius: 8px;">
<b>Selected:</b> {target_name} &nbsp;•&nbsp; <span style="color:#94A3B8;">Pending Forensic Audit</span> &nbsp;•&nbsp; <b>Status:</b> {selected_row['Status']}
</div>""",
                        unsafe_allow_html=True,
                    )
                    if act_box2.button(f"⚡ Audit {target_sym} Now →", type="primary", use_container_width=True, key=f"tbl_audit_{target_sym}"):
                        meta = next((item for item in all_ipos if item["symbol"].upper() == target_sym), None)
                        if not meta:
                            meta = {
                                "symbol": target_sym,
                                "company_name": selected_row["company_name"],
                                "open_date": "Live",
                                "close_date": "Live",
                                "issue_size": selected_row["Issue Size"],
                                "price_band": "Book Building",
                                "peers": [],
                            }
                        new_audit, _ = execute_audit(meta, None, bypass_cache=True)
                        if new_audit:
                            switch_view("🔍 Forensic Deep-Dive", target_company=target_sym)

    # Risk vs. Opportunity Scatter Chart
    st.write("")
    st.markdown("### 📈 Risk vs. Opportunity Matrix")
    st.caption("Safety Score (Capital Integrity) versus Growth Score (Operating Moat & Leverage).")

    if audits_list:
        plot_rows = []
        for a in audits_list:
            plot_rows.append({
                "Company": a["company_name"],
                "Symbol": a["symbol"],
                "Safety Score": a.get("safety_score", 0.0),
                "Growth Score": a.get("growth_score", 0.0),
                "Verdict": a.get("overall_verdict", "HIGH_RISK_SPECULATIVE").replace("_", " ").title(),
                "Expected Return": a.get("expected_listing_return", "0-10%"),
            })
        df_chart = pd.DataFrame(plot_rows)

        fig = px.scatter(
            df_chart,
            x="Growth Score",
            y="Safety Score",
            color="Verdict",
            hover_data=["Company", "Expected Return", "Safety Score", "Growth Score"],
            text="Symbol",
            color_discrete_map={
                "Long Term Compounder": COLOR_GREEN,
                "Apply For Listing Gains": COLOR_BLUE,
                "High Risk Speculative": COLOR_AMBER,
                "Avoid": COLOR_ROSE,
            },
            template="plotly_dark",
        )
        fig.update_traces(textposition="top center", marker=dict(size=13, line=dict(width=1, color="white")))
        fig.add_hline(y=70, line_dash="dot", line_color="#10B981", annotation_text="Institutional Tier (70)")
        fig.add_hline(y=50, line_dash="dash", line_color="#F59E0B", annotation_text="Safety Cutoff (50)")
        fig.add_vline(x=50, line_dash="dash", line_color="#64748B", annotation_text="Moat Threshold (50)")
        fig.update_layout(
            height=380,
            xaxis=dict(range=[0, 105], title="Growth Score (Market Opportunity & Moat)"),
            yaxis=dict(range=[0, 105], title="Safety Score (Capital Integrity & Governance)"),
            margin=dict(l=40, r=40, t=30, b=40),
            plot_bgcolor="#151D2E",
            paper_bgcolor="#0B0F19",
        )
        st.plotly_chart(fig, use_container_width=True)


# =====================================================================
# VIEW 2: 🔍 FORENSIC DEEP-DIVE (MICRO VIEW)
# =====================================================================
elif st.session_state.active_view == "🔍 Forensic Deep-Dive":
    cached_audits = cache_mgr.get_all_audits()
    audited_map = {a["symbol"].upper(): a for a in cached_audits}
    all_ipos = st.session_state.get("available_ipos", [])

    # 1. Prominent Company Selector & Navigation Header Bar
    st.markdown(
        """<div style="font-size: 0.8rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 6px;">
    Target Offering for Deep-Dive Audit:
</div>""",
        unsafe_allow_html=True,
    )

    nav_col1, nav_col2, nav_col3 = st.columns([1.2, 2.2, 2.6])
    with nav_col1:
        if st.button("← Back to Screener", use_container_width=True):
            switch_view("📊 Market Screener")

    # Build comprehensive dropdown options list (audited first with score, then pending)
    options_dict = {}
    for a in cached_audits:
        score_val = int(a.get("safety_score", 0))
        label = f"🟢 {a['company_name']} ({a['symbol']}) — Score: {score_val}/100"
        options_dict[label] = a["symbol"]

    for ipo in all_ipos:
        sym = ipo.get("symbol", "").upper()
        c_name = ipo.get("company_name", "")
        if sym in audited_map or any(are_entities_equivalent(c_name, sym, a["company_name"], a["symbol"]) for a in cached_audits):
            continue
        label = f"⏳ {ipo['company_name']} ({sym}) — [Pending Audit]"
        options_dict[label] = sym

    labels_list = list(options_dict.keys())
    curr_sym = st.session_state.selected_company.upper()

    current_idx = 0
    for idx, lbl in enumerate(labels_list):
        if curr_sym in lbl:
            current_idx = idx
            break

    with nav_col2:
        quick_type_dd = st.text_input(
            "Search Offering",
            placeholder="Type company name or ticker (e.g. NSE)...",
            label_visibility="collapsed",
            key="deep_dive_search_input",
            help="Type any company or symbol and press Enter to jump to its audit",
        )
        if quick_type_dd and quick_type_dd.strip():
            qd = quick_type_dd.strip().lower()
            matched_sym_d = None
            for lbl, sym in options_dict.items():
                if qd == sym.lower():
                    matched_sym_d = sym
                    break
            if not matched_sym_d:
                for lbl, sym in options_dict.items():
                    if qd in lbl.lower() or qd in sym.lower():
                        matched_sym_d = sym
                        break
            if matched_sym_d and matched_sym_d != curr_sym:
                st.session_state.selected_company = matched_sym_d
                st.rerun()

    with nav_col3:
        selected_label = st.selectbox(
            "Select Company",
            labels_list,
            index=current_idx,
            label_visibility="collapsed",
            key="deep_dive_select_box",
        )
        chosen_sym = options_dict.get(selected_label)
        if chosen_sym and chosen_sym != curr_sym:
            st.session_state.selected_company = chosen_sym
            st.rerun()

    # Load current audit
    curr_sym = st.session_state.selected_company.upper()
    current_audit = audited_map.get(curr_sym)
    if not current_audit:
        current_audit = cache_mgr.get_cached_audit(curr_sym)

    # Lookup metadata
    meta = next((item for item in all_ipos if item["symbol"].upper() == curr_sym), None)
    if not meta:
        meta = next((item for item in BENCHMARK_IPOS if item["symbol"].upper() == curr_sym), {})

    # If the offering is pending audit, provide an instant trigger
    if not current_audit:
        company_display_name = meta.get("company_name", curr_sym)
        st.write("")
        st.markdown(
            f"""<div style="background: #151D2E; border: 1px solid #222F49; padding: 24px; border-radius: 8px; text-align: center; margin: 20px 0;">
<div style="font-size: 1.3rem; font-weight: 700; color: #F8FAFC; margin-bottom: 6px;">
    ⏳ Forensic Audit Pending for {company_display_name} ({curr_sym})
</div>
<div style="font-size: 0.9rem; color: #94A3B8; max-width: 600px; margin: 0 auto 16px auto;">
    This offering is tracked in the registry but has not yet undergone the 12-factor forensic rubric evaluation. Click below to run a live audit via Google Gemini.
</div>
</div>""",
            unsafe_allow_html=True,
        )
        p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
        with p_col2:
            if st.button(f"🚀 Run Institutional Forensic Audit for {curr_sym}", type="primary", use_container_width=True):
                if not meta:
                    meta = {"symbol": curr_sym, "company_name": curr_sym, "open_date": "Live", "close_date": "Live", "issue_size": "TBD", "price_band": "TBD", "peers": []}
                new_audit, _ = execute_audit(meta, None, bypass_cache=True)
                if new_audit:
                    st.rerun()
    else:
        audit_data = current_audit.get("audit_data", current_audit)
        company_name = current_audit.get("company_name", audit_data.get("company_name", "Unknown Company"))

        open_d = meta.get("open_date", current_audit.get("open_date", "TBD"))
        close_d = meta.get("close_date", current_audit.get("close_date", "TBD"))
        issue_size = meta.get("issue_size", current_audit.get("issue_size", "TBD"))
        price_band = meta.get("price_band", current_audit.get("price_band", "TBD"))
        lifecycle = get_offering_lifecycle(open_d, close_d, curr_sym)

        # 2. Offering Metadata Ribbon
        st.write("")
        meta_col1, meta_col2 = st.columns([3, 1.2])
        with meta_col1:
            st.markdown(
                f"""<div>
<h2 style="margin: 0; font-size: 1.85rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;">
    {company_name} <span style="font-size: 1.1rem; color: #94A3B8; font-weight: 600;">({curr_sym})</span>
</h2>
<div style="display: flex; gap: 12px; align-items: center; margin-top: 6px; font-size: 0.85rem; color: #94A3B8; flex-wrap: wrap;">
    <span>{render_lifecycle_badge(lifecycle)}</span>
    <span>📅 <b>Dates:</b> {format_bidding_dates(open_d, close_d)}</span>
    <span>💰 <b>Size:</b> {issue_size}</span>
    <span>🏷️ <b>Price:</b> {price_band}</span>
</div>
</div>""",
                unsafe_allow_html=True,
            )

        with meta_col2:
            bypass_toggle = st.checkbox("Bypass Cache", value=False, key="deep_dive_bypass_chk")
            if st.button("⚡ Re-run Audit", type="secondary", use_container_width=True):
                execute_audit(meta if meta else {"symbol": curr_sym, "company_name": company_name}, None, bypass_cache=bypass_toggle)
                st.rerun()

        # Offering Status Notice
        if "RENTOMOJ" in curr_sym:
            st.write("")
            st.warning(
                "ℹ️ **Offering Status Notice**: Rentomojo's public subscription window has concluded (closed Sep 11). "
                "Analysis focused on post-listing valuation, secondary market entry, and capital allocation."
            )
        elif lifecycle == "Closed":
            st.write("")
            st.info(
                f"ℹ️ **Offering Status Notice**: Subscription bidding for {company_name} is closed. Analysis reflects secondary market valuation and governance risks."
            )

        st.write("")

        # 3. Forensic KPI Cards (4 columns)
        safety_score = float(current_audit.get("safety_score", audit_data.get("safety_score", 0.0)))
        scorecard = audit_data.get("scorecard", []) or []
        red_flags_num = sum(
            1 for item in scorecard
            if item.get("status", "").upper() == "RED" or item.get("severity", "").upper() == "CRITICAL"
        )
        verdict = current_audit.get("overall_verdict", audit_data.get("overall_verdict", "HIGH_RISK_SPECULATIVE"))
        div_data = audit_data.get("forum_vs_filing_divergence", {})
        div_verdict = div_data.get("divergence_verdict", "ALIGNED")

        render_decision_ribbon(safety_score, red_flags_num, verdict, div_verdict)

        st.write("")

        # 4. Institutional Executive Brief
        exec_summary = audit_data.get("executive_summary", "No executive summary available.")
        render_executive_brief(exec_summary)

        st.write("")

        # 5. Two-Column Analytical Matrix (Bull vs Bear)
        render_balance_sheet(audit_data.get("pros", []), audit_data.get("cons", []))

        st.write("")

        # 6. Market Sentiment vs. Filing Reality (Divergence Split)
        st.markdown("### 🗣️ Market Sentiment vs. Filing Reality (Divergence Split)")
        crowd_sent = div_data.get("crowd_sentiment", "Retail discussions mirror neutral expectations.")
        filing_real = div_data.get("filing_reality", "Regulatory filings disclose standard corporate caveats.")
        render_divergence_split(crowd_sent, filing_real, div_verdict)

        st.write("")

        # 7. The 12-Factor Categorized Accordion
        st.markdown("### 🔬 The 12-Factor Categorized Forensic Audit")
        st.caption("Grouped into Capital Integrity, Earnings Quality, and Valuation Overhang.")
        render_categorized_12_factor_rubric(scorecard)

        st.write("")
        st.divider()

        # 8. Publication-Quality Institutional PDF Export
        f_col1, f_col2 = st.columns([3, 1.5])
        with f_col1:
            st.markdown("<div style='font-size: 0.95rem; font-weight: 700; color: #F8FAFC;'>Institutional Due Diligence Documentation</div>", unsafe_allow_html=True)
            st.caption("Generate a publication-quality institutional research report (PDF) with full 12-factor scorecards and prospectus citations.")
        with f_col2:
            export_meta = {
                "symbol": curr_sym,
                "company_name": company_name,
                "open_date": open_d,
                "close_date": close_d,
                "issue_size": issue_size,
                "price_band": price_band,
            }
            pdf_bytes = generate_forensic_pdf(audit_data, export_meta)
            st.caption("Includes complete 3-page research note with all 12 factor findings & citations.")
            st.download_button(
                label="📄 Export 3-Page Audit Report (PDF)",
                data=pdf_bytes,
                file_name=f"ProspectusIQ_Audit_{curr_sym}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                key=f"pdf_export_v3_{curr_sym}",
            )
