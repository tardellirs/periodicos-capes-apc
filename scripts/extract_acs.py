"""
Extract ACS CAPES agreement journals from ACS.pdf.
Enriches with ISSNs from CrossRef public API.
"""

import json
import os
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path

import pdfplumber

RAW_DIR = Path(__file__).parent.parent / "data" / "00_raw"
OUT_DIR = Path(__file__).parent.parent / "data" / "01_processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CROSSREF_API = "https://api.crossref.org/journals"
# Polite pool: CrossRef etiquette asks for a contact email in the User-Agent.
# Set CONTACT_EMAIL in your environment to join the polite pool; otherwise an
# anonymous User-Agent is sent.
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "").strip()
HEADERS = {
    "User-Agent": (
        f"CAPES-Journal-Catalog/1.0 (mailto:{CONTACT_EMAIL})"
        if CONTACT_EMAIL
        else "CAPES-Journal-Catalog/1.0"
    )
}

# Known junk lines that match the regex but are not journals
SKIP_EXACT = {
    "ACS Publications also provides",
    "Chemical Education",
    "Chemical Engineering and",
    "Organic Chemistry",
    "Environmental Chemistry",
    "Industrial Chemistry",
    "Nanoscience",
    "Energy",
}

# Agreement-specific OA type overrides
DIAMOND_OA = {"ACS Central Science", "ACS Chemical Health & Safety"}


# ─── Step 1: Extract journal names from PDF ───────────────────────────────────

def extract_names_from_pdf() -> list[str]:
    journals = set()

    with pdfplumber.open(RAW_DIR / "ACS.pdf") as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            if not words:
                continue

            # Group words by y-coordinate (5px buckets = same line)
            lines_by_y: dict[int, list] = {}
            for w in words:
                y = round(w["top"] / 5) * 5
                lines_by_y.setdefault(y, []).append(w)

            for y in sorted(lines_by_y):
                line_words = sorted(lines_by_y[y], key=lambda w: w["x0"])

                # Split into column segments at gaps > 40px
                segments = []
                current = [line_words[0]]
                for w in line_words[1:]:
                    if w["x0"] - current[-1]["x1"] > 40:
                        segments.append(" ".join(x["text"] for x in current))
                        current = [w]
                    else:
                        current.append(w)
                segments.append(" ".join(x["text"] for x in current))

                for seg in segments:
                    seg = seg.strip()
                    if seg in SKIP_EXACT or len(seg) < 5:
                        continue
                    # Skip section headers and noise
                    if re.search(
                        r"Highly Recommended|Also Valuable|Journals by|multidisciplinary"
                        r"|guide is not|serve as|always able|received more"
                        r"|Unique Element|peer-reviewed|account manager"
                        r"|Publications \d|research area|^\d+\s*$",
                        seg,
                    ):
                        continue
                    # Match journal name patterns
                    if re.match(
                        r"^(ACS |Accounts |Analytical Chemistry|Biochemistry"
                        r"|Bioconjugate|Biomacromolecules|Chemical Research"
                        r"|Chemical Reviews|Chemistry of|Crystal |Energy & "
                        r"|Environmental Science|Industrial & |Inorganic Chemistry"
                        r"|JACS |Journal |Langmuir|Macromolecules|Molecular "
                        r"|Nano Letters|Organic Letters|Organic Process"
                        r"|Organometallics|The Journal)",
                        seg,
                    ):
                        # Reject merged lines (two journal names concatenated)
                        if not re.search(
                            r"(ACS [A-Z]|Journal of [A-Z]|The Journal|Accounts of|"
                            r"Analytical|Biochemistry|Bioconjugate|Biomacromolecules|"
                            r"Chemical R|Chemistry of|Crystal|Energy &|Environmental S|"
                            r"Industrial|Inorganic|JACS|Langmuir|Macromolecules|"
                            r"Molecular|Nano L|Organic|Organometallics).+"
                            r"(ACS |Journal|The Journal|Accounts|Analytical|"
                            r"Biochemistry|Chemical|Chemistry|Crystal|Energy|"
                            r"Environmental|Industrial|Inorganic|JACS|Langmuir|"
                            r"Macromolecules|Molecular|Nano|Organic|Organometallics)",
                            seg,
                        ):
                            journals.add(seg)

    return sorted(journals)


# ─── Step 2: Look up ISSNs via CrossRef ───────────────────────────────────────

def lookup_issn(title: str) -> dict:
    """Query CrossRef for a journal title, return best match metadata."""
    query = urllib.parse.urlencode({"query": title, "rows": 3})
    url = f"{CROSSREF_API}?{query}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        items = data.get("message", {}).get("items", [])
        for item in items:
            item_title = item.get("title", "")
            # Accept if titles match closely (case-insensitive)
            if item_title.lower().strip() == title.lower().strip():
                issns = item.get("ISSN", [])
                issn_types = {t["type"]: t["value"] for t in item.get("issn-type", [])}
                return {
                    "issn": issn_types.get("print") or (issns[0] if issns else None),
                    "eissn": issn_types.get("electronic") or (issns[1] if len(issns) > 1 else None),
                    "url": item.get("URL"),
                    "publisher": item.get("publisher"),
                }
    except Exception as e:
        print(f"  [WARN] CrossRef lookup failed for '{title}': {e}")
    return {}


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("Step 1: Extracting journal names from PDF...")
    names = extract_names_from_pdf()
    print(f"  Found {len(names)} unique journal names")

    print("\nStep 2: Looking up ISSNs via CrossRef API...")
    journals = []
    for i, name in enumerate(names, 1):
        meta = lookup_issn(name)
        oa_type = "Diamond Open Access" if name in DIAMOND_OA else "Hybrid"
        journals.append({
            "publisher": "ACS",
            "title": name,
            "issn": meta.get("issn"),
            "eissn": meta.get("eissn"),
            "open_access_type": oa_type,
            "license": "CC BY" if name in DIAMOND_OA else None,
            "publisher_journal_id": None,
            "acronym": None,
            "main_discipline": "Chemistry",
            "subject_area": None,
            "publishing_model": oa_type,
            "imprint": "ACS Publications",
            "url": meta.get("url"),
            "metrics": None,
        })
        found = "✓" if meta.get("issn") or meta.get("eissn") else "✗"
        print(f"  [{i:02d}/{len(names)}] {found} {name}")
        time.sleep(0.1)  # polite delay

    found_count = sum(1 for j in journals if j["issn"] or j["eissn"])
    print(f"\n  ISSNs resolved: {found_count}/{len(journals)}")

    out = {
        "publisher": "ACS",
        "full_name": "American Chemical Society",
        "agreement_model": "APC",
        "agreement_note": (
            "Covers ALL ACS journals. "
            "ACS Central Science and ACS Chemical Health & Safety are Diamond OA (free to publish and read). "
            "All other journals: APC fully covered under CAPES agreement."
        ),
        "agreement_url": "https://acsopenscience.org/customers/capes/",
        "journals": journals,
    }

    out_path = OUT_DIR / "acs.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {out_path}")
    print(f"Total: {len(journals)} journals")


if __name__ == "__main__":
    main()
