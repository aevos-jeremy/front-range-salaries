"""Settings, read from the environment or from .streamlit/secrets.toml (never committed).

- DATABASE_URL: the shared PostgreSQL database.
- ADMIN_EMAILS: comma-separated emails of signed-in viewers who may approve
  submissions on the hosted app.
- ADMIN_PASSWORD: optional. Entering it on the review page also unlocks reviewing,
  which is how you review when running the app on your own computer.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SECRETS_FILE = PROJECT_ROOT / ".streamlit" / "secrets.toml"


@dataclass
class Settings:
    database_url: str | None
    admin_emails: set = field(default_factory=set)
    admin_password: str | None = None


def _secrets():
    if SECRETS_FILE.exists():
        return tomllib.loads(SECRETS_FILE.read_text(encoding="utf-8"))
    return {}


def load_settings():
    secrets = _secrets()
    url = os.environ.get("DATABASE_URL") or secrets.get("DATABASE_URL") or ""
    admins = os.environ.get("ADMIN_EMAILS") or secrets.get("ADMIN_EMAILS") or ""
    if isinstance(admins, list):
        admins = ",".join(admins)
    password = os.environ.get("ADMIN_PASSWORD") or secrets.get("ADMIN_PASSWORD") or ""
    return Settings(database_url=url.strip() or None,
                    admin_password=password or None,
                    admin_emails={a.strip().lower() for a in admins.split(",") if a.strip()})
