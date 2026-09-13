"""
Targeted Chapter PDF Text Extractor for DRHP / RHP / S-1 Filings.
Uses PyMuPDF (fitz) to selectively extract high-risk sections to stay under token limits.
"""
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

from config import SAMPLE_FILINGS_DIR

logger = logging.getLogger("prospectus_iq.pdf")

TARGET_SECTION_PATTERNS = {
    "Objects of the Issue": [
        r"objects\s+of\s+the\s+issue",
        r"use\s+of\s+proceeds",
        r"requirements\s+of\s+funds",
    ],
    "Risk Factors": [
        r"risk\s+factors",
        r"internal\s+risk\s+factors",
        r"external\s+risk\s+factors",
    ],
    "Capital Structure": [
        r"capital\s+structure",
        r"shareholding\s+pattern",
        r"share\s+capital\s+history",
    ],
    "Related Party Transactions": [
        r"related\s+party\s+transactions",
        r"transactions\s+with\s+promoters",
    ],
    "Outstanding Litigations and Defaults": [
        r"outstanding\s+litigations?\s+and\s+defaults?",
        r"legal\s+and\s+other\s+information",
        r"material\s+litigations?",
        r"contingent\s+liabilities",
    ],
}

# 80,000 tokens ~= 320,000 characters
MAX_EXTRACT_CHARS = 320000


class PDFProcessor:
    """Extracts targeted high-risk chapters from prospectus filings."""

    @staticmethod
    def get_sample_filing(symbol: str) -> Optional[str]:
        """Load pre-extracted benchmark text for instant offline demonstrations."""
        sym_clean = symbol.strip().upper()
        sample_file = SAMPLE_FILINGS_DIR / f"{sym_clean}.txt"
        if sample_file.exists():
            try:
                return sample_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to read sample filing for {symbol}: {e}")
        return None

    @classmethod
    def extract_targeted_sections_from_pdf(
        cls,
        pdf_source: Union[str, Path, bytes],
        max_chars: int = MAX_EXTRACT_CHARS,
    ) -> Dict[str, str]:
        """
        Extract only the critical forensic sections from a PDF file.
        Returns a dict mapping section name to extracted text.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF (fitz) is not installed. PDF extraction unavailable.")
            return {"error": "PyMuPDF not installed in current environment."}

        doc = None
        try:
            if isinstance(pdf_source, (str, Path)):
                doc = fitz.open(str(pdf_source))
            elif isinstance(pdf_source, bytes):
                doc = fitz.open(stream=pdf_source, filetype="pdf")
            else:
                return {"error": "Invalid PDF source format."}

            num_pages = len(doc)
            toc = doc.get_toc(simple=True)  # [[lvl, title, page], ...]
            section_pages: Dict[str, List[int]] = {sec: [] for sec in TARGET_SECTION_PATTERNS}

            # Strategy 1: Check Table of Contents bookmarks
            if toc:
                for idx, entry in enumerate(toc):
                    title = entry[1]
                    page_num = entry[2] - 1  # 0-indexed
                    if 0 <= page_num < num_pages:
                        for sec_name, patterns in TARGET_SECTION_PATTERNS.items():
                            for pattern in patterns:
                                if re.search(pattern, title, re.IGNORECASE):
                                    # Determine page range until next entry or max 25 pages
                                    next_page = num_pages
                                    if idx + 1 < len(toc):
                                        next_page = min(num_pages, max(page_num + 1, toc[idx + 1][2] - 1))
                                    # Cap each section to at most 30 pages to prevent bloat
                                    end_page = min(page_num + 30, next_page)
                                    section_pages[sec_name].extend(range(page_num, end_page))
                                    break

            # Strategy 2: If TOC missing or empty sections, scan headings in pages
            for sec_name, pages in section_pages.items():
                if not pages:
                    patterns = TARGET_SECTION_PATTERNS[sec_name]
                    # Scan first 60 pages (TOC & intro) and sampling thereafter
                    for p in range(min(num_pages, 80)):
                        page_text = doc[p].get_text("text")
                        first_lines = "\n".join(page_text.split("\n")[:10])
                        for pat in patterns:
                            if re.search(pat, first_lines, re.IGNORECASE):
                                # Found section start
                                section_pages[sec_name].extend(range(p, min(num_pages, p + 25)))
                                break
                        if section_pages[sec_name]:
                            break

            # Extract and concatenate text per section
            extracted_sections: Dict[str, str] = {}
            total_chars = 0

            for sec_name, pages in section_pages.items():
                if not pages:
                    continue
                pages_sorted = sorted(list(set(pages)))
                sec_text_parts = []
                for p in pages_sorted:
                    if p < num_pages:
                        page_txt = doc[p].get_text("text")
                        sec_text_parts.append(f"--- Page {p+1} ---\n{page_txt}")
                        total_chars += len(page_txt)
                        if total_chars >= max_chars:
                            break
                extracted_sections[sec_name] = "\n".join(sec_text_parts)
                if total_chars >= max_chars:
                    break

            # If no sections matched explicitly, extract pages 1 to 40 (standard summary section)
            if not extracted_sections:
                logger.info("No section patterns matched; extracting initial summary pages 1-40.")
                sec_text_parts = []
                for p in range(min(num_pages, 40)):
                    page_txt = doc[p].get_text("text")
                    sec_text_parts.append(f"--- Page {p+1} ---\n{page_txt}")
                extracted_sections["General Summary"] = "\n".join(sec_text_parts)

            return extracted_sections

        except Exception as e:
            logger.error(f"Failed to extract PDF sections: {e}")
            return {"error": str(e)}
        finally:
            if doc:
                doc.close()

    @classmethod
    def get_concatenated_filing_text(
        cls,
        pdf_source: Optional[Union[str, Path, bytes]] = None,
        symbol: Optional[str] = None,
    ) -> str:
        """
        Produce a single formatted string representing high-risk chapters.
        Falls back to benchmark sample if PDF source is empty or fails.
        """
        # 1. Try benchmark sample if requested or if symbol given
        if symbol and not pdf_source:
            sample = cls.get_sample_filing(symbol)
            if sample:
                return sample

        # 2. If PDF source provided, extract
        if pdf_source:
            sections = cls.extract_targeted_sections_from_pdf(pdf_source)
            if "error" not in sections:
                combined = []
                for title, body in sections.items():
                    combined.append(f"==================================================")
                    combined.append(f"[SECTION: {title.upper()}]")
                    combined.append(f"==================================================")
                    combined.append(body)
                full_text = "\n\n".join(combined)
                if len(full_text) > MAX_EXTRACT_CHARS:
                    full_text = full_text[:MAX_EXTRACT_CHARS] + "\n[TRUNCATED TO 80K TOKENS]"
                return full_text

        # 3. Fallback to sample if symbol provided
        if symbol:
            sample = cls.get_sample_filing(symbol)
            if sample:
                return sample

        return ""
