"""Shared helpers for the Streamlit pages."""
import getpass

import streamlit as st

from salaries.config import load_settings
from salaries.casfm import load_seed
from salaries.db import connect, init_db


def get_settings():
    return load_settings()


@st.cache_resource(show_spinner="Connecting to the database...")
def _prepare_database(url):
    """Create missing tables and load the CASFM postings, once per app start."""
    conn = connect(url)
    try:
        init_db(conn)
        load_seed(conn)
    finally:
        conn.close()
    return True


def get_conn():
    """Open a connection to the shared database for this page run."""
    url = get_settings().database_url
    if not url:
        st.error("The database is not configured. Add DATABASE_URL to "
                 "`.streamlit/secrets.toml` (or the hosted app's Secrets).")
        st.stop()
    _prepare_database(url)
    return connect(url)


def signed_in_email():
    """The viewer's email on the hosted app, or None when running locally."""
    try:
        email = st.user.get("email")
    except Exception:
        email = None
    return email if email and email != "test@example.com" else None


def current_user():
    """Who is using the app, for the record of who submitted or approved what."""
    return signed_in_email() or f"{getpass.getuser()} (local)"


def is_admin():
    """Reviewers are signed-in viewers listed in ADMIN_EMAILS, or anyone who enters
    ADMIN_PASSWORD on the review page (useful locally, where nobody is signed in)."""
    settings = get_settings()
    email = signed_in_email()
    if email and email.lower() in settings.admin_emails:
        return True
    return bool(st.session_state.get("admin_unlocked"))
