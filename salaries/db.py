"""PostgreSQL connection and schema setup."""
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

SCHEMA_FILE = Path(__file__).with_name("schema.sql")


def connect(url):
    # Autocommit, so every `with conn.transaction()` block is its own committed
    # transaction even after earlier reads on the same connection.
    return psycopg.connect(url, row_factory=dict_row, autocommit=True)


def init_db(conn):
    """Create missing tables. Safe to run every time the app starts."""
    with conn.transaction():
        conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
