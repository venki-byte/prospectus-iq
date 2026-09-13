"""
Reusable Institutional Terminal UI Components for ProspectusIQ.
"""
from typing import Any, Callable, Dict, List, Optional
import streamlit as st
from ui.styles import (
    COLOR_AMBER,
    COLOR_BLUE,
    COLOR_GREEN,
    COLOR_ROSE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)


def render_verdict_badge(verdict: str) -> str:
    """Returns HTML for an institutional verdict badge."""
    v = (verdict or "").upper()
    if "COMPOUNDER" in v:
        return "<span class='badge-compounder'>🟢 LONG_TERM_COMPOUNDER</span>"
    elif "LISTING" in v:
        return "<span class='badge-listing'>🔵 APPLY_FOR_LISTING_GAINS</span>"
    elif "SPECULATIVE" in v:
        return "<span class='badge-speculative'>🟡 HIGH_RISK_SPECULATIVE</span>"
    elif "AVOID" in v:
        return "<span class='badge-avoid'>🔴 AVOID</span>"
    return "<span class='badge-pending'>⏳ PENDING</span>"


def render_lifecycle_badge(status_str: str) -> str:
    """Returns HTML for offering lifecycle status."""
    s = (status_str or "").lower()
    if "open" in s or "active" in s or "bidding" in s:
        return "<span class='lifecycle-active'>🟢 Open</span>"
    elif "upcoming" in s:
        return "<span class='lifecycle-upcoming'>🟡 Upcoming</span>"
    elif "closed" in s or "finished" in s or "listed" in s:
        return "<span class='lifecycle-closed'>🔴 Closed</span>"
    return f"<span class='lifecycle-upcoming'>{status_str}</span>"


def render_kpi_card(title: str, value: str, subtitle: str = "", value_color: str = COLOR_TEXT_PRIMARY):
    """Renders a single high-density terminal KPI card matching Section 3 spec."""
    html = f"""<div class="terminal-card">
<div class="metric-title">{title}</div>
<div class="metric-value-lg" style="color: {value_color};">{value}</div>
<div class="metric-sub">{subtitle}</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


def render_executive_brief(brief: str):
    """Renders the 3-sentence institutional brief callout card."""
    cleaned_brief = brief.strip() if brief else "No executive brief generated."
    html = f"""<div class="executive-brief-container">
<div class="brief-header">🏛️ Institutional Executive Brief</div>
<div class="brief-text">{cleaned_brief}</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


def render_decision_ribbon(
    safety_score: float,
    red_flags_count: int,
    verdict: str,
    divergence_verdict: str,
):
    """Renders the 4 top decision cards for the deep-dive screen."""
    c1, c2, c3, c4 = st.columns(4)

    # 1. Forensic Quality Score
    score_color = COLOR_GREEN if safety_score >= 70 else (COLOR_AMBER if safety_score >= 50 else COLOR_ROSE)
    tier_label = (
        "Institutional Quality"
        if safety_score >= 70
        else ("Moderate Governance Risk" if safety_score >= 50 else "High Forensic Danger")
    )
    with c1:
        render_kpi_card(
            title="Forensic Quality Score",
            value=f"{int(safety_score)}<span style='font-size:16px; color:{COLOR_TEXT_MUTED};'>/100</span>",
            subtitle=tier_label,
            value_color=score_color,
        )

    # 2. Red Flags Count
    flags_color = COLOR_GREEN if red_flags_count == 0 else (COLOR_AMBER if red_flags_count <= 2 else COLOR_ROSE)
    flags_label = "Clean Filing" if red_flags_count == 0 else ("Governance Anomalies" if red_flags_count <= 2 else "Multiple Critical Warnings")
    with c2:
        render_kpi_card(
            title="Forensic Red Flags",
            value=f"{red_flags_count} <span style='font-size:16px; color:{COLOR_TEXT_MUTED};'>🚩</span>",
            subtitle=flags_label,
            value_color=flags_color,
        )

    # 3. Institutional Recommendation
    with c3:
        st.markdown(
            f"""<div class="terminal-card" style="display:flex; flex-direction:column; justify-content:space-between; min-height:92px;">
<div class="metric-title">Institutional Recommendation</div>
<div style="margin: 4px 0;">{render_verdict_badge(verdict)}</div>
<div class="metric-sub">Capital Allocation Decision</div>
</div>""",
            unsafe_allow_html=True,
        )

    # 4. Market Divergence
    div_clean = (divergence_verdict or "ALIGNED").upper()
    if "EUPHORIA" in div_clean:
        div_title = "Dangerous Euphoria"
        div_color = COLOR_ROSE
        div_sub = "Retail Trap / Speculative Hype"
    elif "PESSIMISM" in div_clean:
        div_title = "Pessimism Overhang"
        div_color = COLOR_GREEN
        div_sub = "Discounted Fundamentals"
    else:
        div_title = "Aligned Realism"
        div_color = COLOR_BLUE
        div_sub = "Consensus Reflects Disclosures"

    with c4:
        render_kpi_card(
            title="Market Divergence",
            value=div_title,
            subtitle=div_sub,
            value_color=div_color,
        )


def render_balance_sheet(pros: List[str], cons: List[str]):
    """Renders the two-column Analytical Matrix."""
    c1, c2 = st.columns(2)

    with c1:
        pros_html = "".join([f"<div class='bullet-item'>• {p}</div>" for p in pros]) if pros else "<div class='bullet-item'>No prominent strengths identified.</div>"
        st.markdown(
            f"""<div class="balance-sheet-bull">
<div class="column-header-bull">🟢 Institutional Bull Thesis (Key Strengths)</div>
{pros_html}
</div>""",
            unsafe_allow_html=True,
        )

    with c2:
        cons_html = "".join([f"<div class='bullet-item'>• {c}</div>" for c in cons]) if cons else "<div class='bullet-item'>No critical red flags recorded.</div>"
        st.markdown(
            f"""<div class="balance-sheet-bear">
<div class="column-header-bear">🔴 Forensic Bear Concerns (Critical Red Flags)</div>
{cons_html}
</div>""",
            unsafe_allow_html=True,
        )


def render_divergence_split(
    crowd_sentiment: str,
    filing_reality: str,
    divergence_verdict: str,
):
    """Renders the Divergence Analyzer split card comparing social media vs DRHP."""
    v_clean = (divergence_verdict or "ALIGNED").upper()
    if "EUPHORIA" in v_clean:
        st.error(
            "🚨 **DANGEROUS EUPHORIA DETECTED**: Retail forum sentiment and grey market excitement are disconnected from underlying prospectus disclosures. High probability of retail liquidity trap!"
        )
    elif "PESSIMISM" in v_clean:
        st.success(
            "💡 **PESSIMISM OVERHANG**: Negative crowd sentiment overlooks fundamental asset backing, defensible margins, and long-term compounding balance sheet strength."
        )
    else:
        st.info(
            "⚖️ **ALIGNED REALISM**: Retail investor discourse reflects disclosures in the regulatory prospectus with measured, objective valuation expectations."
        )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""<div class="divergence-card">
<div class="divergence-header-crowd">💬 What Retail & Forums Believe</div>
<div class="divergence-text">{crowd_sentiment or "No retail consensus available."}</div>
</div>""",
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""<div class="divergence-card">
<div class="divergence-header-filing">📑 What the Prospectus Discloses</div>
<div class="divergence-text">{filing_reality or "No regulatory disclosure recorded."}</div>
</div>""",
            unsafe_allow_html=True,
        )


def render_categorized_12_factor_rubric(scorecard: List[Dict[str, Any]]):
    """
    Renders the 12-factor rubric grouped into 3 structured categories:
    Category A: Capital Integrity (Factors 1-5)
    Category B: Earnings Quality & Moat (Factors 6-8)
    Category C: Valuation & Overhang (Factors 9-12)
    """
    scorecard_map = {item.get("parameter_id", 0): item for item in scorecard}

    categories = [
        {
            "name": "🏛️ Category A: Capital Integrity (Factors 1–5)",
            "factors": [1, 2, 3, 4, 5],
            "description": "50% Category Weight: Use of Proceeds, Pre-IPO Share Disparity, Related-Party Leaks, Litigation Exposure, Share Pledges.",
        },
        {
            "name": "📊 Category B: Earnings Quality & Moat (Factors 6–8)",
            "factors": [6, 7, 8],
            "description": "30% Category Weight: CFO vs. PAT Cash Conversion, Customer Concentration, Operating Margin Trajectory.",
        },
        {
            "name": "⚖️ Category C: Valuation & Overhang (Factors 9–12)",
            "factors": [9, 10, 11, 12],
            "description": "20% Category Weight: Peer P/E Multiples, Regulatory Vulnerability, 30/90 Day Anchor Lock-in Cliff, Whistleblower Insights.",
        },
    ]

    for cat in categories:
        has_critical = any(
            scorecard_map.get(fid, {}).get("status", "").upper() == "RED"
            for fid in cat["factors"]
        )

        with st.expander(f"{cat['name']}", expanded=has_critical):
            st.caption(cat["description"])
            st.write("")

            for fid in cat["factors"]:
                factor = scorecard_map.get(fid)
                if not factor:
                    continue

                pname = factor.get("parameter_name", f"Factor {fid}")
                status = factor.get("status", "YELLOW").upper()
                finding = factor.get("finding", "No analytical finding recorded.")
                evidence = factor.get("evidence_quote", "No filing quote available.")

                if status == "GREEN":
                    status_icon = "🟢"
                elif status == "YELLOW":
                    status_icon = "🟡"
                else:
                    status_icon = "🔴"

                st.markdown(
                    f"""<div class="factor-card">
<div style="font-size: 0.92rem; font-weight: 700; color: #F8FAFC; margin-bottom: 6px;">
    {status_icon} Factor {fid}: {pname}
</div>
<div style="font-size: 0.88rem; color: #CBD5E1; line-height: 1.5; margin-bottom: 6px;">
    <b>Analytical Finding:</b> {finding}
</div>
<div class="evidence-quote-box">
    <b>Prospectus Citation:</b><br>
    "{evidence}"
</div>
</div>""",
                    unsafe_allow_html=True,
                )


def render_system_diagnostics(cached_count: int, on_clear_cache: Optional[Callable] = None):
    """
    Renders the subtle, collapsed bottom footer expander in the sidebar.
    Title: ⚙️ Diagnostics & Storage (clean UTF-8 string, no HTML entity leaks).
    """
    with st.expander("⚙️ Diagnostics & Storage", expanded=False):
        st.markdown(
            """<div style="margin-bottom: 8px;">
<span class="system-status-pill">● Gemini Active</span>
</div>""",
            unsafe_allow_html=True,
        )
        st.caption(f"Persisted Offerings: **{cached_count} Audits Cached**")
        st.caption("Zero-cost deduplication active.")

        if on_clear_cache and st.button("Clear Cache Database", use_container_width=True):
            on_clear_cache()
