# MASTER SPECIFICATION: ProspectusIQ (UI/UX Terminal Polish & Interactive Fixes)

Save this file as `UI_REPAIR_SPEC.md` and pass it directly to `agy cli`. It provides exact root-cause resolutions, styling constraints, and state-machine logic to eliminate all UI defects shown in the current deployment.

---

## 1. Visual Bug Audit & Root-Cause Analysis

The current build exhibits five critical UI/UX defects that break usability:

| Defect Observed in Screenshots | Root Cause | Architectural Fix |
| --- | --- | --- |
| **1. Broken Table Selection & Truncation** | Default light-theme `st.dataframe` or static HTML table with auto-truncated text columns (`Closed / List`, `Active Biddi`). Clicking rows does nothing. | Implement Streamlit native interactive dataframe with `selection_mode="single-row"` and `on_select="rerun"`. Add explicit column configurations (`width`, `ProgressColumn`). Map row clicks directly to `st.session_state.selected_company` and trigger an immediate view switch to `deep_dive`. |
| **2. Clashing White-on-Dark Elements** | Missing scoped theme inheritance; Streamlit text inputs, search boxes, and table containers are defaulting to `#FFFFFF` background with illegible grey/white text. | Inject an aggressive, dark-mode CSS override targeting all `.stTextInput`, `.stSelectbox`, `.stDataFrame`, and table containers with `#151D2E` background and `#F8FAFC` high-contrast typography. |
| **3. Dark-on-Dark Invisible Sidebar Labels** | Checkbox and filter text (`Hide High Risk`, `Active Listings Only`) inherit Streamlit's secondary muted color (`#475569`), which is invisible against `#0B0F19`. | Force CSS override on `div[data-testid="stCheckbox"] label` to `#E2E8F0` with `font-weight: 500`. |
| **4. Raw Icon String Glitches (`_arrow_right`)** | Attempting to use non-standard Markdown or HTML entity strings inside `st.expander()` or sidebar labels (`_arrow_right Custom Filing`). | Replace all text-encoded icon entities with standard native UTF-8 symbols (e.g., `📁 Custom Filing`, `⚙️ Diagnostics`). |
| **5. Header Masking in Deep Dive** | Top navigation contains an unstyled empty text box/container next to the back button. | Replace the entire header with a clean, two-column layout: Left = `← Back to Screener` button; Right = Clean status badge pill. |

---

## 2. Updated Project File Structure

```text
prospectus_iq/
├── .env                          # API Keys
├── requirements.txt              # Ensure streamlit>=1.35.0
├── config.py                     # Visual theme tokens & thresholds
├── core/
│   ├── llm_router.py             # Silent multi-provider engine
│   ├── cache_manager.py          # SQLite persistence
│   ├── scraper.py                # Data collection pipelines
│   └── forensic_engine.py       # Prompt & JSON scoring
├── ui/
│   ├── styles.py                 # Scoped High-Contrast CSS injection
│   └── components.py             # Interactive Dataframe & metric builders
└── app.py                        # Clean 2-screen state orchestrator
```

---

## 3. Global CSS Architecture (`ui/styles.py`)

The application must inject the following CSS rules on every rerun to enforce an institutional terminal appearance:

```css
/* Deep Slate Terminal Theme Override */
.stApp {
    background-color: #0B0F19 !important;
    color: #F8FAFC !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

/* Sidebar styling and dark-label visibility */
section[data-testid="stSidebar"] {
    background-color: #0F172A !important;
    border-right: 1px solid #1E293B !important;
}
section[data-testid="stSidebar"] div[data-testid="stCheckbox"] label span p {
    color: #E2E8F0 !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}
section[data-testid="stSidebar"] .stRadio label span p {
    color: #F8FAFC !important;
    font-weight: 500 !important;
}

/* Eliminate white background bleed on inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background-color: #1E293B !important;
    color: #F8FAFC !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #6366F1 !important;
    box-shadow: none !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color: #64748B !important;
}

/* Table / Dataframe Dark Terminal Integration */
div[data-testid="stDataFrame"] {
    background-color: #151D2E !important;
    border: 1px solid #222F49 !important;
    border-radius: 8px !important;
    padding: 4px !important;
}
div[data-testid="stDataFrame"] div[data-testid="glide-cell"] {
    color: #F8FAFC !important;
}

/* High-Contrast Metric Cards */
.terminal-card {
    background-color: #151D2E;
    border: 1px solid #222F49;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
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
}
.metric-sub {
    font-size: 12px;
    color: #64748B;
    margin-top: 2px;
}

/* Clean Button States */
button[kind="primary"] {
    background-color: #6366F1 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}
button[kind="secondary"] {
    background-color: #1E293B !important;
    color: #E2E8F0 !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
}
button[kind="secondary"]:hover {
    border-color: #6366F1 !important;
    color: #FFFFFF !important;
}
```

---

## 4. Interactive Table Architecture (`ui/components.py`)

### The Row-Click Navigation Engine

The table must not be a passive display. It must act as the primary navigation system:

1. **Native Streamlit Event Listening:**
Use `st.dataframe` configured with `selection_mode="single-row"` and `on_select="rerun"`.
2. **Column Configuration Rules:**
* **Company & Ticker:** `st.column_config.TextColumn("Company & Ticker", width="medium")`
* **Status:** `st.column_config.TextColumn("Status", width="small")` (Formatted as clean labels: `Open`, `Upcoming`, `Closed`)
* **Bidding Dates:** `st.column_config.TextColumn("Bidding Window", width="small")` (Formatted as concise dates: `Sep 16 - Sep 18`)
* **Issue Size:** `st.column_config.TextColumn("Issue Size", width="small")`
* **Safety Score:** `st.column_config.ProgressColumn("Safety Score", format="%d/100", min_value=0, max_value=100, width="small")`
* **Red Flags:** `st.column_config.NumberColumn("Flags", format="%d 🚩", width="small")`
* **Verdict:** `st.column_config.TextColumn("Verdict", width="medium")`


3. **State Transition Handler:**
```python
# Detect row click event:
if table_event.selection and table_event.selection.rows:
    selected_index = table_event.selection.rows[0]
    selected_company_name = filtered_df.iloc[selected_index]["company_name"]
    st.session_state.selected_company = selected_company_name
    st.session_state.active_view = "deep_dive"
    st.rerun()
```


4. **Fallback Dropdown Selector:**
Include a compact selector immediately above the table: *"Quick Inspect Company:"* with an *"Open Report →"* button. This provides a secondary, fail-safe path to navigate to the deep-dive view if a user prefers clicking a standard button over selecting a table row.

---

## 5. Screen-by-Screen Layout Specifications

### A. Minimalist Sidebar

* **Branding:**
* Header: `⚖️ ProspectusIQ`
* Subtitle: `Institutional Terminal`


* **Navigation Control:**
* Render an `st.radio` control with two options:
* `📊 Market Screener`
* `🔍 Forensic Deep-Dive`


* Bound directly to `st.session_state.active_view`.


* **Screener Filters Container:**
* `st.checkbox("Hide High Risk (<50 Score)")`
* `st.checkbox("Active Listings Only")`


* **Bottom Diagnostics Expander:**
* Title: `⚙️ Diagnostics & Storage` (clean UTF-8 string, no HTML entity leaks).
* Contains engine health (`● Gemini Active`), cached company count, and a `Clear Cache Database` button.


---

### B. View 1: Market Screener (`📊 Market Screener`)

1. **Top Macro KPI Bar (4 horizontal cards):**
* *Tracked IPOs:* Total count of offerings detected.
* *Institutional Grade:* Count of offerings with Safety Score $\ge 70$.
* *High-Risk Offerings:* Count of offerings with Safety Score $< 50$.
* *Open for Bidding:* Count of currently active issues.


2. **Search and Action Bar (3 columns):**
* *Column 1 (Search):* `st.text_input` with placeholder *"Search company or symbol..."*.
* *Column 2 (Sort):* `st.selectbox` with options: *Safety Score (High to Low)*, *Issue Size (High to Low)*, *Close Date (Urgent)*.
* *Column 3 (Action):* `st.button("⚡ Scan for New IPOs", type="primary", use_container_width=True)`.


3. **Interactive Leaderboard Grid:**
* Render the configured interactive `st.dataframe`.
* Include a sub-caption: *"💡 Click any row to open the complete 12-factor institutional forensic report."*


---

### C. View 2: Forensic Deep-Dive (`🔍 Forensic Deep-Dive`)

1. **Navigation & Offering Status Ribbon:**
* Left Column: `st.button("← Back to Screener")` $\rightarrow$ Sets `active_view = "screener"` and calls `st.rerun()`.
* Right Column: Direct Company Dropdown to allow switching companies without navigating back.


2. **Offering Metadata Ribbon:**
* Display Company Name and Ticker in large typography (`## Swiggy Limited (SWIGGY)`).
* Badges in a single horizontal row: `[Status: Closed/Listed]` | `[Dates: Nov 06 - Nov 08]` | `[Size: ₹11,327 Cr]` | `[Price: ₹371 - ₹390]`.
* Checkbox on the right: `Bypass Cache & Re-run Audit`.


3. **Forensic KPI Cards (4 columns):**
* Card 1: **Forensic Quality Score** (Large bold score out of 100, colored green if $>70$, yellow if $50-69$, red if $<50$).
* Card 2: **Forensic Red Flags** (Number of critical warnings detected with badge).
* Card 3: **Institutional Recommendation** (Colored badge: `LONG_TERM_COMPOUNDER`, `APPLY_FOR_LISTING_GAINS`, `HIGH_RISK_SPECULATIVE`, `AVOID`).
* Card 4: **Market Divergence** (Indicator: `Aligned Realism`, `Dangerous Euphoria`, `Pessimism Overhang`).


4. **Institutional Executive Brief:**
* High-contrast card containing the 3-sentence summary of business viability, governance risk, and verdict.


5. **Two-Column Analytical Matrix:**
* Column 1: `🟢 Institutional Bull Thesis (Key Strengths)` $\rightarrow$ Bulleted list with concrete numbers and citations.
* Column 2: `🔴 Forensic Bear Concerns (Critical Red Flags)` $\rightarrow$ Bulleted list with explicit governance/debt warnings.


6. **Market Sentiment vs. Filing Reality (Divergence Split):**
* Split card showing *What Retail/Forums Believe* vs. *What the Prospectus Discloses*.


7. **The 12-Factor Categorized Accordion:**
Organize factors into three structured collapsible sections:
* **Category A: Capital Integrity (Factors 1–5):** Use of Proceeds, Pre-IPO Share Disparity, Related-Party Leaks, Litigation Exposure, Share Pledges.
* **Category B: Earnings Quality & Moat (Factors 6–8):** CFO vs. PAT Cash Conversion, Customer Concentration, Operating Margin Trajectory.
* **Category C: Valuation & Overhang (Factors 9–12):** Peer P/E Multiples, Regulatory Vulnerability, 30/90 Day Anchor Lock-in Cliff, Whistleblower Insights.
* Each item displays an icon (`🟢`, `🟡`, `🔴`), a 1-sentence analytical finding, and a highlighted quote box citing the exact section of the prospectus.


---

## 6. Implementation Directives for `agy cli`

1. **State Preservation Guarantee:**
Ensure `st.session_state` keys (`active_view`, `selected_company`, `search_term`) are initialized at the very top of `app.py` before any widget renders to prevent state resets during clicks.
2. **Zero Light-Mode Fallback:**
Apply background color `#0B0F19` directly to `st.set_page_config()` or inject the CSS block as the first rendered element in `app.py`.
3. **Handle Empty Search/Filter States:**
If the search query yields 0 rows, display a clean callout box: *"No offerings match your search criteria"* instead of breaking the dataframe component.
4. **Remove Glitched Entity Strings:**
Search the entire repository for `_arrow_right`, `:arrow_right:`, or malformed markdown strings and replace them with clean UTF-8 emojis or clean text labels.
