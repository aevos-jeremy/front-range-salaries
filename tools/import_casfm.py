"""Load postings from the CASFM scraper's SQLite file (salary.db) into the app's database.

    python tools/import_casfm.py path/to/salary.db

Only postings with a pay range are loaded; they arrive approved. Re-running updates
CASFM postings already loaded and never touches postings people submitted.
"""
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from salaries.config import load_settings  # noqa: E402
from salaries.db import connect, init_db  # noqa: E402
from salaries.postings import annualize, pe_from_licenses, posting_key  # noqa: E402

COLUMNS = ["posting_key", "title", "employer", "location", "url", "source", "posted_month",
           "pay_min", "pay_max", "pay_period", "annual_min", "annual_max",
           "years_exp_min", "years_exp_max", "pe_required", "other_licenses", "education",
           "level", "notes", "status", "submitted_by"]


def rows_from_scraper(path):
    src = sqlite3.connect(path)
    src.row_factory = sqlite3.Row
    for r in src.execute("SELECT * FROM postings WHERE pay_min IS NOT NULL"):
        licenses = r["licenses_required"]
        pe = pe_from_licenses(licenses)
        others = ", ".join(x.strip() for x in (licenses or "").split(",")
                           if x.strip() and not x.strip().startswith("PE")) or None
        first = r["first_seen"]
        yield {
            "posting_key": posting_key(r["title"], r["employer"], r["location"]),
            "title": r["title"], "employer": r["employer"], "location": r["location"],
            "url": r["url"], "source": "CASFM",
            "posted_month": date(int(first[:4]), int(first[5:7]), 1) if first else None,
            "pay_min": r["pay_min"], "pay_max": r["pay_max"], "pay_period": r["pay_period"],
            "annual_min": annualize(r["pay_min"], r["pay_period"]),
            "annual_max": annualize(r["pay_max"], r["pay_period"]),
            "years_exp_min": r["years_exp_min"], "years_exp_max": r["years_exp_max"],
            "pe_required": pe, "other_licenses": others if pe != "One option" else licenses,
            "education": r["education"], "level": r["level"], "notes": r["notes"],
            "status": "approved", "submitted_by": "CASFM scraper",
        }


def upsert(conn, rows):
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in COLUMNS
                        if c not in ("posting_key", "status", "submitted_by", "posted_month"))
    n = 0
    with conn.transaction():
        for row in rows:
            conn.execute(
                f"INSERT INTO salary_posting ({', '.join(COLUMNS)}) "
                f"VALUES ({', '.join('%s' for _ in COLUMNS)}) "
                f"ON CONFLICT (posting_key) DO UPDATE SET {updates} "
                "WHERE salary_posting.source = 'CASFM'",
                [row[c] for c in COLUMNS])
            n += 1
    return n


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    url = load_settings().database_url
    if not url:
        sys.exit("Set DATABASE_URL (or put it in .streamlit/secrets.toml) first.")
    conn = connect(url)
    try:
        init_db(conn)
        print(f"Loaded {upsert(conn, rows_from_scraper(sys.argv[1]))} CASFM postings.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
