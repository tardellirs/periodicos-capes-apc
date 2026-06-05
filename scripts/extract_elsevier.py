"""
Scrape Elsevier CAPES agreement journals from agreements.journals.elsevier.com/capes
Uses parallel requests with polite delays between batches.
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import urllib.request
import urllib.error
from html.parser import HTMLParser

OUT_DIR = Path(__file__).parent.parent / "data" / "01_processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)
BASE_URL = "https://agreements.journals.elsevier.com/capes"
TOTAL_PAGES = 162
BATCH_SIZE = 10
BATCH_DELAY = 0.5  # seconds between batches
MAX_RETRIES = 3
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


# ─── HTML Parser ──────────────────────────────────────────────────────────────

class JournalParser(HTMLParser):
    """Extract journal entries from Elsevier agreements page HTML."""

    def __init__(self):
        super().__init__()
        self.journals = []
        self._current = {}
        self._in_journal_block = False
        self._capture_next_strong = None  # field name to capture
        self._in_title_link = False
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        # Journal block starts at the outer row div
        if tag == "div" and "open-access-journal-result" in attrs.get("class", ""):
            self._current = {}
            self._in_journal_block = True
            return

        if not self._in_journal_block:
            return

        # Title link — only in the large-screen version (not the small hidden clone)
        if (tag == "a"
                and attrs.get("data-aa-name") == "journal title"
                and "data-aa-region" in attrs):
            self._current["title"] = attrs["data-aa-region"].strip()
            href = attrs.get("href", "")
            self._current["url"] = href
            # Extract ISSN from URL
            m = re.search(r"/issn/([0-9X-]+)", href)
            if m:
                raw = m.group(1).replace("-", "")
                if len(raw) == 8:
                    self._current["issn"] = f"{raw[:4]}-{raw[4:]}"
                else:
                    self._current["issn"] = m.group(1)
            return

        # Detect which field the next <strong> belongs to
        if tag == "span" and attrs.get("class") == "search-result-text":
            self._capture_next_strong = None  # reset

        # Large-screen only blocks carry the canonical data (ignore small/hidden duplicates)
        if tag == "div" and "hide-for-large-up" in attrs.get("class", ""):
            self._capture_next_strong = "__skip__"

    def handle_endtag(self, tag):
        if not self._in_journal_block:
            return

        if tag == "div" and self._capture_next_strong == "__skip__":
            self._capture_next_strong = None

    def handle_data(self, data):
        if not self._in_journal_block:
            return

        data = data.strip()
        if not data:
            return

        # Detect field labels
        if data in ("Primary Subject:", "OA Type:"):
            self._capture_next_strong = data.rstrip(":")
            return

        # Flush journal when we hit the <hr> separator text — but <hr> has no data,
        # so we detect the next journal's title link appearing while _current has data.
        # (handled via the journal block div detection above)

    def handle_entityref(self, name):
        pass

    def unknown_decl(self, data):
        pass


def parse_page(html: str) -> list[dict]:
    """Parse one page of HTML and return list of journal dicts."""
    journals = []

    # Split into journal blocks using the outer div class as delimiter
    blocks = re.split(r'class="[^"]*open-access-journal-result[^"]*"', html)

    for block in blocks[1:]:  # skip content before first journal
        journal = {}

        # Title: from data-aa-region attribute on the journal link
        m = re.search(r'data-aa-region="([^"]+)"', block)
        if m:
            journal["title"] = m.group(1).strip()

        # URL + ISSN from href
        m = re.search(r'href="(https?://[^"]*elsevier\.com/locate/issn/([^"]+))"', block)
        if m:
            journal["url"] = m.group(1).strip()
            issn_raw = m.group(2).strip()
            # URL already contains formatted ISSN (e.g. 1876-2859)
            journal["issn"] = issn_raw if "-" in issn_raw else f"{issn_raw[:4]}-{issn_raw[4:]}"

        # Primary Subject — </span></div> pattern before the show-for-large-up div
        m = re.search(
            r"Primary Subject:</span>\s*</span>\s*</div>\s*"
            r"<div[^>]*show-for-large-up[^>]*>\s*"
            r"<strong[^>]*>\s*([^<]+?)\s*</strong>",
            block,
            re.DOTALL,
        )
        if m:
            journal["primary_subject"] = m.group(1).strip()

        # OA Type
        m = re.search(
            r"OA Type:</span>\s*</span>\s*</div>\s*"
            r"<div[^>]*>\s*"
            r"<strong[^>]*>\s*([^<]+?)\s*</strong>",
            block,
            re.DOTALL,
        )
        if m:
            journal["oa_type"] = m.group(1).strip()

        if journal.get("title"):
            journals.append(journal)

    return journals


# ─── Fetcher ──────────────────────────────────────────────────────────────────

def fetch_page(page_no: int) -> tuple[int, list[dict]]:
    url = f"{BASE_URL}?pageNo={page_no}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            journals = parse_page(html)
            return page_no, journals
        except Exception as e:
            if attempt == MAX_RETRIES:
                print(f"  [FAIL] page {page_no} after {MAX_RETRIES} attempts: {e}")
                return page_no, []
            time.sleep(1.5 * attempt)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    all_journals = []
    failed_pages = []

    pages = list(range(1, TOTAL_PAGES + 1))
    batches = [pages[i:i + BATCH_SIZE] for i in range(0, len(pages), BATCH_SIZE)]

    print(f"Scraping {TOTAL_PAGES} pages in {len(batches)} batches of {BATCH_SIZE}...")

    for batch_idx, batch in enumerate(batches, 1):
        with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
            futures = {executor.submit(fetch_page, p): p for p in batch}
            for future in as_completed(futures):
                page_no, journals = future.result()
                if journals:
                    all_journals.extend(journals)
                else:
                    failed_pages.append(page_no)

        print(
            f"  Batch {batch_idx}/{len(batches)} done — "
            f"{len(all_journals)} journals so far"
        )
        if batch_idx < len(batches):
            time.sleep(BATCH_DELAY)

    # Deduplicate by ISSN (keep first occurrence)
    seen_issn = set()
    unique = []
    for j in all_journals:
        key = j.get("issn") or j.get("title", "").lower()
        if key not in seen_issn:
            seen_issn.add(key)
            unique.append(j)

    # Sort by title
    unique.sort(key=lambda j: j.get("title", "").lower())

    # Add publisher metadata to each record
    for j in unique:
        j["publisher"] = "Elsevier"
        j["open_access_type"] = j.pop("oa_type", None)
        j["main_discipline"] = j.pop("primary_subject", None)
        j["eissn"] = None
        j["license"] = None
        j["publisher_journal_id"] = None
        j["acronym"] = None
        j["subject_area"] = None
        j["publishing_model"] = None
        j["imprint"] = "Elsevier"
        j["metrics"] = None

    # Save
    out = {
        "publisher": "Elsevier",
        "full_name": "Elsevier",
        "agreement_model": "APC",
        "agreement_url": "https://agreements.journals.elsevier.com/capes",
        "journals": unique,
    }
    out_path = OUT_DIR / "elsevier.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\nDone: {len(unique)} unique journals saved to {out_path}")
    if failed_pages:
        print(f"Failed pages: {sorted(failed_pages)}")


if __name__ == "__main__":
    main()
