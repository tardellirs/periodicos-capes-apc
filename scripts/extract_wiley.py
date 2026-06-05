"""
Extract Wiley CAPES agreement journals from Wiley.xlsx.
"""

import json
from pathlib import Path

import openpyxl

RAW_DIR = Path(__file__).parent.parent / "data" / "00_raw"
OUT_DIR = Path(__file__).parent.parent / "data" / "01_processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def format_eissn(raw) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip().upper()
    # Remove any existing dashes
    s = s.replace("-", "")
    if len(s) == 8:
        return f"{s[:4]}-{s[4:]}"
    return s or None


def extract_wiley():
    wb = openpyxl.load_workbook(RAW_DIR / "Wiley.xlsx", read_only=True, data_only=True)
    ws = wb["PERIÓDICOS HÍBRIDOS WILEY"]

    rows = list(ws.iter_rows(values_only=True))

    # Header is at row index 4 (0-based)
    # Cols: #, TITULO, ESSN, ÁREA PRINCIPAL, SUB-ÁREA, LINK DE ACESSO URL, FATOR DE IMPACTO
    journals = []
    for row in rows[5:]:
        num, title, essn, main_area, sub_area, url, impact_factor = row

        title = str(title).strip() if title else None
        if not title:
            continue

        eissn = format_eissn(essn)
        url = str(url).strip() if url else None

        # Impact factor: already a float in the Excel
        if impact_factor is not None:
            try:
                impact_factor = float(impact_factor)
            except (ValueError, TypeError):
                impact_factor = None

        journals.append({
            "publisher": "Wiley",
            "title": title,
            "issn": None,
            "eissn": eissn,
            "open_access_type": "Hybrid",
            "license": None,
            "publisher_journal_id": None,
            "acronym": None,
            "main_discipline": str(main_area).strip() if main_area else None,
            "subject_area": str(sub_area).strip() if sub_area else None,
            "publishing_model": "Hybrid",
            "imprint": "Wiley",
            "url": url,
            "metrics": {
                "impact_factor": impact_factor,
            } if impact_factor is not None else None,
        })

    return journals


def main():
    journals = extract_wiley()
    print(f"Wiley: {len(journals)} journals extracted")

    out = {
        "publisher": "Wiley",
        "full_name": "John Wiley & Sons",
        "agreement_model": "APC",
        "agreement_url": "https://www.periodicos.capes.gov.br/index.php/acessoaberto/acordos-transformativos.html",
        "journals": journals,
    }

    out_path = OUT_DIR / "wiley.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved: {out_path}")

    # Quick summary
    from collections import Counter
    areas = Counter(j["main_discipline"] for j in journals)
    print("\nTop 10 subject areas:")
    for area, n in areas.most_common(10):
        print(f"  {area}: {n}")

    sample = journals[:3]
    print("\nSample:")
    for j in sample:
        print(f"  {j['title']} | {j['eissn']} | {j['main_discipline']} | IF:{j['metrics']}")


if __name__ == "__main__":
    main()
