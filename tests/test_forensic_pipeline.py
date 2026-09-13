"""
Comprehensive Integration and Forensic Pipeline Tests for ProspectusIQ.
"""
import json
import pytest
from pathlib import Path

from config import BENCHMARK_IPOS, FORENSIC_FACTORS, DB_PATH
from core.cache_manager import CacheManager
from core.pdf_processor import PDFProcessor
from core.scraper import IPOScraper, SentimentScraper, ValuationBenchmarker
from core.forensic_engine import ForensicEngine, ForensicAuditReport, ScorecardItem
from core.llm_router import LLMRouter, LLMRoutingException


def test_rubric_factor_weights():
    """Verify all 12 factors sum to 100% (1.0)."""
    assert len(FORENSIC_FACTORS) == 12
    total_weight = sum(f["weight"] for f in FORENSIC_FACTORS)
    assert abs(total_weight - 1.0) < 1e-6


def test_cache_manager_operations(tmp_path):
    """Test SQLite persistence, hash deduplication, and zero token waste."""
    test_db = tmp_path / "test_cache.db"
    cm = CacheManager(db_path=test_db)

    dummy_audit = ForensicEngine.get_benchmark_audit("SWIGGY")
    raw_hash = cm.compute_hash({"test": "data_swiggy"})

    # 1. Save
    saved = cm.save_audit(
        symbol="SWIGGY",
        company_name="Swiggy Limited",
        open_date="2024-11-06",
        close_date="2024-11-08",
        issue_size="₹11,327 Cr",
        price_band="₹371 - ₹390",
        raw_data_hash=raw_hash,
        audit_data=dummy_audit,
    )
    assert saved is True

    # 2. Retrieve with exact hash
    cached = cm.get_cached_audit("SWIGGY", raw_data_hash=raw_hash)
    assert cached is not None
    assert cached["overall_verdict"] == "APPLY_FOR_LISTING_GAINS"
    assert cached["_cached"] is True

    # 3. Retrieve with different hash (should return None for exact match)
    mismatch = cm.get_cached_audit("SWIGGY", raw_data_hash="different_hash")
    assert mismatch is None

    # 4. Fetch all audits for leaderboard
    all_audits = cm.get_all_audits()
    assert len(all_audits) == 1
    assert all_audits[0]["symbol"] == "SWIGGY"


def test_pdf_processor_benchmark_filings():
    """Verify pre-extracted benchmark filings load and have required sections."""
    for symbol in ["SWIGGY", "NSE", "AFCONS"]:
        text = PDFProcessor.get_sample_filing(symbol)
        assert text is not None
        assert len(text) > 1000
        # Check for critical chapters
        assert "OBJECTS OF THE ISSUE" in text or "USE OF PROCEEDS" in text
        assert "RISK FACTORS" in text
        assert "CAPITAL STRUCTURE" in text
        assert "RELATED PARTY TRANSACTIONS" in text
        assert "OUTSTANDING LITIGATIONS" in text


def test_forensic_pydantic_schema():
    """Verify strict adherence to Section 8 JSON Contract."""
    for symbol in ["SWIGGY", "NSE", "AFCONS"]:
        audit = ForensicEngine.get_benchmark_audit(symbol)
        report = ForensicAuditReport(**audit)
        assert report.company_name
        assert 0.0 <= report.safety_score <= 100.0
        assert 0.0 <= report.growth_score <= 100.0
        assert report.overall_verdict in [
            "APPLY_FOR_LISTING_GAINS",
            "LONG_TERM_COMPOUNDER",
            "HIGH_RISK_SPECULATIVE",
            "AVOID",
        ]
        assert report.expected_listing_return in ["NEGATIVE", "0-10%", "10-25%", ">25%"]
        assert len(report.scorecard) == 12
        assert report.forum_vs_filing_divergence.divergence_verdict in [
            "ALIGNED",
            "DANGEROUS_EUPHORIA",
            "UNWARRANTED_PESSIMISM",
        ]


def test_scraper_fault_tolerance():
    """Verify zero-cost scrapers always return valid lists without crashing."""
    # 1. IPO Discovery with infallible fallback
    ipos = IPOScraper.fetch_active_and_upcoming_ipos()
    assert len(ipos) >= 3
    symbols = [item["symbol"] for item in ipos]
    assert "SWIGGY" in symbols
    assert "NSE" in symbols

    # 2. Competitor Valuation Benchmarking
    multiples = ValuationBenchmarker.get_peer_multiples(["INVALID_TICKER_XYZ", "ZOMATO.NS"])
    assert len(multiples) == 2
    for m in multiples:
        assert "trailing_pe" in m
        assert "price_to_book" in m

    # 3. Forum Sentiment Mining
    sentiment = SentimentScraper.get_aggregated_sentiment_text("Swiggy Limited", "SWIGGY")
    assert len(sentiment) > 50


def test_llm_router_benchmark_fallback():
    """Verify LLM Router safely triggers benchmark fallback if all keys unconfigured."""
    result = LLMRouter.generate_json(
        system_prompt="system",
        user_prompt="audit Swiggy",
        symbol_hint="SWIGGY",
        allow_benchmark_fallback=True,
    )
    assert result is not None
    assert result["company_name"] == "Swiggy Limited"
    assert len(result["scorecard"]) == 12


def test_deterministic_safety_score_calculation():
    """Verify weighted score calculation formula."""
    sample_scorecard = [
        {"parameter_id": i, "status": "GREEN", "severity": "LOW"} for i in range(1, 13)
    ]
    all_green_score = ForensicEngine.calculate_deterministic_safety_score(sample_scorecard)
    assert all_green_score == 100.0

    sample_scorecard_red = [
        {"parameter_id": i, "status": "RED", "severity": "MEDIUM"} for i in range(1, 13)
    ]
    all_red_score = ForensicEngine.calculate_deterministic_safety_score(sample_scorecard_red)
    assert all_red_score == 0.0
