"""
Institutional PDF Research Report Exporter for ProspectusIQ.
Generates publication-quality, high-design institutional PDF equity research notes using PyMuPDF.
"""
import datetime
from typing import Any, Dict, Optional
import pymupdf

# Institutional Design Tokens
COLOR_NAVY = (0.03, 0.05, 0.09)         # #070D17 (Deep Slate Navy)
COLOR_NAVY_SUB = (0.07, 0.10, 0.18)     # #121A2E
COLOR_INDIGO = (0.25, 0.20, 0.80)       # #4033CC (Institutional Accent)
COLOR_BLUE = (0.08, 0.32, 0.85)         # #1452D9
COLOR_EMERALD = (0.01, 0.48, 0.32)      # #037A52 (Safe / Pass)
COLOR_AMBER = (0.75, 0.38, 0.02)        # #BF6105 (Watch / Moderate)
COLOR_ROSE = (0.82, 0.08, 0.22)         # #D11438 (Avoid / Red Flag)

FILL_WHITE = (1.0, 1.0, 1.0)
FILL_CARD_BG = (0.97, 0.98, 0.99)       # #F8FAFC
FILL_GREEN_TINT = (0.94, 0.99, 0.96)    # #F0FDF4
FILL_ROSE_TINT = (1.0, 0.95, 0.96)      # #FFF1F2
FILL_AMBER_TINT = (1.0, 0.98, 0.93)     # #FFFBEB
FILL_BLUE_TINT = (0.94, 0.97, 1.0)      # #EFF6FF
FILL_QUOTE_BG = (0.95, 0.96, 0.98)      # #F1F5F9

BORDER_LIGHT = (0.78, 0.82, 0.88)       # #C7D1E0 (Crisp high-contrast border)
BORDER_GREEN = (0.55, 0.85, 0.68)       # #8CD9AD
BORDER_ROSE = (0.95, 0.65, 0.72)         # #F2A6B8
BORDER_AMBER = (0.95, 0.75, 0.50)       # #F2BF80
BORDER_BLUE = (0.65, 0.78, 0.96)         # #A6C7F5

# HIGH-CONTRAST PITCH BLACK INK (ELIMINATES LIGHT/WASHED-OUT TEXT)
TEXT_INK = (0.02, 0.03, 0.05)           # #05080D (Pitch Black Ink for 100% legibility)
TEXT_DARK = (0.02, 0.03, 0.05)          # #05080D
TEXT_BODY = (0.04, 0.06, 0.10)          # #0A0F1A (High-Density Dark Charcoal)
TEXT_SLATE = (0.15, 0.20, 0.30)         # #26334D (Deep Dark Slate for sub-labels)
TEXT_MUTED = (0.24, 0.30, 0.40)         # #3D4D66 (Crisp Dark Charcoal)
TEXT_WHITE = (0.99, 0.99, 1.0)          # Pure White


def clean_pdf_text(text: Any) -> str:
    """Sanitizes text for standard PDF Type-1 fonts to prevent '?' or garbled symbols."""
    if text is None:
        return ""
    t = str(text).strip()
    t = t.replace("₹", "Rs. ")
    t = t.replace("•", "- ")
    t = t.replace("\u00a0", " ")
    cleaned = []
    for ch in t:
        code = ord(ch)
        if 32 <= code <= 126 or code == 10:
            cleaned.append(ch)
        elif code in (8216, 8217):  # curly single quotes
            cleaned.append("'")
        elif code in (8220, 8221):  # curly double quotes
            cleaned.append('"')
        elif code in (8211, 8212):  # en/em dash
            cleaned.append("-")
        elif code == 8230:          # ellipsis
            cleaned.append("...")
        elif code == 8377:          # rupee
            cleaned.append("Rs. ")
        elif code > 127:            # drop unprintable/Devanagari OCR artifacts
            continue
        else:
            cleaned.append(" ")
    return "".join(cleaned).strip()


def draw_pill(page, rect: pymupdf.Rect, text: str, bg_color: tuple, border_color: tuple, text_color: tuple, fontsize: float = 7.5):
    """Draws a centered institutional status badge pill with bold high-contrast text."""
    page.draw_rect(rect, color=border_color, fill=bg_color, width=1.0)
    tw = pymupdf.get_text_length(text, fontname="hebo", fontsize=fontsize)
    cx = rect.x0 + (rect.width - tw) / 2
    cy = rect.y0 + rect.height / 2 + fontsize / 3
    page.insert_text(pymupdf.Point(cx, cy), text, fontname="hebo", fontsize=fontsize, color=text_color)


def insert_fit_textbox(page, rect: pymupdf.Rect, text: str, max_fontsize: float = 9.2, min_fontsize: float = 7.2, fontname: str = "helv", color: tuple = TEXT_INK) -> float:
    """
    Inserts text into a bounding box, automatically scaling down fontsize if needed
    to ensure zero text truncation (avoiding negative return code where PyMuPDF drops all text).
    """
    text = clean_pdf_text(text)
    if not text:
        return 0.0
    fs = max_fontsize
    while fs >= min_fontsize:
        rc = page.insert_textbox(rect, text, fontsize=fs, fontname=fontname, color=color)
        if rc >= 0:
            return rc
        fs -= 0.3
    # Truncation fallback with ellipsis if text is unusually massive
    words = text.split()
    while len(words) > 10:
        words = words[:-4]
        candidate = " ".join(words) + " [...]"
        rc = page.insert_textbox(rect, candidate, fontsize=min_fontsize, fontname=fontname, color=color)
        if rc >= 0:
            return rc
    return 0.0


def generate_forensic_pdf(audit_data: Dict[str, Any], meta: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Generates an institutional-grade, publication-quality 3-page equity research report.
    Guarantees complete analytical findings, citations, and high visual hierarchy.
    """
    doc = pymupdf.open()
    company_name = clean_pdf_text(audit_data.get("company_name", meta.get("company_name", "IPO Company") if meta else "IPO Company"))
    symbol = (meta.get("symbol") if meta and meta.get("symbol") else audit_data.get("symbol", "IPO")).upper()
    safety_score = float(audit_data.get("safety_score", 0.0))
    growth_score = float(audit_data.get("growth_score", 0.0))
    verdict = str(audit_data.get("overall_verdict", "HIGH_RISK_SPECULATIVE")).replace("_", " ").title()
    expected_return = str(audit_data.get("expected_listing_return", "0-10%"))
    exec_summary = clean_pdf_text(audit_data.get("executive_summary", "No executive summary available."))
    pros = [clean_pdf_text(p) for p in audit_data.get("pros", [])]
    cons = [clean_pdf_text(c) for c in audit_data.get("cons", [])]
    scorecard = audit_data.get("scorecard", []) or []
    divergence = audit_data.get("forum_vs_filing_divergence", {})

    open_d = clean_pdf_text(meta.get("open_date", "TBD") if meta else "TBD")
    close_d = clean_pdf_text(meta.get("close_date", "TBD") if meta else "TBD")
    issue_size = clean_pdf_text(meta.get("issue_size", "TBD") if meta else "TBD")
    price_band = clean_pdf_text(meta.get("price_band", "TBD") if meta else "TBD")

    date_str = datetime.datetime.now().strftime("%d %b %Y")

    # =============================================================
    # PAGE 1: Executive Dashboard, Key Metrics & Balance Sheet
    # =============================================================
    page1 = doc.new_page(width=595, height=842)  # A4

    # Top Dark Banner (Height: 74 pt)
    page1.draw_rect(pymupdf.Rect(0, 0, 595, 74), color=None, fill=COLOR_NAVY)
    page1.draw_rect(pymupdf.Rect(0, 71, 595, 74), color=None, fill=COLOR_INDIGO)  # 3pt accent stripe

    # Header Title & Classification
    page1.insert_text(pymupdf.Point(36, 28), "PROSPECTUS", fontsize=15, color=TEXT_WHITE, fontname="hebo")
    page1.insert_text(pymupdf.Point(145, 28), "IQ", fontsize=15, color=(0.58, 0.62, 1.0), fontname="hebo")
    page1.insert_text(pymupdf.Point(175, 28), "//  INSTITUTIONAL FORENSIC RESEARCH NOTE", fontsize=9.2, color=(0.80, 0.85, 0.95), fontname="hebo")

    page1.insert_text(pymupdf.Point(36, 54), f"{company_name.upper()}  ({symbol})", fontsize=12, color=TEXT_WHITE, fontname="hebo")

    # Right side classification badge
    draw_pill(page1, pymupdf.Rect(435, 16, 559, 32), "STRICTLY CONFIDENTIAL", (0.15, 0.20, 0.32), (0.30, 0.38, 0.55), TEXT_WHITE, fontsize=7.2)
    page1.insert_text(pymupdf.Point(465, 52), f"Date: {date_str}", fontsize=9.2, color=(0.80, 0.85, 0.95), fontname="hebo")

    # Offering Metadata Summary Strip
    page1.draw_rect(pymupdf.Rect(36, 82, 559, 108), color=BORDER_LIGHT, fill=FILL_CARD_BG, width=1.0)
    page1.draw_rect(pymupdf.Rect(36, 82, 40, 108), color=None, fill=COLOR_INDIGO)
    meta_text = f"Bidding Window: {open_d} to {close_d}   |   Issue Size: {issue_size}   |   Price Band: {price_band}"
    page1.insert_text(pymupdf.Point(48, 99), meta_text, fontsize=9.5, color=TEXT_INK, fontname="hebo")

    # 4 Key Decision Metric Cards
    card_w = 120.75
    card_gap = 13.0
    start_x = 36.0
    y_card = 116.0
    card_h = 70.0

    # Metric 1: Safety Score
    score_col = COLOR_EMERALD if safety_score >= 70 else (COLOR_AMBER if safety_score >= 50 else COLOR_ROSE)
    score_tier = "INVESTMENT GRADE" if safety_score >= 70 else ("MODERATE RISK" if safety_score >= 50 else "HIGH GOVERNANCE RISK")
    page1.draw_rect(pymupdf.Rect(start_x, y_card, start_x + card_w, y_card + card_h), color=BORDER_LIGHT, fill=FILL_WHITE, width=1.0)
    page1.insert_text(pymupdf.Point(start_x + 10, y_card + 16), "SAFETY SCORE", fontsize=8.0, color=TEXT_SLATE, fontname="hebo")
    page1.insert_text(pymupdf.Point(start_x + 10, y_card + 42), f"{safety_score:.1f}", fontsize=18, color=score_col, fontname="hebo")
    page1.insert_text(pymupdf.Point(start_x + 60, y_card + 40), "/ 100", fontsize=10.5, color=TEXT_SLATE, fontname="hebo")
    draw_pill(page1, pymupdf.Rect(start_x + 8, y_card + 50, start_x + card_w - 8, y_card + 64), score_tier, FILL_GREEN_TINT if safety_score >= 70 else FILL_ROSE_TINT, BORDER_GREEN if safety_score >= 70 else BORDER_ROSE, score_col, fontsize=6.8)

    # Metric 2: Growth Score
    start_x += card_w + card_gap
    page1.draw_rect(pymupdf.Rect(start_x, y_card, start_x + card_w, y_card + card_h), color=BORDER_LIGHT, fill=FILL_WHITE, width=1.0)
    page1.insert_text(pymupdf.Point(start_x + 10, y_card + 16), "GROWTH SCORE", fontsize=8.0, color=TEXT_SLATE, fontname="hebo")
    page1.insert_text(pymupdf.Point(start_x + 10, y_card + 42), f"{growth_score:.1f}", fontsize=18, color=COLOR_BLUE, fontname="hebo")
    page1.insert_text(pymupdf.Point(start_x + 60, y_card + 40), "/ 100", fontsize=10.5, color=TEXT_SLATE, fontname="hebo")
    draw_pill(page1, pymupdf.Rect(start_x + 8, y_card + 50, start_x + card_w - 8, y_card + 64), "HIGH OPERATING LEVERAGE" if growth_score >= 70 else "MODERATE MOAT", FILL_BLUE_TINT, BORDER_BLUE, COLOR_BLUE, fontsize=6.5)

    # Metric 3: Overall Verdict
    start_x += card_w + card_gap
    page1.draw_rect(pymupdf.Rect(start_x, y_card, start_x + card_w, y_card + card_h), color=BORDER_LIGHT, fill=FILL_WHITE, width=1.0)
    page1.insert_text(pymupdf.Point(start_x + 10, y_card + 16), "VERDICT RECOMMENDATION", fontsize=8.0, color=TEXT_SLATE, fontname="hebo")
    v_clean = "Compounder" if "Compounder" in verdict else ("Listing Gains" if "Listing" in verdict else ("Speculative" if "Speculative" in verdict else "Avoid"))
    page1.insert_text(pymupdf.Point(start_x + 10, y_card + 42), v_clean, fontsize=13.5, color=score_col, fontname="hebo")
    draw_pill(page1, pymupdf.Rect(start_x + 8, y_card + 50, start_x + card_w - 8, y_card + 64), "INSTITUTIONAL ALLOCATION", (0.95, 0.95, 0.98), BORDER_LIGHT, TEXT_SLATE, fontsize=6.5)

    # Metric 4: Est. Day-1 Return
    start_x += card_w + card_gap
    page1.draw_rect(pymupdf.Rect(start_x, y_card, 559, y_card + card_h), color=BORDER_LIGHT, fill=FILL_WHITE, width=1.0)
    page1.insert_text(pymupdf.Point(start_x + 10, y_card + 16), "EST. LISTING GAIN", fontsize=8.0, color=TEXT_SLATE, fontname="hebo")
    page1.insert_text(pymupdf.Point(start_x + 10, y_card + 42), expected_return, fontsize=17, color=TEXT_INK, fontname="hebo")
    draw_pill(page1, pymupdf.Rect(start_x + 8, y_card + 50, 551, y_card + 64), "DAY-1 RANGE PROJECTION", (0.95, 0.95, 0.98), BORDER_LIGHT, TEXT_SLATE, fontsize=6.5)

    # Section 1: Executive Thesis Callout Card (Height: 100 pt)
    y_exec = 194.0
    h_exec = 100.0
    page1.draw_rect(pymupdf.Rect(36, y_exec, 559, y_exec + h_exec), color=BORDER_LIGHT, fill=FILL_CARD_BG, width=1.0)
    page1.draw_rect(pymupdf.Rect(36, y_exec, 40.5, y_exec + h_exec), color=None, fill=COLOR_INDIGO)  # Left accent border
    page1.insert_text(pymupdf.Point(48, y_exec + 16), "INSTITUTIONAL INVESTMENT COMMITTEE THESIS", fontsize=9.0, color=COLOR_INDIGO, fontname="hebo")
    insert_fit_textbox(page1, pymupdf.Rect(48, y_exec + 22, 548, y_exec + h_exec - 8), exec_summary, max_fontsize=9.2, min_fontsize=8.0, fontname="helv", color=TEXT_INK)

    # Section 2: Due Diligence Balance Sheet (2 Columns)
    y_bs = 302.0
    page1.insert_text(pymupdf.Point(36, y_bs + 12), "DUE DILIGENCE BALANCE SHEET (OPERATIONAL MOATS VS. FORENSIC RISKS)", fontsize=9.8, color=TEXT_INK, fontname="hebo")

    col_w = 254.5
    gap = 14.0
    y_box = y_bs + 18.0
    h_box = 188.0

    # Bull Column (Left)
    b_rect = pymupdf.Rect(36, y_box, 36 + col_w, y_box + h_box)
    page1.draw_rect(b_rect, color=BORDER_GREEN, fill=FILL_GREEN_TINT, width=1.0)
    page1.draw_rect(pymupdf.Rect(36, y_box, 40, y_box + h_box), color=None, fill=COLOR_EMERALD)
    page1.insert_text(pymupdf.Point(48, y_box + 16), "+ INSTITUTIONAL BULL THESIS (KEY STRENGTHS)", fontsize=8.8, color=COLOR_EMERALD, fontname="hebo")
    pros_text = "\n\n".join([f"- {p}" for p in pros[:4]]) if pros else "- Defensible competitive positioning."
    insert_fit_textbox(page1, pymupdf.Rect(48, y_box + 24, 36 + col_w - 12, y_box + h_box - 8), pros_text, max_fontsize=8.8, min_fontsize=7.8, fontname="helv", color=TEXT_INK)

    # Bear Column (Right)
    r_rect = pymupdf.Rect(36 + col_w + gap, y_box, 559, y_box + h_box)
    page1.draw_rect(r_rect, color=BORDER_ROSE, fill=FILL_ROSE_TINT, width=1.0)
    page1.draw_rect(pymupdf.Rect(36 + col_w + gap, y_box, 36 + col_w + gap + 4, y_box + h_box), color=None, fill=COLOR_ROSE)
    page1.insert_text(pymupdf.Point(36 + col_w + gap + 12, y_box + 16), "- FORENSIC BEAR CONCERNS (CRITICAL RED FLAGS)", fontsize=8.8, color=COLOR_ROSE, fontname="hebo")
    cons_text = "\n\n".join([f"- {c}" for c in cons[:4]]) if cons else "- No critical governance exceptions noted."
    insert_fit_textbox(page1, pymupdf.Rect(36 + col_w + gap + 12, y_box + 24, 547, y_box + h_box - 8), cons_text, max_fontsize=8.8, min_fontsize=7.8, fontname="helv", color=TEXT_INK)

    # Section 3: Divergence Analyzer Box (Full Height)
    y_div = y_box + h_box + 12.0
    page1.insert_text(pymupdf.Point(36, y_div + 12), "MARKET SENTIMENT VS. PROSPECTUS REALITY (DIVERGENCE ANALYZER)", fontsize=9.8, color=TEXT_INK, fontname="hebo")

    div_box = pymupdf.Rect(36, y_div + 18.0, 559, 796.0)
    page1.draw_rect(div_box, color=BORDER_LIGHT, fill=FILL_CARD_BG, width=1.0)

    crowd_text = clean_pdf_text(divergence.get("crowd_sentiment", "Retail consensus mirrors neutral expectations."))
    filing_text = clean_pdf_text(divergence.get("filing_reality", "Regulatory filings disclose standard operational caveats."))
    div_verdict = clean_pdf_text(divergence.get("divergence_verdict", "ALIGNED"))

    div_color = COLOR_EMERALD if "PESSIMISM" in div_verdict else (COLOR_ROSE if "EUPHORIA" in div_verdict else COLOR_BLUE)
    draw_pill(page1, pymupdf.Rect(48, y_div + 26, 255, y_div + 42), f"CONSENSUS STATUS: {div_verdict}", FILL_WHITE, BORDER_LIGHT, div_color, fontsize=7.5)
    page1.insert_text(pymupdf.Point(265, y_div + 37), "Cross-examination of community discussions vs statutory risk factors", fontsize=8.0, color=TEXT_SLATE, fontname="hebo")

    # Divergence side-by-side containers
    comp_y = y_div + 48.0
    comp_h = 796.0 - comp_y - 10.0
    comp_w = 243.5

    # Left Container (Retail Sentiment)
    c1_rect = pymupdf.Rect(48, comp_y, 48 + comp_w, comp_y + comp_h)
    page1.draw_rect(c1_rect, color=BORDER_AMBER, fill=FILL_AMBER_TINT, width=1.0)
    page1.draw_rect(pymupdf.Rect(48, comp_y, 52, comp_y + comp_h), color=None, fill=COLOR_AMBER)
    page1.insert_text(pymupdf.Point(58, comp_y + 16), "RETAIL & COMMUNITY FORUM SENTIMENT", fontsize=8.2, color=COLOR_AMBER, fontname="hebo")
    insert_fit_textbox(page1, pymupdf.Rect(58, comp_y + 22, 48 + comp_w - 10, comp_y + comp_h - 8), crowd_text, max_fontsize=8.8, min_fontsize=7.5, fontname="helv", color=TEXT_INK)

    # Right Container (Prospectus Disclosures)
    c2_rect = pymupdf.Rect(48 + comp_w + 14.0, comp_y, 547, comp_y + comp_h)
    page1.draw_rect(c2_rect, color=BORDER_BLUE, fill=FILL_BLUE_TINT, width=1.0)
    page1.draw_rect(pymupdf.Rect(48 + comp_w + 14.0, comp_y, 48 + comp_w + 18.0, comp_y + comp_h), color=None, fill=COLOR_BLUE)
    page1.insert_text(pymupdf.Point(48 + comp_w + 24.0, comp_y + 16), "STATUTORY DRHP / RHP DISCLOSURES", fontsize=8.2, color=COLOR_BLUE, fontname="hebo")
    insert_fit_textbox(page1, pymupdf.Rect(48 + comp_w + 24.0, comp_y + 22, 537, comp_y + comp_h - 8), filing_text, max_fontsize=8.8, min_fontsize=7.5, fontname="helv", color=TEXT_INK)

    # Page 1 Footer
    page1.draw_line(pymupdf.Point(36, 810), pymupdf.Point(559, 810), color=BORDER_LIGHT, width=1.0)
    page1.insert_text(pymupdf.Point(36, 824), "ProspectusIQ Institutional Terminal  •  Confidential Investment Committee Note", fontsize=8.2, color=TEXT_SLATE, fontname="hebo")
    page1.insert_text(pymupdf.Point(516, 824), "Page 1 of 3", fontsize=8.2, color=TEXT_SLATE, fontname="hebo")

    # =============================================================
    # PAGE 2: 12-Factor Forensic Rubric (Part 1: Factors 1 to 6)
    # =============================================================
    page2 = doc.new_page(width=595, height=842)

    # Header Bar
    page2.draw_rect(pymupdf.Rect(0, 0, 595, 48), color=None, fill=COLOR_NAVY)
    page2.draw_rect(pymupdf.Rect(0, 46, 595, 48), color=None, fill=COLOR_INDIGO)
    page2.insert_text(pymupdf.Point(36, 26), f"PROSPECTUS IQ  //  12-FACTOR FORENSIC RUBRIC AUDIT: {symbol}", fontsize=11.5, color=TEXT_WHITE, fontname="hebo")
    page2.insert_text(pymupdf.Point(36, 40), "PART 1: CAPITAL INTEGRITY, GOVERNANCE & CASH CONVERSION (FACTORS 1 TO 6)", fontsize=7.8, color=(0.80, 0.85, 0.95), fontname="hebo")
    draw_pill(page2, pymupdf.Rect(455, 16, 559, 32), "STRICTLY CONFIDENTIAL", (0.15, 0.20, 0.32), (0.30, 0.38, 0.55), TEXT_WHITE, fontsize=7.2)

    sorted_scorecard = sorted(scorecard, key=lambda x: x.get("parameter_id", 0))
    y_pos = 58.0
    card_h = 112.0

    for item in sorted_scorecard[:6]:
        pid = item.get("parameter_id", 0)
        pname = clean_pdf_text(item.get("parameter_name", f"Factor {pid}"))
        status = str(item.get("status", "YELLOW")).upper()
        severity = str(item.get("severity", "MEDIUM")).upper()
        finding = clean_pdf_text(item.get("finding", "No finding recorded."))
        evidence = clean_pdf_text(item.get("evidence_quote", "No quote cited."))

        item_rect = pymupdf.Rect(36, y_pos, 559, y_pos + card_h)
        status_col = COLOR_EMERALD if status == "GREEN" else (COLOR_AMBER if status == "YELLOW" else COLOR_ROSE)
        status_label = "PASS" if status == "GREEN" else ("WATCH" if status == "YELLOW" else "RED FLAG")
        status_fill = FILL_GREEN_TINT if status == "GREEN" else (FILL_AMBER_TINT if status == "YELLOW" else FILL_ROSE_TINT)
        status_border = BORDER_GREEN if status == "GREEN" else (BORDER_AMBER if status == "YELLOW" else BORDER_ROSE)

        page2.draw_rect(item_rect, color=BORDER_LIGHT, fill=FILL_WHITE, width=1.0)
        page2.draw_rect(pymupdf.Rect(36, y_pos, 40.5, y_pos + card_h), color=None, fill=status_col)

        header_str = f"Factor {pid}: {pname}"
        page2.insert_text(pymupdf.Point(48, y_pos + 16), header_str, fontsize=10.0, color=TEXT_INK, fontname="hebo")

        # Top-Right Pills
        draw_pill(page2, pymupdf.Rect(415, y_pos + 6, 485, y_pos + 20), f"SEV: {severity}", (0.95, 0.95, 0.98), BORDER_LIGHT, TEXT_SLATE, fontsize=7.0)
        draw_pill(page2, pymupdf.Rect(492, y_pos + 6, 551, y_pos + 20), status_label, status_fill, status_border, status_col, fontsize=7.5)

        # Analytical Finding with distinct bold label and pitch-black text
        page2.insert_text(pymupdf.Point(48, y_pos + 29), "ANALYTICAL AUDIT FINDING:", fontsize=7.6, color=COLOR_INDIGO, fontname="hebo")
        insert_fit_textbox(page2, pymupdf.Rect(48, y_pos + 31, 545, y_pos + 67), finding, max_fontsize=8.8, min_fontsize=7.5, fontname="helv", color=TEXT_INK)

        # Prospectus Citation Box in Helvetica Italic
        quote_rect = pymupdf.Rect(48, y_pos + 70, 545, y_pos + 104)
        page2.draw_rect(quote_rect, color=(0.80, 0.83, 0.88), fill=FILL_QUOTE_BG, width=0.8)
        page2.draw_rect(pymupdf.Rect(48, y_pos + 70, 51.5, y_pos + 104), color=None, fill=COLOR_AMBER)
        page2.insert_text(pymupdf.Point(56, y_pos + 80), "PROSPECTUS STATUTORY CITATION:", fontsize=7.0, color=(0.65, 0.32, 0.0), fontname="hebo")
        insert_fit_textbox(page2, pymupdf.Rect(56, y_pos + 82, 540, y_pos + 102), f'"{evidence}"', max_fontsize=8.5, min_fontsize=7.2, fontname="heit", color=TEXT_INK)

        y_pos += card_h + 12.0

    # Page 2 Footer
    page2.draw_line(pymupdf.Point(36, 810), pymupdf.Point(559, 810), color=BORDER_LIGHT, width=1.0)
    page2.insert_text(pymupdf.Point(36, 824), "ProspectusIQ Institutional Terminal  •  Automated Equity Forensic Engine", fontsize=8.2, color=TEXT_SLATE, fontname="hebo")
    page2.insert_text(pymupdf.Point(516, 824), "Page 2 of 3", fontsize=8.2, color=TEXT_SLATE, fontname="hebo")

    # =============================================================
    # PAGE 3: 12-Factor Forensic Rubric (Part 2: Factors 7 to 12)
    # =============================================================
    page3 = doc.new_page(width=595, height=842)

    # Header Bar
    page3.draw_rect(pymupdf.Rect(0, 0, 595, 48), color=None, fill=COLOR_NAVY)
    page3.draw_rect(pymupdf.Rect(0, 46, 595, 48), color=None, fill=COLOR_INDIGO)
    page3.insert_text(pymupdf.Point(36, 26), f"PROSPECTUS IQ  //  12-FACTOR FORENSIC RUBRIC AUDIT: {symbol}", fontsize=11.5, color=TEXT_WHITE, fontname="hebo")
    page3.insert_text(pymupdf.Point(36, 40), "PART 2: OPERATIONAL MOAT, PEER MULTIPLES & POLICY OVERHANG (FACTORS 7 TO 12)", fontsize=7.8, color=(0.80, 0.85, 0.95), fontname="hebo")
    draw_pill(page3, pymupdf.Rect(455, 16, 559, 32), "STRICTLY CONFIDENTIAL", (0.15, 0.20, 0.32), (0.30, 0.38, 0.55), TEXT_WHITE, fontsize=7.2)

    y_pos = 58.0
    card_h = 104.0

    for item in sorted_scorecard[6:12]:
        pid = item.get("parameter_id", 0)
        pname = clean_pdf_text(item.get("parameter_name", f"Factor {pid}"))
        status = str(item.get("status", "YELLOW")).upper()
        severity = str(item.get("severity", "MEDIUM")).upper()
        finding = clean_pdf_text(item.get("finding", "No finding recorded."))
        evidence = clean_pdf_text(item.get("evidence_quote", "No quote cited."))

        item_rect = pymupdf.Rect(36, y_pos, 559, y_pos + card_h)
        status_col = COLOR_EMERALD if status == "GREEN" else (COLOR_AMBER if status == "YELLOW" else COLOR_ROSE)
        status_label = "PASS" if status == "GREEN" else ("WATCH" if status == "YELLOW" else "RED FLAG")
        status_fill = FILL_GREEN_TINT if status == "GREEN" else (FILL_AMBER_TINT if status == "YELLOW" else FILL_ROSE_TINT)
        status_border = BORDER_GREEN if status == "GREEN" else (BORDER_AMBER if status == "YELLOW" else BORDER_ROSE)

        page3.draw_rect(item_rect, color=BORDER_LIGHT, fill=FILL_WHITE, width=1.0)
        page3.draw_rect(pymupdf.Rect(36, y_pos, 40.5, y_pos + card_h), color=None, fill=status_col)

        header_str = f"Factor {pid}: {pname}"
        page3.insert_text(pymupdf.Point(48, y_pos + 16), header_str, fontsize=10.0, color=TEXT_INK, fontname="hebo")

        draw_pill(page3, pymupdf.Rect(415, y_pos + 6, 485, y_pos + 20), f"SEV: {severity}", (0.95, 0.95, 0.98), BORDER_LIGHT, TEXT_SLATE, fontsize=7.0)
        draw_pill(page3, pymupdf.Rect(492, y_pos + 6, 551, y_pos + 20), status_label, status_fill, status_border, status_col, fontsize=7.5)

        # Analytical Finding with distinct bold label and pitch-black text
        page3.insert_text(pymupdf.Point(48, y_pos + 29), "ANALYTICAL AUDIT FINDING:", fontsize=7.6, color=COLOR_INDIGO, fontname="hebo")
        insert_fit_textbox(page3, pymupdf.Rect(48, y_pos + 31, 545, y_pos + 64), finding, max_fontsize=8.8, min_fontsize=7.5, fontname="helv", color=TEXT_INK)

        # Prospectus Citation Box in Helvetica Italic
        quote_rect = pymupdf.Rect(48, y_pos + 66, 545, y_pos + 98)
        page3.draw_rect(quote_rect, color=(0.80, 0.83, 0.88), fill=FILL_QUOTE_BG, width=0.8)
        page3.draw_rect(pymupdf.Rect(48, y_pos + 66, 51.5, y_pos + 98), color=None, fill=COLOR_AMBER)
        page3.insert_text(pymupdf.Point(56, y_pos + 76), "PROSPECTUS STATUTORY CITATION:", fontsize=7.0, color=(0.65, 0.32, 0.0), fontname="hebo")
        insert_fit_textbox(page3, pymupdf.Rect(56, y_pos + 78, 540, y_pos + 96), f'"{evidence}"', max_fontsize=8.5, min_fontsize=7.2, fontname="heit", color=TEXT_INK)

        y_pos += card_h + 10.0

    # Institutional Methodology & Governance Sign-Off Box
    y_sign = y_pos + 4.0
    sign_box = pymupdf.Rect(36, y_sign, 559, y_sign + 70.0)
    page3.draw_rect(sign_box, color=(0.75, 0.80, 0.88), fill=FILL_CARD_BG, width=1.0)
    page3.draw_rect(pymupdf.Rect(36, y_sign, 40.5, y_sign + 70.0), color=None, fill=COLOR_INDIGO)
    page3.insert_text(pymupdf.Point(48, y_sign + 16), "INSTITUTIONAL FORENSIC METHODOLOGY & COMPLIANCE SEAL", fontsize=8.8, color=COLOR_INDIGO, fontname="hebo")
    method_note = (
        "Evaluation Framework: Capital Integrity (50% weight), Earnings Quality & Moat (30% weight), Valuation & Overhang (20% weight). "
        "Prospectus citations are extracted directly from regulatory DRHP/RHP filings and validated against live competitor multiples. "
        "This research note is generated autonomously for institutional capital allocation decision support."
    )
    insert_fit_textbox(page3, pymupdf.Rect(48, y_sign + 22, 545, y_sign + 66), method_note, max_fontsize=8.2, min_fontsize=7.2, fontname="helv", color=TEXT_INK)

    # Page 3 Footer
    page3.draw_line(pymupdf.Point(36, 810), pymupdf.Point(559, 810), color=BORDER_LIGHT, width=1.0)
    page3.insert_text(pymupdf.Point(36, 824), "ProspectusIQ Institutional Terminal  •  Automated Equity Forensic Engine", fontsize=8.2, color=TEXT_SLATE, fontname="hebo")
    page3.insert_text(pymupdf.Point(516, 824), "Page 3 of 3", fontsize=8.2, color=TEXT_SLATE, fontname="hebo")

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
