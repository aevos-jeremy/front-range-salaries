"""Each test gets its own temporary schema, deleted afterwards, so real data is never touched."""
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from salaries.config import load_settings  # noqa: E402
from salaries.db import connect, init_db  # noqa: E402


@pytest.fixture
def conn():
    url = load_settings().database_url
    if not url:
        pytest.skip("DATABASE_URL is not set")
    c = connect(url)
    schema = f"test_{uuid.uuid4().hex[:10]}"
    c.execute(f"CREATE SCHEMA {schema}")
    c.execute(f"SET search_path TO {schema}")
    init_db(c)
    try:
        yield c
    finally:
        c.execute(f"DROP SCHEMA {schema} CASCADE")
        c.close()
