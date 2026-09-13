"""
Run live audits via Gemini Flash-Lite for benchmark IPOs and store them in ipo_cache.db.
"""
import json
import logging
from config import BENCHMARK_IPOS
from core.cache_manager import CacheManager
from core.forensic_engine import ForensicEngine, SYSTEM_PROMPT, build_user_prompt
from core.llm_router import LLMRouter
from core.pdf_processor import PDFProcessor
from core.scraper import SentimentScraper, ValuationBenchmarker

logging.basicConfig(level=logging.INFO)

def run():
    cm = CacheManager()
    print("Executing live Gemini Flash-Lite audits for benchmark IPOs...")

    for b in BENCHMARK_IPOS:
        sym = b["symbol"]
        name = b["company_name"]
        print(f"\n--- Auditing {name} ({sym}) via Google Gemini ---")

        filing_text = PDFProcessor.get_sample_filing(sym)
        forum_text = SentimentScraper.get_aggregated_sentiment_text(name, sym)
        peers = ValuationBenchmarker.get_peer_multiples(b.get("peers", []))

        user_prompt = build_user_prompt(
            company_name=name,
            metadata=b,
            prospectus_text=filing_text,
            competitor_metrics=peers,
            forum_sentiment=forum_text,
        )

        audit = LLMRouter.generate_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            symbol_hint=sym,
            allow_benchmark_fallback=False,  # strictly use live Gemini!
        )

        raw_hash = cm.compute_hash({
            "symbol": sym,
            "company_name": name,
            "filing_fingerprint": filing_text[:2000] if filing_text else "none",
            "forum_fingerprint": forum_text[:500] if forum_text else "none",
        })

        cm.save_audit(
            symbol=sym,
            company_name=name,
            open_date=b["open_date"],
            close_date=b["close_date"],
            issue_size=b["issue_size"],
            price_band=b["price_band"],
            raw_data_hash=raw_hash,
            audit_data=audit,
        )

        print(f"  [+] Audit persisted for {name}:")
        print(f"      Provider: {audit.get('_provider_used')}")
        print(f"      Safety Score: {audit.get('safety_score')}")
        print(f"      Growth Score: {audit.get('growth_score')}")
        print(f"      Verdict: {audit.get('overall_verdict')}")
        print(f"      Listing Return: {audit.get('expected_listing_return')}")

    print("\nAll benchmark live Gemini audits completed successfully!")

if __name__ == "__main__":
    run()
