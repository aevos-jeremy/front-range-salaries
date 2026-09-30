"""Update the CASFM postings the app loads, from the scraper's SQLite file (salary.db).

    python tools/import_casfm.py path/to/salary.db

This rewrites reference_data/casfm_postings.csv. Commit and push that file, and the
hosted app loads the postings the next time it starts (Streamlit restarts the app
after every push). Only postings with a pay range are included.

If DATABASE_URL is set, the postings are also loaded into that database right away.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from salaries.casfm import SEED_FILE, load_seed, rows_from_scraper, write_seed  # noqa: E402
from salaries.config import load_settings  # noqa: E402
from salaries.db import connect, init_db  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    n = write_seed(rows_from_scraper(sys.argv[1]))
    print(f"Wrote {n} CASFM postings to {SEED_FILE}.")
    url = load_settings().database_url
    if url:
        conn = connect(url)
        try:
            init_db(conn)
            print(f"Loaded {load_seed(conn)} CASFM postings into the database.")
        finally:
            conn.close()


if __name__ == "__main__":
    main()
