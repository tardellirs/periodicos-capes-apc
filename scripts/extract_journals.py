"""
Extract journal data from CAPES APC agreement PDFs.
Outputs structured JSON files ready for database ingestion.
"""

import json
import re
import sys
from pathlib import Path

import pdfplumber

RAW_DIR = Path(__file__).parent.parent / "data" / "00_raw"
OUT_DIR = Path(__file__).parent.parent / "data" / "01_processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def clean(value):
    if value is None:
        return None
    v = str(value).strip()
    return v if v and v != "N/A" else None


def parse_float(value):
    v = clean(value)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def parse_issn(value):
    """Normalize ISSN to XXXX-XXXX format."""
    v = clean(value)
    if v is None:
        return None
    digits = re.sub(r"[^0-9Xx]", "", v)
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:]}"
    return v if v else None


# ─── ACM ──────────────────────────────────────────────────────────────────────

def extract_acm():
    pdf_path = RAW_DIR / "ACM.pdf"
    journals = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    num, issn, eissn, title = row
                    num = clean(num)
                    title = clean(title)
                    if not title or not num or not num.isdigit():
                        continue
                    journals.append({
                        "publisher": "ACM",
                        "title": title,
                        "issn": parse_issn(issn),
                        "eissn": parse_issn(eissn),
                        "open_access_type": "Full Open Access",
                        "license": "CC BY",
                        "publisher_journal_id": None,
                        "acronym": None,
                        "main_discipline": "Computer Science",
                        "subject_area": None,
                        "publishing_model": None,
                        "imprint": "ACM",
                        "url": None,
                        "metrics": None,
                    })

    print(f"ACM: {len(journals)} journals extracted")
    return journals


# ─── IEEE ─────────────────────────────────────────────────────────────────────

def extract_ieee():
    pdf_path = RAW_DIR / "IEEE.pdf"
    journals = []
    header_cols = [
        "acronym", "title", "open_access_type", "issn", "eissn",
        "index", "impact_factor", "impact_factor_5yr", "quartile",
        "jci", "eigenfactor", "article_influence_score", "cite_score",
    ]

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    # Skip header rows and title rows
                    first = clean(row[0]) if row else None
                    if not first or first in ("IEEE Title List", "Publication\nAcronym", "Publication Acronym"):
                        continue
                    if len(row) < 13:
                        continue

                    acronym = clean(row[0])
                    title = clean(row[1])
                    if not title:
                        continue

                    oa_type = clean(row[2])
                    metrics = {
                        "index": clean(row[5]),
                        "impact_factor": parse_float(row[6]),
                        "impact_factor_5yr": parse_float(row[7]),
                        "quartile": clean(row[8]),
                        "jci": parse_float(row[9]),
                        "eigenfactor": parse_float(row[10]),
                        "article_influence_score": parse_float(row[11]),
                        "cite_score": parse_float(row[12]),
                    }
                    # Drop metrics dict if all values are None
                    has_metrics = any(v is not None for v in metrics.values())

                    journals.append({
                        "publisher": "IEEE",
                        "title": title,
                        "issn": parse_issn(row[3]),
                        "eissn": parse_issn(row[4]),
                        "open_access_type": oa_type,
                        "license": None,
                        "publisher_journal_id": None,
                        "acronym": acronym,
                        "main_discipline": None,
                        "subject_area": None,
                        "publishing_model": None,
                        "imprint": "IEEE",
                        "url": f"https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber={acronym}" if acronym else None,
                        "metrics": metrics if has_metrics else None,
                    })

    # Deduplicate by title (same journal may appear on multiple pages)
    seen = set()
    unique = []
    for j in journals:
        key = j["title"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(j)

    print(f"IEEE: {len(unique)} journals extracted")
    return unique


# ─── Nature / Springer ────────────────────────────────────────────────────────

NATURE_MODEL_MAP = {
    "Hybrid": "Hybrid",
    "Fully Open Access": "Full Open Access",
    "Open Access": "Full Open Access",
    "Subscription": "Subscription",
}

VALID_MODELS = {"Hybrid", "Full Open Access", "Subscription"}


def normalize_publishing_model(raw):
    if not raw:
        return None
    # Fix known OCR corruption patterns (e.g. "HSpybrirnidger" is "Hybrid" + noise)
    for known in NATURE_MODEL_MAP:
        if raw.startswith(known[:4]):
            return NATURE_MODEL_MAP[known]
    return None


def extract_nature():
    pdf_path = RAW_DIR / "Nature.pdf"
    journals = []
    seen_ids = set()

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                prev_journal_id = None
                prev_title = None
                prev_eissn = None
                prev_imprint = None

                for row in table:
                    if not row or len(row) < 9:
                        continue

                    journal_id = clean(row[0])
                    title = clean(row[1])
                    eissn = clean(row[2])
                    imprint = clean(row[3])
                    main_discipline = clean(row[4])
                    subject_area = clean(row[5])
                    publishing_model_raw = clean(row[6])
                    publishing_model = normalize_publishing_model(publishing_model_raw)
                    license_ = clean(row[7])
                    url = clean(row[8])

                    # Handle split rows (title wraps across rows)
                    if journal_id and journal_id.isdigit():
                        prev_journal_id = journal_id
                        prev_title = title
                        prev_eissn = eissn
                        prev_imprint = imprint
                    elif not journal_id and prev_journal_id:
                        # continuation row — merge into previous entry
                        if journals and journals[-1]["publisher_journal_id"] == prev_journal_id:
                            if title and not journals[-1]["title"]:
                                journals[-1]["title"] = title
                            if eissn and not journals[-1]["eissn"]:
                                journals[-1]["eissn"] = parse_issn(eissn)
                            if imprint and not journals[-1]["imprint"]:
                                journals[-1]["imprint"] = imprint
                            if main_discipline and not journals[-1]["main_discipline"]:
                                journals[-1]["main_discipline"] = main_discipline
                            if subject_area and not journals[-1]["subject_area"]:
                                journals[-1]["subject_area"] = subject_area
                            if publishing_model and not journals[-1]["publishing_model"]:
                                journals[-1]["publishing_model"] = publishing_model
                                journals[-1]["open_access_type"] = publishing_model
                        continue

                    if not prev_journal_id or prev_journal_id in seen_ids:
                        continue
                    if not (title or prev_title):
                        continue

                    seen_ids.add(prev_journal_id)
                    oa_type = publishing_model or "Hybrid"
                    journals.append({
                        "publisher": "Springer Nature",
                        "title": title or prev_title,
                        "issn": None,
                        "eissn": parse_issn(eissn or prev_eissn),
                        "open_access_type": oa_type,
                        "license": license_,
                        "publisher_journal_id": prev_journal_id,
                        "acronym": None,
                        "main_discipline": main_discipline,
                        "subject_area": subject_area,
                        "publishing_model": publishing_model,
                        "imprint": imprint or prev_imprint,
                        "url": url,
                        "metrics": None,
                    })

    print(f"Nature/Springer: {len(journals)} journals extracted")
    return journals


# ─── Royal Society ────────────────────────────────────────────────────────────

ROYAL_SOCIETY_JOURNALS = [
    {"title": "Philosophical Transactions A", "eissn": "1471-2962", "issn": "1364-503X"},
    {"title": "Philosophical Transactions B", "eissn": "1471-2970", "issn": "0962-8436"},
    {"title": "Proceedings A",                "eissn": "1471-2946", "issn": "1364-5021"},
    {"title": "Proceedings B",                "eissn": "1471-2954", "issn": "0962-8452"},
    {"title": "Biology Letters",              "eissn": "1744-957X", "issn": "1744-9561"},
    {"title": "Interface",                    "eissn": "1742-5662", "issn": "1742-5689"},
    {"title": "Interface Focus",              "eissn": "2042-8901", "issn": "2042-8898"},
    {"title": "Open Biology",                 "eissn": "2046-2441", "issn": None},
    {"title": "Royal Society Open Science",   "eissn": "2054-5703", "issn": None},
    {"title": "Notes and Records",            "eissn": "1743-0178", "issn": "0035-9149"},
]


def extract_royal_society():
    pdf_path = RAW_DIR / "Royal-Society.pdf"
    journals = []

    # Extract participating institutions from PDF text
    institutions = []
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(
            page.extract_text() or "" for page in pdf.pages
        )

    # Parse institutions list after "Instituições Participantes"
    marker = "Instituições Participantes"
    end_marker = "Conheça os periódicos"
    if marker in full_text:
        start = full_text.index(marker) + len(marker)
        # Cut off at footer / end-of-institutions markers
        end = len(full_text)
        for stop in ["© 2025", "Follow us", "Modern Slavery", "Statement", "Cookie"]:
            idx = full_text.find(stop, start)
            if idx != -1 and idx < end:
                end = idx
        inst_block = full_text[start:end]
        # Remove "O acordo contempla 260 instituições..." line
        inst_block = re.sub(r"O acordo contempla.*?\n", "", inst_block)
        stop_words = [
            "email update", "subscribe", "first name", "last name",
            "newsletter", "we promote", "benefit humanity", "fellowship",
            "flexi grant", "useful links", "legal visit",
        ]
        for line in inst_block.splitlines():
            line = line.strip()
            if not line or len(line) < 5:
                continue
            if any(kw in line.lower() for kw in stop_words):
                break
            if all(not c.isalpha() for c in line):
                continue
            institutions.append(line)

    for j in ROYAL_SOCIETY_JOURNALS:
        oa_type = (
            "Full Open Access"
            if j["title"] in ("Open Biology", "Royal Society Open Science")
            else "Hybrid Open Access"
        )
        journals.append({
            "publisher": "Royal Society",
            "title": j["title"],
            "issn": j.get("issn"),
            "eissn": j.get("eissn"),
            "open_access_type": oa_type,
            "license": "CC BY 4.0",
            "publisher_journal_id": None,
            "acronym": None,
            "main_discipline": None,
            "subject_area": None,
            "publishing_model": "Read and Publish",
            "imprint": "Royal Society",
            "url": f"https://royalsocietypublishing.org/{j['title'].lower().replace(' ', '')}",
            "metrics": None,
            "participating_institutions": institutions,
        })

    print(f"Royal Society: {len(journals)} journals extracted ({len(institutions)} institutions)")
    return journals


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    all_publishers = {}

    acm = extract_acm()
    all_publishers["ACM"] = {
        "publisher": "ACM",
        "full_name": "Association for Computing Machinery",
        "agreement_model": "APC",
        "agreement_url": "https://www.periodicos.capes.gov.br/index.php/acessoaberto/acordos-transformativos.html",
        "journals": acm,
    }

    ieee = extract_ieee()
    all_publishers["IEEE"] = {
        "publisher": "IEEE",
        "full_name": "Institute of Electrical and Electronics Engineers",
        "agreement_model": "APC",
        "agreement_url": "https://www.periodicos.capes.gov.br/index.php/acessoaberto/acordos-transformativos.html",
        "journals": ieee,
    }

    nature = extract_nature()
    all_publishers["Springer Nature"] = {
        "publisher": "Springer Nature",
        "full_name": "Springer Nature",
        "agreement_model": "APC",
        "agreement_updated": "2025-12-31",
        "agreement_url": "https://www.periodicos.capes.gov.br/index.php/acessoaberto/acordos-transformativos.html",
        "journals": nature,
    }

    royal = extract_royal_society()
    all_publishers["Royal Society"] = {
        "publisher": "Royal Society",
        "full_name": "The Royal Society",
        "agreement_model": "Read and Publish",
        "agreement_url": "https://www.periodicos.capes.gov.br/index.php/acessoaberto/acordos-transformativos.html",
        "journals": royal,
    }

    # Save per-publisher files
    for publisher_key, data in all_publishers.items():
        slug = publisher_key.lower().replace(" ", "_").replace("/", "_")
        out_path = OUT_DIR / f"{slug}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved: {out_path}")

    # Save combined flat list of all journals
    all_journals = []
    for data in all_publishers.values():
        for j in data["journals"]:
            j_copy = dict(j)
            # Don't duplicate institutions in flat list
            j_copy.pop("participating_institutions", None)
            all_journals.append(j_copy)

    total_out = OUT_DIR / "all_journals.json"
    with open(total_out, "w", encoding="utf-8") as f:
        json.dump(all_journals, f, ensure_ascii=False, indent=2)

    print(f"\nTotal: {len(all_journals)} journals across {len(all_publishers)} publishers")
    print(f"Combined file: {total_out}")

    # Summary
    for publisher_key, data in all_publishers.items():
        print(f"  {publisher_key}: {len(data['journals'])} journals")


if __name__ == "__main__":
    main()
