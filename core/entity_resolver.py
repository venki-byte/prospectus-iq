"""
ProspectusIQ: Enterprise Entity Resolution & Offering Deduplication Engine.
Guarantees deterministic, idempotent mapping between scraped offerings,
benchmark registries, and cached database audits to prevent duplicate entries.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("prospectus_iq.entity_resolver")

# High-conviction institutional alias registry
KNOWN_ALIASES: Dict[str, str] = {
    "national stock exchange": "NSE",
    "nse": "NSE",
    "swiggy": "SWIGGY",
    "afcons": "AFCONS",
    "afcons infrastructure": "AFCONS",
    "rentomojo": "RENTOMOJ",
    "edunetwork": "RENTOMOJ",
    "hero motors": "HEROMOTO",
    "ntpc green": "NTPCGREE",
    "tata capital": "TATACAPI",
    "hdb financial": "HDBFINAN",
}

# Legal suffixes and filler terms to strip during entity normalization
STOPWORD_PATTERNS = [
    r"\bipo\b",
    r"\blimited\b",
    r"\bltd\b",
    r"\bpvt\b",
    r"\bprivate\b",
    r"\binc\b",
    r"\bincorporated\b",
    r"\bcorp\b",
    r"\bcorporation\b",
    r"\bcompany\b",
    r"\bco\b",
    r"\bholdings\b",
    r"\bgroup\b",
    r"\bindia\b",
    r"\bbharat\b",
]


def normalize_company_name(name: str) -> str:
    """
    Produces a canonical root key from a corporate name by stripping
    parenthetical qualifiers, legal entity suffixes, and punctuation.
    """
    if not name:
        return ""
    clean = str(name).lower()
    
    # Remove parentheticals e.g. (India), (Mom's Belief), (Edunetwork Private Limited)
    clean = re.sub(r"\([^)]*\)", "", clean)
    
    for pattern in STOPWORD_PATTERNS:
        clean = re.sub(pattern, " ", clean, flags=re.IGNORECASE)
        
    # Remove non-alphanumeric chars
    clean = re.sub(r"[^a-z0-9\s]", " ", clean)
    # Collapse multiple spaces
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def generate_canonical_symbol(clean_name: str, fallback_symbol: Optional[str] = None) -> str:
    """
    Generates a deterministic 3 to 8 character ticker symbol from the company's
    canonical root name. Preserves known aliases and authoritative symbols.
    """
    if fallback_symbol and len(fallback_symbol.strip()) >= 2 and fallback_symbol.strip().upper() not in ["TBA", "TBD", "IPO", ""]:
        # If a verified symbol is already provided and not generic
        f_sym = fallback_symbol.strip().upper()
        if f_sym in KNOWN_ALIASES.values():
            return f_sym

    norm = normalize_company_name(clean_name)
    
    # Check known institutional aliases
    for alias, sym in KNOWN_ALIASES.items():
        if alias in norm or norm in alias:
            return sym

    # Generate from normalized brand root
    compact = re.sub(r"[^A-Za-z0-9]", "", norm).upper()
    if compact:
        return compact[:8]

    # Fallback to alphanumeric of raw string
    raw_compact = re.sub(r"[^A-Za-z0-9]", "", clean_name).upper()
    return raw_compact[:8] if raw_compact else "IPO"


def are_entities_equivalent(
    name1: str,
    sym1: str,
    name2: str,
    sym2: str,
) -> bool:
    """
    Determines if two offering records refer to the identical corporate entity.
    Evaluates exact ticker match, canonical name equality, and substring containment.
    """
    s1 = (sym1 or "").upper().strip()
    s2 = (sym2 or "").upper().strip()

    # Exact symbol match (excluding generic placeholders)
    if s1 and s2 and s1 == s2 and s1 not in ["TBA", "TBD", "IPO", "CUSTOM"]:
        return True

    n1 = normalize_company_name(name1)
    n2 = normalize_company_name(name2)

    if not n1 or not n2:
        return False

    # Exact normalized name equality
    if n1 == n2:
        return True

    # Alias cross-check
    for alias in KNOWN_ALIASES:
        if (alias in n1 or n1 in alias) and (alias in n2 or n2 in alias):
            return True

    words1 = n1.split()
    words2 = n2.split()

    # If single-word brands (e.g. Swiggy)
    if len(words1) == 1 and len(words2) == 1:
        if words1[0] == words2[0]:
            return True

    # If multi-word names: check if one is prefix/subset of another
    # Protect against collisions between distinct divisions (e.g. "Manipal Health" vs "Manipal Payment")
    if n1 in n2 or n2 in n1:
        diff = set(words1).symmetric_difference(set(words2))
        generic_qualifiers = {
            "services", "tech", "technology", "technologies",
            "enterprises", "solutions", "cards", "digital", "systems", "infra", "infrastructure"
        }
        if not diff or diff.issubset(generic_qualifiers):
            return True

    return False


def find_equivalent_entity(
    target_name: str,
    target_sym: str,
    entity_list: List[Dict[str, Any]],
) -> Optional[Tuple[int, Dict[str, Any]]]:
    """
    Finds if an entity exists in a list of offerings. Returns (index, entity) or None.
    """
    for idx, item in enumerate(entity_list):
        i_name = item.get("company_name", "")
        i_sym = item.get("symbol", "")
        if are_entities_equivalent(target_name, target_sym, i_name, i_sym):
            return idx, item
    return None


def deduplicate_offerings(
    primary_list: List[Dict[str, Any]],
    incoming_list: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Idempotently merges incoming offerings into primary offerings.
    If an incoming entity already exists in primary, merges updated dates
    without duplicating the row. New offerings are appended with canonical symbols.
    """
    merged = [dict(item) for item in primary_list]

    for inc in incoming_list:
        inc_name = inc.get("company_name", "")
        inc_sym = inc.get("symbol", "")
        canonical_sym = generate_canonical_symbol(inc_name, inc_sym)
        inc["symbol"] = canonical_sym

        match = find_equivalent_entity(inc_name, canonical_sym, merged)
        if match:
            idx, existing = match
            # Merge live date information if incoming has it and existing has placeholders
            if inc.get("open_date") and inc["open_date"] not in ["TBA", "TBD", "Upcoming", ""]:
                existing["open_date"] = inc["open_date"]
            if inc.get("close_date") and inc["close_date"] not in ["TBA", "TBD", ""]:
                existing["close_date"] = inc["close_date"]
            if inc.get("price_band") and inc["price_band"] not in ["TBA", "TBD", "Book Building", ""]:
                existing["price_band"] = inc["price_band"]
            if inc.get("issue_size") and inc["issue_size"] not in ["TBA", "TBD", ""]:
                existing["issue_size"] = inc["issue_size"]
        else:
            merged.append(inc)

    return merged
