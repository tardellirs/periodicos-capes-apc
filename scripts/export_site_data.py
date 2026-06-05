"""
Export SQLite database to an optimized JSON file for the static site.
Run: python scripts/export_site_data.py
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_FILE = ROOT / "acordos.db"
OUT_DIR = ROOT / "site" / "public"
OUT_FILE = OUT_DIR / "data.json"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    # Fetch all journals
    rows = conn.execute("""
        SELECT id, title, publisher, issn, eissn,
               open_access_type AS oa, license,
               primary_area AS area, main_discipline,
               imprint, url, qualis_best,
               impact_factor, acronym
        FROM journals
        ORDER BY title COLLATE NOCASE
    """).fetchall()

    # Fetch all qualis entries grouped by journal
    qualis_rows = conn.execute("""
        SELECT journal_id, area, estrato
        FROM journal_qualis
        ORDER BY journal_id, area
    """).fetchall()

    # Build qualis map
    qualis_map: dict[int, list] = {}
    for qr in qualis_rows:
        qualis_map.setdefault(qr["journal_id"], []).append({
            "area": qr["area"],
            "estrato": qr["estrato"],
        })

    journals = []
    for r in rows:
        j = dict(r)
        j["qualis"] = qualis_map.get(j["id"], [])
        journals.append(j)

    conn.close()

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(journals, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = OUT_FILE.stat().st_size // 1024
    print(f"Exported {len(journals)} journals → {OUT_FILE} ({size_kb} KB)")


if __name__ == "__main__":
    main()
