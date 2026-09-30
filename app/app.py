"""Streamlit entry point. Run with:  streamlit run app/app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Front Range Engineering Pay", layout="wide")

pages = [
    st.Page("browse_page.py", title="Browse pay", default=True),
    st.Page("submit_page.py", title="Add a posting"),
    st.Page("review_page.py", title="Review submissions"),
]
st.navigation(pages).run()
