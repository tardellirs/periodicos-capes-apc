"""
Link Qualis CAPES classifications to the extracted journal catalog.

Strategy:
  1. Build Qualis index by ISSN → list of {area, estrato}
  2. For each journal: match by ISSN, then eISSN, then normalized title (fallback)
  3. Add qualis_classifications list to each journal entry
  4. Save enriched per-publisher JSONs + combined all_journals.json
"""

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

RAW_DIR  = Path(__file__).parent.parent / "data" / "00_raw"
OUT_DIR  = Path(__file__).parent.parent / "data" / "01_processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

QUALIS_FILE = RAW_DIR / "classificações_publicadas_todas_as_areas_avaliacao1768259646562.xlsx"

PUBLISHER_FILES = [
    "acm.json",
    "ieee.json",
    "springer_nature.json",
    "elsevier.json",
    "wiley.json",
    "acs.json",
    "royal_society.json",
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def normalize_title(title: str) -> str:
    """Lowercase, remove accents, collapse spaces, strip punctuation."""
    if not title:
        return ""
    nfkd = unicodedata.normalize("NFKD", title)
    ascii_ = nfkd.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", ascii_.lower()).split().__str__()


def normalize_issn(issn) -> str | None:
    if not issn:
        return None
    s = re.sub(r"[^0-9Xx]", "", str(issn)).upper()
    if len(s) == 8:
        return f"{s[:4]}-{s[4:]}"
    return None


# ─── Build Qualis index ───────────────────────────────────────────────────────

def build_qualis_index(df: pd.DataFrame):
    """Returns two dicts:
      issn_index  : ISSN  → list[{area, estrato}]
      title_index : normalized_title → list[{area, estrato, issn}]
    """
    issn_index: dict[str, list] = {}
    title_index: dict[str, list] = {}

    for _, row in df.iterrows():
        issn  = normalize_issn(row.get("ISSN"))
        title = str(row.get("Título", "") or "").strip()
        area  = str(row.get("Área de Avaliação", "") or "").strip()
        strat = str(row.get("Estrato", "") or "").strip()

        if not area or not strat:
            continue

        entry = {"area": area, "estrato": strat}

        if issn:
            issn_index.setdefault(issn, []).append(entry)

        nt = normalize_title(title)
        if nt:
            title_index.setdefault(nt, []).append({**entry, "issn": issn})

    return issn_index, title_index


def lookup(journal: dict, issn_index: dict, title_index: dict) -> list:
    """Find all Qualis classifications for a journal."""
    # Try print ISSN
    issn = normalize_issn(journal.get("issn"))
    if issn and issn in issn_index:
        return issn_index[issn]

    # Try electronic ISSN
    eissn = normalize_issn(journal.get("eissn"))
    if eissn and eissn in issn_index:
        return issn_index[eissn]

    # Fallback: title match
    nt = normalize_title(journal.get("title", ""))
    if nt and nt in title_index:
        entries = title_index[nt]
        # Reject ambiguous matches: multiple distinct ISSNs with the same title
        # means different journals share the name — we can't tell which one is ours
        distinct_issns = {e.get("issn") for e in entries if e.get("issn")}
        if len(distinct_issns) > 1:
            return []
        return entries

    return []


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("Loading Qualis data...")
    df = pd.read_excel(QUALIS_FILE)
    print(f"  {len(df):,} rows, {df['ISSN'].nunique():,} unique ISSNs")

    print("Building Qualis index...")
    issn_index, title_index = build_qualis_index(df)
    print(f"  ISSN index: {len(issn_index):,} entries")
    print(f"  Title index: {len(title_index):,} entries")

    total_journals = 0
    total_matched = 0
    all_journals_flat = []

    for fname in PUBLISHER_FILES:
        fpath = OUT_DIR / fname
        if not fpath.exists():
            print(f"  [SKIP] {fname} not found")
            continue

        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)

        journals = data["journals"]
        matched = 0

        for j in journals:
            # Skip institution list stored inside Royal Society journals
            j.pop("participating_institutions", None)

            classifications = lookup(j, issn_index, title_index)

            # Deduplicate (same area can appear via different ISSN match paths)
            seen = set()
            unique_classifications = []
            for c in classifications:
                key = (c["area"], c["estrato"])
                if key not in seen:
                    seen.add(key)
                    unique_classifications.append(c)

            j["qualis"] = sorted(unique_classifications, key=lambda c: (c["area"], c["estrato"]))

            if unique_classifications:
                matched += 1

            # Best stratum across all areas (A1 > A2 > ... > C)
            strata_order = ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4", "C"]
            all_strata = [c["estrato"] for c in unique_classifications]
            best = min(all_strata, key=lambda s: strata_order.index(s)) if all_strata else None
            j["qualis_best"] = best

            all_journals_flat.append(j)

        data["journals"] = journals
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  {fname}: {matched}/{len(journals)} journals matched Qualis")
        total_journals += len(journals)
        total_matched += matched

    # Save combined flat file
    out_path = OUT_DIR / "all_journals.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_journals_flat, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: {total_matched}/{total_journals} journals linked to Qualis")
    print(f"Combined file: {out_path}")

    # Coverage summary by publisher
    print("\nCoverage by publisher:")
    for fname in PUBLISHER_FILES:
        fpath = OUT_DIR / fname
        if not fpath.exists():
            continue
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        journals = data["journals"]
        matched = sum(1 for j in journals if j.get("qualis"))
        print(f"  {data['publisher']}: {matched}/{len(journals)} ({100*matched//len(journals)}%)")

    # Qualis distribution across catalog
    print("\nQualis stratum distribution in catalog:")
    from collections import Counter
    best_strata = [j["qualis_best"] for j in all_journals_flat if j.get("qualis_best")]
    for s, n in sorted(Counter(best_strata).items()):
        print(f"  {s}: {n}")
    unmatched = sum(1 for j in all_journals_flat if not j.get("qualis_best"))
    print(f"  (sem Qualis): {unmatched}")


if __name__ == "__main__":
    main()
