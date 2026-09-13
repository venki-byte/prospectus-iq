"""
Batch auditor script to run real-time Gemini Flash-Lite audits for upcoming IPOs.
"""
import logging
from core.cache_manager import CacheManager
from core.llm_router import LLMRouter
from core.forensic_engine import SYSTEM_PROMPT, build_user_prompt
from core.scraper import IPOScraper, SentimentScraper, ValuationBenchmarker

logging.basicConfig(level=logging.INFO)

def run_batch(count=6):
    cm = CacheManager()
    cached_symbols = {a['symbol'].upper() for a in cm.get_all_audits()}
    all_ipos = IPOScraper.fetch_active_and_upcoming_ipos()

    to_audit = [item for item in all_ipos if item['symbol'].upper() not in cached_symbols][:count]
    print(f"Batch auditing {len(to_audit)} pending IPOs via Google Gemini...")

    for item in to_audit:
        sym = item['symbol']
        name = item['company_name']
        print(f"\n[>>>] Auditing {name} ({sym})...")
        forum_text = SentimentScraper.get_aggregated_sentiment_text(name, sym)
        peers = ValuationBenchmarker.get_peer_multiples(item.get('peers', []))
        user_prompt = build_user_prompt(name, item, '', peers, forum_text)

        try:
            audit = LLMRouter.generate_json(SYSTEM_PROMPT, user_prompt, symbol_hint=sym, allow_benchmark_fallback=False)
            raw_hash = cm.compute_hash({'symbol': sym, 'name': name})
            cm.save_audit(
                symbol=sym,
                company_name=name,
                open_date=item.get('open_date', 'TBD'),
                close_date=item.get('close_date', 'TBD'),
                issue_size=item.get('issue_size', 'TBD'),
                price_band=item.get('price_band', 'TBD'),
                raw_data_hash=raw_hash,
                audit_data=audit
            )
            print(f"  [+] Success {name}: Safety Score = {audit.get('safety_score')}, Verdict = {audit.get('overall_verdict')}")
        except Exception as e:
            print(f"  [-] Failed {name}: {e}")

    print("\nBatch audit completed successfully!")

if __name__ == "__main__":
    run_batch(6)
