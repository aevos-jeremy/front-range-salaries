"""CASFM postings: read them from the scraper's SQLite file or from the seed CSV
committed in reference_data/, and upsert them as approved postings."""
import csv
import sqlite3
from datetime import date
from pathlib import Path

from salaries.describe import extract
from salaries.postings import annualize, pe_from_licenses, posting_key

SEED_FILE = Path(__file__).resolve().parents[1] / "reference_data" / "casfm_postings.csv"

SEED_COLUMNS = ["title", "employer", "location", "url", "posted_month",
                "pay_min", "pay_max", "pay_period", "years_exp_min", "years_exp_max",
                "pe_required", "other_licenses", "education", "level", "notes",
                "summary", "responsibilities", "qualifications", "desired_traits",
                "description", "archived_at", "source"]
DB_COLUMNS = ["posting_key", "annual_min", "annual_max", "status",
              "submitted_by"] + SEED_COLUMNS
NUMERIC = {"pay_min", "pay_max", "years_exp_min", "years_exp_max"}


def rows_from_scraper(path):
    """Seed-shaped rows from the scraper's salary.db (postings with pay only)."""
    src = sqlite3.connect(path)
    src.row_factory = sqlite3.Row
    for r in src.execute("SELECT * FROM postings WHERE pay_min IS NOT NULL ORDER BY first_seen"):
        licenses = r["licenses_required"]
        pe = pe_from_licenses(licenses)
        others = ", ".join(x.strip() for x in (licenses or "").split(",")
                           if x.strip() and not x.strip().startswith("PE")) or None
        first = r["first_seen"]
        # Details typed in by hand win; otherwise pull them from the page text that
        # newer scraper runs save.
        keys = r.keys()
        details = extract(r["description"] if "description" in keys else None)
        for name in details:
            if name in keys and r[name]:
                details[name] = r[name]
        yield {
            **details,
            "title": r["title"], "employer": r["employer"], "location": r["location"],
            "url": r["url"], "posted_month": f"{first[:7]}-01" if first else None,
            "pay_min": r["pay_min"], "pay_max": r["pay_max"], "pay_period": r["pay_period"],
            "years_exp_min": r["years_exp_min"], "years_exp_max": r["years_exp_max"],
            "pe_required": pe, "other_licenses": licenses if pe == "One option" else others,
            "education": r["education"], "level": r["level"], "notes": r["notes"],
            "description": r["description"] if "description" in keys else None,
            "archived_at": r["archived_at"] if "archived_at" in keys else None,
            # CASFM for the live board; older postings Jeremy logged by hand say where
            # they came from.
            "source": r["source"] or "CASFM",
        }


def write_seed(rows, path=SEED_FILE):
    rows = list(rows)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SEED_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def rows_from_seed(path=SEED_FILE):
    if not Path(path).exists():
        return
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            row = {c: (r.get(c) or "").strip() or None for c in SEED_COLUMNS}
            for c in NUMERIC:
                row[c] = float(row[c]) if row[c] is not None else None
            yield row


def upsert(conn, rows):
    """Insert seed postings as approved, or refresh ones already loaded from the seed.
    Never changes postings people submitted."""
    keep = {"posting_key", "status", "submitted_by", "posted_month"}
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in DB_COLUMNS if c not in keep)
    n = 0
    with conn.transaction():
        for row in rows:
            full = dict(row)
            full.update(
                posting_key=posting_key(row["title"], row["employer"], row["location"]),
                source=row.get("source") or "CASFM", status="approved", submitted_by="CASFM scraper",
                annual_min=annualize(row["pay_min"], row["pay_period"]),
                annual_max=annualize(row["pay_max"], row["pay_period"]),
                posted_month=date.fromisoformat(row["posted_month"]) if row["posted_month"] else None,
                archived_at=date.fromisoformat(row["archived_at"]) if row.get("archived_at") else None,
            )
            conn.execute(
                f"INSERT INTO salary_posting ({', '.join(DB_COLUMNS)}) "
                f"VALUES ({', '.join('%s' for _ in DB_COLUMNS)}) "
                f"ON CONFLICT (posting_key) DO UPDATE SET {updates} "
                "WHERE salary_posting.submitted_by = 'CASFM scraper'",
                [full[c] for c in DB_COLUMNS])
            n += 1
    return n


def load_seed(conn):
    """Called at app start: loads reference_data/casfm_postings.csv. Safe to repeat."""
    return upsert(conn, rows_from_seed())
