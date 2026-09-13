# MASTER SPECIFICATION: ProspectusIQ (Forensic IPO Auditor & Opportunity Screener)

---

## 1. Executive Summary & Core Objective

**ProspectusIQ** is an institutional-grade, zero-API-cost IPO forensic auditor and automated screener. The application bridges the information asymmetry between institutional investment banks and retail investors by evaluating regulatory filings (DRHP, RHP, S-1) and retail forum discussions across 12 weighted forensic parameters.

The software must operate completely on free-tier infrastructure, featuring a resilient multi-provider LLM fallback chain (Google Gemini $\rightarrow$ xAI Grok $\rightarrow$ OpenRouter), deterministic SQLite caching to prevent token waste, and a Streamlit dashboard that ranks active and upcoming IPOs by safety and return potential.

---

## 2. System Architecture & Directory Layout

The project must be structured into modular, decoupled packages:

```text
prospectus_iq/
├── .env.example                  # Environment template for all 3 LLM providers
├── requirements.txt              # Production dependencies
├── config.py                     # Global constants, weights, and rubric definitions
├── core/
│   ├── __init__.py
│   ├── llm_router.py             # Multi-provider failover engine (Gemini -> Grok -> OpenRouter)
│   ├── cache_manager.py          # SQLite persistence and deduplication hash engine
│   ├── scraper.py                # Zero-cost scrapers (IPO calendar, Reddit, DuckDuckGo, yfinance)
│   ├── pdf_processor.py          # Targeted chapter text extractor for DRHP/S-1 filings
│   └── forensic_engine.py       # Master prompt builder, scoring algorithms, and rubric validator
├── data/
│   ├── ipo_cache.db              # SQLite storage for cached audits and IPO registries
│   └── sample_filings/           # Pre-extracted chapter texts for instant offline demonstrations
└── app.py                        # High-density Streamlit executive dashboard

```

---

## 3. Environment & Dependencies

### Environment Variables (`.env.example`)

The system must read credentials from `.env` without crashing if any single key is missing:

* `GEMINI_API_KEY`: Google AI Studio API key (Primary provider).
* `GROK_API_KEY`: xAI API key (Secondary fallback).
* `GROK_BASE_URL`: Base URL for xAI endpoint (default: `[https://api.x.ai/v1](https://api.x.ai/v1)`).
* `GROK_MODEL`: Model identifier for Grok (default: `grok-beta`).
* `OPENROUTER_API_KEY`: OpenRouter API key (Tertiary fallback).
* `OPENROUTER_BASE_URL`: Base URL for OpenRouter (default: `[https://openrouter.ai/api/v1](https://openrouter.ai/api/v1)`).
* `OPENROUTER_MODEL`: Model identifier (default: `meta-llama/llama-3.1-70b-instruct`).

### Required Packages (`requirements.txt`)

* `streamlit`: Executive web dashboard.
* `google-generativeai`: Native SDK for Gemini 1.5 Flash.
* `openai`: Universal client used to connect to Grok and OpenRouter endpoints.
* `duckduckgo-search`: Headless, free search engine query library for forum sentiment extraction.
* `pymupdf`: High-speed local PDF text extraction.
* `yfinance`: Free market data retrieval for listed competitor valuation metrics.
* `beautifulsoup4` & `requests`: Scraping public IPO calendars and web content.
* `pydantic`: Schema enforcement for JSON payloads.
* `python-dotenv`: Environment variable loading.
* `pandas` & `plotly`: Tabular visualization and interactive risk/scorecard graphics.

---

## 4. Multi-Provider Fallback Router Specification (`core/llm_router.py`)

### Core Responsibility

Provide a unified interface `generate_json(system_prompt: str, user_prompt: str) -> dict` that guarantees a valid Python dictionary conforming to the forensic schema, even under provider failure, rate limits, or network timeouts.

### Failover Cascade Order

1. **Primary — Google Gemini 1.5 Flash:**
* Target model: `gemini-1.5-flash`.
* Configuration: Enforce JSON response mime-type (`application/json`).
* Trigger fallback if: Status 429 (Rate Limit Exceeded), Status 402/Quota Exhausted, Timeout (>25s), or Invalid JSON response.


2. **First Fallback — xAI Grok:**
* Client: OpenAI client configured with Grok base URL and API key.
* Target model: Configured via `GROK_MODEL`.
* Configuration: `response_format={"type": "json_object"}`.
* Trigger fallback if: Authentication failure, rate limit, timeout, or empty response.


3. **Second Fallback — OpenRouter:**
* Client: OpenAI client configured with OpenRouter base URL and API key.
* Target model: Free or low-cost models (e.g., Llama 3.1 70B Instruct).
* Configuration: `response_format={"type": "json_object"}`.


4. **Final Exception Handling:**
* If all three fail, raise an explicit custom exception detailing each provider's error log.



---

## 5. Zero-Cost Data Ingestion Engine (`core/scraper.py` & `core/pdf_processor.py`)

All data ingestion must run without paid subscriptions or official social media API tokens.

### A. Active & Upcoming IPO Discovery

* **Target:** Extract active, upcoming, and recently closed listings from public financial aggregation portals (e.g., Chittorgarh or equivalent public IPO tables).
* **Extracted Fields:** Company Name, Market Symbol/Slug, Issue Open Date, Issue Close Date, Price Band, Issue Size (in Crores/Millions), and Issue Type (Book Built / Fixed Price).
* **Network Fault Tolerance:** If scraping fails due to network blocks or anti-bot measures, automatically fall back to an internal hardcoded registry of three real, benchmark IPOs (e.g., National Stock Exchange, Swiggy, Afcons Infrastructure) to ensure zero demo failure.

### B. Forum & Community Sentiment Ingestion

* **Target Platforms:** ValuePickr, Reddit (r/IndiaInvestments, r/wallstreetbets), and Twitter/X sentiment mirrors.
* **Mechanism:**
1. Construct automated search queries using `duckduckgo-search` targeting discussions, red flags, whistleblower remarks, and governance concerns for the specific company name.
2. In parallel, query public Reddit search endpoints using anonymous `.json` URL queries to pull the top 5 most relevant thread titles and comment excerpts.


* **Output:** A cleaned, synthesized block of text combining all community commentary, labeled by source.

### C. Competitor Valuation Benchmarking

* **Target:** Pull live valuation multiples of listed industry peers using `yfinance`.
* **Extracted Metrics:** Trailing P/E, Forward P/E, Price-to-Book (P/B), Return on Equity (ROE), and Operating Profit Margin.

### D. Targeted Prospectus PDF Chapter Ingestion

* **Target:** Regulatory DRHP/S-1 filings are typically 300 to 500 pages. Do NOT ingest the entire document.
* **Mechanism:** Use `pymupdf` to scan the Table of Contents or search for specific headings, extracting only:
* "Objects of the Issue" / "Use of Proceeds"
* "Risk Factors"
* "Capital Structure" & "Shareholding Pattern"
* "Related Party Transactions"
* "Outstanding Litigations and Defaults"


* **Output:** Concatenated plain text representing only the high-risk chapters (under 80,000 tokens).

---

## 6. Deterministic Caching & Token Optimization (`core/cache_manager.py`)

### Database Schema (`data/ipo_cache.db`)

Maintain a local SQLite database with the table `ipo_records`:

* `symbol` (TEXT PRIMARY KEY): Unique identifier of the company.
* `company_name` (TEXT)
* `open_date` (TEXT)
* `close_date` (TEXT)
* `issue_size` (TEXT)
* `price_band` (TEXT)
* `raw_data_hash` (TEXT): MD5 hash of the combined inputs (scraped metadata + extracted text + forum text).
* `audit_json` (TEXT): Serialized JSON response of the forensic audit.
* `safety_score` (REAL): Indexed for sorting (0 to 100).
* `growth_score` (REAL): Indexed for sorting (0 to 100).
* `overall_verdict` (TEXT): Categorical rating.
* `last_updated` (TIMESTAMP): Default current timestamp.

### Token Preservation Logic

* When the user triggers an audit for a selected company:
1. Compute the MD5 fingerprint of the scraped metadata and input text.
2. Query `ipo_cache.db` for an existing record matching both the `symbol` and `raw_data_hash`.
3. If a match exists: Instantly return the cached audit from the database. Make **zero** calls to Gemini, Grok, or OpenRouter.
4. If no match exists: Run the LLM router, store the resulting JSON in the database, and display the new results.



---

## 7. The 12-Factor Forensic Rubric & Scoring Engine (`core/forensic_engine.py`)

The engine audits companies across three core categories containing 12 distinct factors. Each factor possesses an assigned weight and specific penalty criteria.

### Category 1: Capital Integrity (Weight: 50%)

* **Factor 1: Use of Proceeds (Weight: 15%)**
* *Audit Criteria:* Ratio of Fresh Issue (reinvested in business growth) vs. Offer for Sale (promoters/PE exiting).
* *Red Flag:* OFS exceeds 60% of total issue size, or fresh capital is explicitly allocated to repay unsecured loans taken from promoters or sister entities.


* **Factor 2: Pre-IPO Allotment Disparity (Weight: 10%)**
* *Audit Criteria:* Share price paid by promoters, founders, or pre-IPO venture funds in transactions during the preceding 18 months versus the upper IPO price band.
* *Red Flag:* Insiders received shares at a 70%+ discount within the last 12 months with no substantive transformation in business fundamentals.


* **Factor 3: Related-Party Transactions & Siphoning (Weight: 10%)**
* *Audit Criteria:* Volume of sales, purchases, consulting fees, leases, or intellectual property royalties conducted with entities owned by promoters' relatives.
* *Red Flag:* Recurring royalties or uncollateralized loans funneling out to promoter-held private partnerships.


* **Factor 4: Outstanding Litigations & Contingent Liabilities (Weight: 10%)**
* *Audit Criteria:* Total value of disputed tax demands, criminal allegations, or civil litigations against promoters and key subsidiaries measured against the company's tangible net worth.
* *Red Flag:* Quantifiable litigation exposure exceeds 20% of net worth, or active criminal proceedings question managerial integrity.


* **Factor 5: Promoter Holding & Pledge Status (Weight: 5%)**
* *Audit Criteria:* Post-issue promoter shareholding percentage and percentage of existing promoter shares encumbered or pledged to lenders.
* *Red Flag:* Post-IPO promoter holding drops below 30%, or any portion of promoter shares is pledged to financial institutions.



### Category 2: Earnings Quality & Moat (Weight: 30%)

* **Factor 6: CFO vs. PAT Divergence (Weight: 10%)**
* *Audit Criteria:* Comparison of Cash Flow from Operations (CFO) versus Profit After Tax (PAT) over the past 3 fiscal years.
* *Red Flag:* PAT shows consistent growth while CFO is negative or declining, signaling aggressive revenue booking and uncollected trade receivables (surging Days Sales Outstanding).


* **Factor 7: Customer & Supplier Concentration (Weight: 10%)**
* *Audit Criteria:* Percentage of total revenue generated by the Top 1, Top 3, and Top 5 clients; dependence on single-geography suppliers.
* *Red Flag:* Top 3 customers account for over 45% of total revenue with short-term, cancellable contracts.


* **Factor 8: Operating Margin Stability & Pricing Power (Weight: 10%)**
* *Audit Criteria:* Operating EBITDA margin trajectory over 3 years in the face of raw material inflation.
* *Red Flag:* Margin compression exceeding 300 basis points year-over-year, indicating inability to pass on costs.



### Category 3: Market, Valuation & Sentiment (Weight: 20%)

* **Factor 9: Valuation Multiple vs. Listed Peers (Weight: 10%)**
* *Audit Criteria:* IPO P/E, Price-to-Book (P/B), and EV/EBITDA compared against profitable, established listed peers.
* *Red Flag:* Asking valuation demands a 40%+ premium over market leaders without demonstrating superior return on equity (ROE).


* **Factor 10: Regulatory & Government Policy Vulnerability (Weight: 5%)**
* *Audit Criteria:* Reliance on government subsidies, special tax holidays, regulatory licenses, or exposure to looming regulatory tariff caps.
* *Red Flag:* Core revenue stream subject to active regulatory crackdowns (e.g., financial brokerage fee caps, environmental zoning mandates).


* **Factor 11: Anchor Lock-In Expiry Supply Cliff (Weight: 2.5%)**
* *Audit Criteria:* Total volume of shares allocated to anchor investors subject to 30-day (50%) and 90-day (remaining 50%) mandatory lock-in expiries.
* *Red Flag:* Massive anchor allotment volume relative to average daily trading volume, signaling high probability of steep price correction on Day 31.


* **Factor 12: Forum Sentiment vs. Prospectus Reality (Weight: 2.5%)**
* *Audit Criteria:* Divergence between retail speculative hype (e.g., high unofficial grey-market premiums) and skeptical warnings uncovered by analysts in financial forums.
* *Red Flag:* High social media enthusiasm coupled with specific, factual warnings on investor boards regarding corporate governance or past promoter bankruptcy history.



---

## 8. JSON Contract Specification & System Prompt

The LLM Router must enforce this exact JSON response schema from all three providers:

```json
{
  "company_name": "string",
  "safety_score": 0.0,
  "growth_score": 0.0,
  "overall_verdict": "APPLY_FOR_LISTING_GAINS | LONG_TERM_COMPOUNDER | HIGH_RISK_SPECULATIVE | AVOID",
  "expected_listing_return": "NEGATIVE | 0-10% | 10-25% | >25%",
  "executive_summary": "string (3 precise sentences synthesizing the business, safety, and valuation)",
  "pros": [
    "string (key operational or financial strength with data citation)"
  ],
  "cons": [
    "string (critical governance, valuation, or structural red flag with data citation)"
  ],
  "scorecard": [
    {
      "parameter_id": 1,
      "parameter_name": "Use of Proceeds",
      "category": "Capital Integrity",
      "status": "GREEN | YELLOW | RED",
      "finding": "string (1-2 sentence analytical summary with concrete numbers)",
      "evidence_quote": "string (verbatim quote or specific citation from prospectus or forum)",
      "severity": "LOW | MEDIUM | CRITICAL"
    }
  ],
  "forum_vs_filing_divergence": {
    "crowd_sentiment": "string (summary of retail consensus from Reddit/ValuePickr)",
    "filing_reality": "string (what the prospectus disclosures actually reveal)",
    "divergence_verdict": "ALIGNED | DANGEROUS_EUPHORIA | UNWARRANTED_PESSIMISM"
  }
}

```

---

## 9. Streamlit User Interface Specification (`app.py`)

The web dashboard must feature an intuitive, high-density layout organized into logical functional blocks.

### A. Global Control Bar & Trigger

* **Header:** Professional title ("⚖️ ProspectusIQ — Autonomous IPO Forensic Screener") with subtitle and current timestamp.
* **Controls Layout (3 columns):**
* *Column 1:* Dropdown selector containing all discovered active and upcoming IPOs, plus an option to manually enter a ticker or company name.
* *Column 2:* Date indicators showing the issue's opening date, closing date, and current status (e.g., "Active", "Closes in 2 Days", "Upcoming").
* *Column 3:* Primary action button ("Run Forensic Audit") and secondary toggle ("Force Live Refresh — Bypass Cache").



### B. Monitored IPO Leaderboard (Overview Tab)

* A comprehensive data table at the top or in Tab 1 displaying all audited IPOs stored in the SQLite cache.
* **Columns:** Company Name, Overall Verdict, Safety Score (0–100), Growth Score (0–100), Est. Listing Gain, Issue Size, Open Date, Close Date.
* **Dynamic Sorting Controls:** Allow user to sort the leaderboard by:
1. *Safety Score (Highest to Lowest)*
2. *Expected Listing Gain (Highest to Lowest)*
3. *Close Date (Earliest to Latest — Urgency view)*


* **Visual Status Badges:** Display verdicts using colored indicators:
* 🟢 Green: `LONG_TERM_COMPOUNDER`
* 🔵 Blue: `APPLY_FOR_LISTING_GAINS`
* 🟡 Amber: `HIGH_RISK_SPECULATIVE`
* 🔴 Red: `AVOID`



### C. Detailed IPO Audit Drilldown (Active Company Tab)

When an IPO is selected and audited, render the following sections:

1. **Executive Scorecard Cards (4 metrics across top):**
* *Safety Score:* Value / 100 with label indicating level of governance risk.
* *Growth Score:* Value / 100 representing market opportunity and operating leverage.
* *Overall Verdict:* Formal investment recommendation badge.
* *Expected Return:* Categorical projection for listing day.


2. **Executive Brief:** A clean callout box containing the 3-sentence institutional summary.
3. **Pros & Cons Matrix:** A balanced two-column container displaying structural strengths on the left and forensic red flags on the right.
4. **12-Factor Forensic Accordion:**
* Twelve collapsible panels, each representing one of the rubric parameters.
* Panel title features an icon reflecting status (🟢, 🟡, 🔴), the parameter name, category tag, and severity tag.
* Inside each panel: display the concrete analytical finding, followed by a highlighted quote block containing the exact evidence quote from the filing or forum source.


5. **Crowd Sentiment vs. Filing Reality (Divergence Analyzer):**
* A side-by-side comparison container:
* *Left:* "What the Crowd & Forums Believe" (retail hype, Grey Market Premium expectations).
* *Right:* "What the Prospectus Disclosures Actually Reveal" (the hidden liabilities, OFS percentages, or litigation).
* *Verdict:* Banner stating whether the market is experiencing "Dangerous Euphoria" or "Aligned Realism".





### D. Educational Documentation Tab ("Forensic Methodology")

A dedicated documentation view explaining the complete evaluation framework to judges and retail users:

* Explanation of each of the 12 factors.
* Formula breakdown of how the 50% Capital Integrity, 30% Earnings Quality, and 20% Valuation weighting calculates the final Safety Score.
* Clear guidance on why Offer for Sale (OFS), related-party royalties, and CFO-PAT divergence are the three biggest destroyers of retail wealth in new listings.

---

## 10. CLI Agent Implementation Guidelines & Edge Cases

When the automated CLI reads this specification, it must adhere to these exact constraints:

1. **Deterministic Error Handling in Ingestion:**
* If `yfinance` fails to fetch peer multiples for a specific ticker, the script must populate default `"N/A"` strings rather than allowing an unhandled exception to interrupt the pipeline.
* If DuckDuckGo search hits rate limits, fail gracefully by returning an empty string and allowing the audit to proceed using filing text alone.


2. **Strict JSON Parsing:**
* Strip any markdown wrapping (e.g., `json ... `) from the LLM responses before passing to `json.loads()` to ensure complete compatibility across all three providers.


3. **Responsive UI State:**
* Store current audit results in Streamlit's `st.session_state` so interacting with widgets (sorting tables, opening accordions) does not cause the page to reload or re-query the LLM.


4. **Zero-Code Hallucination:**
* Implement real API client calls using standard official library conventions. Do not use deprecated endpoints. Ensure SQLite transactions are committed and connections are closed properly using context managers.