"""
Seed the SQLite cache with initial benchmark audits for SWIGGY, NSE, and AFCONS.
Ensures zero demo failure and instantaneous display upon initial application launch.
"""
from config import BENCHMARK_IPOS
from core.cache_manager import CacheManager
from core.forensic_engine import ForensicEngine

def seed_database():
    cm = CacheManager()
    print("Seeding initial benchmark audits into ipo_cache.db...")

    for b in BENCHMARK_IPOS:
        sym = b["symbol"]
        audit = ForensicEngine.get_benchmark_audit(sym)
        raw_hash = cm.compute_hash({"symbol": sym, "benchmark": True, "filing": sym})

        # Save to database
        cm.save_audit(
            symbol=sym,
            company_name=b["company_name"],
            open_date=b["open_date"],
            close_date=b["close_date"],
            issue_size=b["issue_size"],
            price_band=b["price_band"],
            raw_data_hash=raw_hash,
            audit_data=audit,
        )
        print(f"  [+] Cached benchmark audit for {b['company_name']} ({sym})")

    audits = cm.get_all_audits()
    print(f"Database seeded successfully. Total cached records: {len(audits)}")

if __name__ == "__main__":
    seed_database()
