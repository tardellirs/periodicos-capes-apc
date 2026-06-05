"""
Load all processed journal data into a local SQLite database.
Run: python scripts/load_to_db.py
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent
JSON_FILE = ROOT / "data" / "01_processed" / "all_journals.json"
DB_FILE = ROOT / "acordos.db"


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        DROP TABLE IF EXISTS journals_fts;
        DROP TABLE IF EXISTS journal_qualis;
        DROP TABLE IF EXISTS journals;

        CREATE TABLE journals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            publisher       TEXT,
            issn            TEXT,
            eissn           TEXT,
            open_access_type TEXT,
            license         TEXT,
            primary_area    TEXT,
            main_discipline TEXT,
            subject_area    TEXT,
            imprint         TEXT,
            url             TEXT,
            qualis_best     TEXT,
            impact_factor   REAL,
            acronym         TEXT,
            cites_per_doc   REAL,
            quartile        TEXT,
            sjr             REAL,
            h_index         INTEGER,
            metric_source   TEXT
        );

        CREATE TABLE journal_qualis (
            journal_id  INTEGER NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
            area        TEXT NOT NULL,
            estrato     TEXT NOT NULL,
            PRIMARY KEY (journal_id, area)
        );

        CREATE INDEX idx_j_publisher    ON journals(publisher);
        CREATE INDEX idx_j_primary_area ON journals(primary_area);
        CREATE INDEX idx_j_qualis_best  ON journals(qualis_best);
        CREATE INDEX idx_j_issn         ON journals(issn);
        CREATE INDEX idx_j_eissn        ON journals(eissn);
        CREATE INDEX idx_jq_journal     ON journal_qualis(journal_id);
        CREATE INDEX idx_jq_estrato     ON journal_qualis(estrato);

        CREATE VIRTUAL TABLE journals_fts USING fts5(
            title,
            issn,
            eissn,
            content=journals,
            content_rowid=id
        );
    """)


def load(conn: sqlite3.Connection, journals: list[dict]) -> None:
    insert_journal = """
        INSERT INTO journals
            (title, publisher, issn, eissn, open_access_type, license,
             primary_area, main_discipline, subject_area, imprint, url,
             qualis_best, impact_factor, acronym,
             cites_per_doc, quartile, sjr, h_index, metric_source)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    insert_qualis = """
        INSERT OR IGNORE INTO journal_qualis (journal_id, area, estrato)
        VALUES (?,?,?)
    """

    for j in journals:
        metrics = j.get("metrics") or {}
        if not isinstance(metrics, dict):
            metrics = {}

        cur = conn.execute(insert_journal, (
            j.get("title"),
            j.get("publisher"),
            j.get("issn"),
            j.get("eissn"),
            j.get("open_access_type"),
            j.get("license"),
            j.get("primary_area"),
            j.get("main_discipline"),
            j.get("subject_area"),
            j.get("imprint"),
            j.get("url"),
            j.get("qualis_best"),
            metrics.get("impact_factor"),
            j.get("acronym"),
            metrics.get("cites_per_doc"),
            metrics.get("quartile"),
            metrics.get("sjr"),
            metrics.get("h_index"),
            metrics.get("metric_source"),
        ))
        journal_id = cur.lastrowid

        for q in (j.get("qualis") or []):
            conn.execute(insert_qualis, (journal_id, q["area"], q["estrato"]))

    # Populate FTS index
    conn.execute("""
        INSERT INTO journals_fts(rowid, title, issn, eissn)
        SELECT id, title, COALESCE(issn,''), COALESCE(eissn,'') FROM journals
    """)


def main() -> None:
    print(f"Loading {JSON_FILE} ...")
    with open(JSON_FILE, encoding="utf-8") as f:
        journals = json.load(f)
    print(f"  {len(journals)} journals found")

    print(f"Creating {DB_FILE} ...")
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    create_schema(conn)
    load(conn, journals)
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM journals").fetchone()[0]
    qualis_total = conn.execute("SELECT COUNT(*) FROM journal_qualis").fetchone()[0]
    print(f"  journals:       {total}")
    print(f"  qualis entries: {qualis_total}")
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
