"""
Deterministic SQLite Caching and Deduplication Engine for ProspectusIQ.
Ensures zero token waste by caching audits based on symbol and MD5 content hashes.
"""
import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import DB_PATH
from core.entity_resolver import are_entities_equivalent, generate_canonical_symbol

logger = logging.getLogger("prospectus_iq.cache")


class CacheManager:
    """Manages local SQLite persistence and hash-based token preservation."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a sqlite3 connection with Row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Create the ipo_records table and performance indices if they do not exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ipo_records (
                    symbol TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    open_date TEXT,
                    close_date TEXT,
                    issue_size TEXT,
                    price_band TEXT,
                    raw_data_hash TEXT NOT NULL,
                    audit_json TEXT NOT NULL,
                    safety_score REAL DEFAULT 0.0,
                    growth_score REAL DEFAULT 0.0,
                    overall_verdict TEXT DEFAULT '',
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_safety_score ON ipo_records(safety_score);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_growth_score ON ipo_records(growth_score);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_hash ON ipo_records(symbol, raw_data_hash);
            """)
            conn.commit()

    @staticmethod
    def compute_hash(data: Any) -> str:
        """
        Compute an MD5 fingerprint of the combined inputs
        (scraped metadata, prospectus text, forum sentiment).
        """
        if isinstance(data, (dict, list)):
            serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)
        elif isinstance(data, str):
            serialized = data
        elif isinstance(data, bytes):
            return hashlib.md5(data).hexdigest()
        else:
            serialized = str(data)
        return hashlib.md5(serialized.encode("utf-8")).hexdigest()

    def get_cached_audit(
        self, symbol: str, raw_data_hash: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Query ipo_cache.db for an existing record matching symbol and raw_data_hash.
        If raw_data_hash is None, returns the latest record for symbol if present.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if raw_data_hash:
                    cursor.execute(
                        """
                        SELECT audit_json, raw_data_hash, safety_score, growth_score, overall_verdict, last_updated
                        FROM ipo_records
                        WHERE symbol = ? AND raw_data_hash = ?
                        """,
                        (symbol.upper(), raw_data_hash),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT audit_json, raw_data_hash, safety_score, growth_score, overall_verdict, last_updated
                        FROM ipo_records
                        WHERE symbol = ?
                        """,
                        (symbol.upper(),),
                    )

                row = cursor.fetchone()
                if row:
                    audit_dict = json.loads(row["audit_json"])
                    audit_dict["_cached"] = True
                    audit_dict["_cached_at"] = row["last_updated"]
                    audit_dict["_raw_data_hash"] = row["raw_data_hash"]
                    return audit_dict
        except Exception as e:
            logger.error(f"Error reading cache for symbol {symbol}: {e}")
        return None

    def save_audit(
        self,
        symbol: str,
        company_name: str,
        open_date: str,
        close_date: str,
        issue_size: str,
        price_band: str,
        raw_data_hash: str,
        audit_data: Dict[str, Any],
    ) -> bool:
        """
        Store or update an audit record in the database.
        """
        try:
            safety_score = float(audit_data.get("safety_score", 0.0))
            growth_score = float(audit_data.get("growth_score", 0.0))
            overall_verdict = str(audit_data.get("overall_verdict", ""))
            audit_json = json.dumps(audit_data, ensure_ascii=False)
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            target_symbol = (symbol or "").upper().strip()
            if not target_symbol:
                target_symbol = generate_canonical_symbol(company_name)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Cross-check existing records for equivalent entities
                cursor.execute("SELECT symbol, company_name FROM ipo_records")
                existing_rows = cursor.fetchall()
                for row in existing_rows:
                    ex_sym = row["symbol"]
                    ex_name = row["company_name"]
                    if are_entities_equivalent(company_name, target_symbol, ex_name, ex_sym):
                        target_symbol = ex_sym  # Idempotently map to canonical existing symbol
                        break

                # Safeguard: Preserve existing detailed scorecard if incoming audit is partial
                cursor.execute("SELECT audit_json FROM ipo_records WHERE symbol = ?", (target_symbol,))
                existing_entry = cursor.fetchone()
                if existing_entry and existing_entry["audit_json"]:
                    try:
                        old_audit = json.loads(existing_entry["audit_json"])
                        if not audit_data.get("scorecard") and old_audit.get("scorecard"):
                            audit_data["scorecard"] = old_audit["scorecard"]
                        if not audit_data.get("pros") and old_audit.get("pros"):
                            audit_data["pros"] = old_audit["pros"]
                        if not audit_data.get("cons") and old_audit.get("cons"):
                            audit_data["cons"] = old_audit["cons"]
                        if not audit_data.get("forum_vs_filing_divergence") and old_audit.get("forum_vs_filing_divergence"):
                            audit_data["forum_vs_filing_divergence"] = old_audit["forum_vs_filing_divergence"]
                        if not audit_data.get("executive_summary") and old_audit.get("executive_summary"):
                            audit_data["executive_summary"] = old_audit["executive_summary"]
                        audit_json = json.dumps(audit_data, ensure_ascii=False)
                    except Exception:
                        pass

                cursor.execute(
                    """
                    INSERT INTO ipo_records (
                        symbol, company_name, open_date, close_date, issue_size,
                        price_band, raw_data_hash, audit_json, safety_score,
                        growth_score, overall_verdict, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        company_name = excluded.company_name,
                        open_date = excluded.open_date,
                        close_date = excluded.close_date,
                        issue_size = excluded.issue_size,
                        price_band = excluded.price_band,
                        raw_data_hash = excluded.raw_data_hash,
                        audit_json = excluded.audit_json,
                        safety_score = excluded.safety_score,
                        growth_score = excluded.growth_score,
                        overall_verdict = excluded.overall_verdict,
                        last_updated = excluded.last_updated
                    """,
                    (
                        target_symbol,
                        company_name,
                        open_date,
                        close_date,
                        issue_size,
                        price_band,
                        raw_data_hash,
                        audit_json,
                        safety_score,
                        growth_score,
                        overall_verdict,
                        now_iso,
                    ),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to persist audit for {symbol}: {e}")
            return False

    def get_all_audits(self) -> List[Dict[str, Any]]:
        """
        Return all records from ipo_records formatted for the Monitored IPO Leaderboard.
        """
        records: List[Dict[str, Any]] = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT symbol, company_name, open_date, close_date, issue_size,
                           price_band, safety_score, growth_score, overall_verdict,
                           audit_json, last_updated
                    FROM ipo_records
                    ORDER BY safety_score DESC
                    """
                )
                for row in cursor.fetchall():
                    audit_payload = {}
                    try:
                        audit_payload = json.loads(row["audit_json"])
                    except Exception:
                        pass

                    expected_listing_return = audit_payload.get("expected_listing_return", "N/A")
                    records.append(
                        {
                            "symbol": row["symbol"],
                            "company_name": row["company_name"],
                            "open_date": row["open_date"] or "N/A",
                            "close_date": row["close_date"] or "N/A",
                            "issue_size": row["issue_size"] or "N/A",
                            "price_band": row["price_band"] or "N/A",
                            "safety_score": float(row["safety_score"] or 0.0),
                            "growth_score": float(row["growth_score"] or 0.0),
                            "overall_verdict": row["overall_verdict"] or "UNAUDITED",
                            "expected_listing_return": expected_listing_return,
                            "last_updated": row["last_updated"],
                            "audit_data": audit_payload,
                        }
                    )
        except Exception as e:
            logger.error(f"Error fetching all audits: {e}")
        return records

    def delete_audit(self, symbol: str) -> bool:
        """Remove a cached record by symbol."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ipo_records WHERE symbol = ?", (symbol.upper(),))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting audit {symbol}: {e}")
            return False
