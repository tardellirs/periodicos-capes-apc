"""
Enrich the journal catalog with citation metrics, using ONE uniform source for
every journal so the numbers are directly comparable across publishers.

Primary source  : Scimago Journal Rank (SJR) — bulk parquet, matched by ISSN.
                  Gives quartile (Q1–Q4), SJR, h-index and citations/doc (2y).
Fallback source : OpenAlex API — for the ~7% of journals absent from Scimago.
                  Gives 2yr_mean_citedness (proxy for cites/doc), h-index.

Each journal's `metrics` dict gets a uniform block (kept alongside any existing
publisher-scraped keys, e.g. IEEE's official impact_factor):

    cites_per_doc  : float  — citations per document, 2-year window
    quartile       : str    — best SJR quartile (Q1..Q4), or null (OpenAlex rows)
    sjr            : float   — SJR score (Scimago only)
    h_index        : int     — h-index
    metric_source  : str     — "scimago" | "openalex"

Run: python scripts/add_metrics.py   (after link_qualis.py)
"""

import json
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / "data" / "00_raw"
OUT_DIR = ROOT / "data" / "01_processed"

SCIMAGO_DIR = RAW_DIR / "scimago"
SCIMAGO_FILE = SCIMAGO_DIR / "sjr_journals.parquet"
SCIMAGO_URL = (
    "https://raw.githubusercontent.com/ikashnitsky/sjrdata/master/"
    "data-raw/sjr-journal/sjr_journals-2025.parquet"
)
SCIMAGO_YEAR = 2024  # latest year present in the 2025 release

OPENALEX_MAILTO = "stekel@ifsp.edu.br"  # polite pool
OPENALEX_BATCH = 40

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

def issn_key(value) -> str | None:
    """8-char ISSN with no hyphen, uppercase X. None if not a valid ISSN."""
    if not value:
        return None
    s = re.sub(r"[^0-9Xx]", "", str(value)).upper()
    return s if len(s) == 8 else None


def journal_keys(j: dict) -> list[str]:
    return [k for k in (issn_key(j.get("issn")), issn_key(j.get("eissn"))) if k]


def num(value) -> float | None:
    """Coerce to float, mapping NaN/blank to None."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(f) else f


# ─── Scimago ──────────────────────────────────────────────────────────────────

def ensure_scimago() -> Path:
    if SCIMAGO_FILE.exists():
        return SCIMAGO_FILE
    SCIMAGO_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading Scimago dataset → {SCIMAGO_FILE} (~47 MB)...")
    req = urllib.request.Request(SCIMAGO_URL, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=300) as r, open(SCIMAGO_FILE, "wb") as f:
        f.write(r.read())
    return SCIMAGO_FILE


def build_scimago_index() -> dict[str, dict]:
    """ISSN key → uniform metrics dict (Scimago)."""
    ensure_scimago()
    df = pd.read_parquet(SCIMAGO_FILE)
    df = df[df["year"] == SCIMAGO_YEAR]
    print(f"  Scimago {SCIMAGO_YEAR}: {len(df):,} journals")

    index: dict[str, dict] = {}
    for row in df.itertuples(index=False):
        metrics = {
            "cites_per_doc": round(num(row.citations_doc_2years), 2)
            if num(row.citations_doc_2years) is not None else None,
            "quartile": row.sjr_best_quartile
            if isinstance(row.sjr_best_quartile, str) and row.sjr_best_quartile.startswith("Q")
            else None,
            "sjr": round(num(row.sjr), 3) if num(row.sjr) is not None else None,
            "h_index": int(row.h_index) if num(row.h_index) is not None else None,
            "metric_source": "scimago",
        }
        for tok in re.split(r"[,\s]+", str(row.issn or "")):
            tok = tok.strip().upper()
            if len(tok) == 8:
                index.setdefault(tok, metrics)
    print(f"  Scimago ISSN keys: {len(index):,}")
    return index


# ─── OpenAlex fallback ────────────────────────────────────────────────────────

def fetch_openalex(keys: list[str]) -> dict[str, dict]:
    """ISSN key → uniform metrics dict (OpenAlex), for the given ISSN keys."""
    out: dict[str, dict] = {}
    hyphenated = [f"{k[:4]}-{k[4:]}" for k in keys]
    headers = {"User-Agent": f"acordos-capes (mailto:{OPENALEX_MAILTO})"}

    for i in range(0, len(hyphenated), OPENALEX_BATCH):
        chunk = hyphenated[i:i + OPENALEX_BATCH]
        params = urllib.parse.urlencode({
            "filter": "issn:" + "|".join(chunk),
            "select": "issn,issn_l,summary_stats",
            "per-page": 100,
            "mailto": OPENALEX_MAILTO,
        })
        url = f"https://api.openalex.org/sources?{params}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                results = json.load(r).get("results", [])
        except Exception as exc:  # noqa: BLE001 — best-effort enrichment
            print(f"    [warn] OpenAlex batch {i // OPENALEX_BATCH} failed: {exc}")
            results = []

        for src in results:
            stats = src.get("summary_stats") or {}
            cpd = num(stats.get("2yr_mean_citedness"))
            metrics = {
                "cites_per_doc": round(cpd, 2) if cpd is not None else None,
                "quartile": None,  # OpenAlex has no quartile
                "sjr": None,
                "h_index": int(stats["h_index"]) if num(stats.get("h_index")) is not None else None,
                "metric_source": "openalex",
            }
            for ii in (src.get("issn") or []):
                k = issn_key(ii)
                if k:
                    out[k] = metrics
        time.sleep(0.2)
    return out


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Building Scimago index...")
    scimago = build_scimago_index()

    # Pass 1: load every journal, match Scimago, collect the misses.
    files: dict[str, dict] = {}
    flat: list[dict] = []
    unmatched: list[dict] = []

    for fname in PUBLISHER_FILES:
        fpath = OUT_DIR / fname
        if not fpath.exists():
            print(f"  [SKIP] {fname} not found")
            continue
        with open(fpath, encoding="utf-8") as f:
            files[fname] = json.load(f)

        for j in files[fname]["journals"]:
            flat.append(j)
            metrics = next((scimago[k] for k in journal_keys(j) if k in scimago), None)
            if metrics:
                j["metrics"] = {**(j.get("metrics") or {}), **metrics}
            else:
                unmatched.append(j)

    print(f"\nScimago matched {len(flat) - len(unmatched)}/{len(flat)} journals")

    # Pass 2: OpenAlex fallback for the misses.
    miss_keys = sorted({k for j in unmatched for k in journal_keys(j)})
    print(f"Querying OpenAlex for {len(miss_keys)} ISSNs ({len(unmatched)} journals)...")
    openalex = fetch_openalex(miss_keys)

    oa_matched = 0
    for j in unmatched:
        metrics = next((openalex[k] for k in journal_keys(j) if k in openalex), None)
        if metrics:
            j["metrics"] = {**(j.get("metrics") or {}), **metrics}
            oa_matched += 1
    print(f"OpenAlex matched {oa_matched}/{len(unmatched)} of the remainder")

    # Write per-publisher files back + the combined flat file.
    for fname, data in files.items():
        with open(OUT_DIR / fname, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    with open(OUT_DIR / "all_journals.json", "w", encoding="utf-8") as f:
        json.dump(flat, f, ensure_ascii=False, indent=2)

    # Summary.
    have = sum(1 for j in flat if (j.get("metrics") or {}).get("cites_per_doc") is not None)
    print(f"\nTotal with cites/doc: {have}/{len(flat)} ({100 * have // len(flat)}%)")
    src = Counter((j.get("metrics") or {}).get("metric_source") for j in flat)
    print("By source:", dict(src))
    quart = Counter((j.get("metrics") or {}).get("quartile") for j in flat)
    print("Quartile distribution:", {k: quart[k] for k in ["Q1", "Q2", "Q3", "Q4", None]})


if __name__ == "__main__":
    main()
