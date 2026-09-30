"""A form anyone can use to add a posting. Submissions wait for review before they show up."""
from datetime import date

import streamlit as st

from common import get_conn, signed_in_email
from salaries.postings import LEVELS, PE_OPTIONS, DuplicatePosting, Posting, add_posting, validate

st.title("Add a posting")
st.caption("Seen a Front Range engineering job with a pay range? Add it here. "
           "It appears on **Browse pay** after a reviewer approves it.")

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
today = date.today()

with st.form("add_posting", clear_on_submit=False):
    st.markdown("**The job**")
    a, b = st.columns(2)
    title = a.text_input("Job title *", key="title", placeholder="Project Engineer")
    employer = b.text_input("Employer *", key="employer", placeholder="City of Fort Collins")
    a, b = st.columns(2)
    location = a.text_input("Location *", key="location", placeholder="Fort Collins, CO")
    url = b.text_input("Link to the posting", key="url", placeholder="https://...")
    a, b, c = st.columns([1, 1, 2])
    month = a.selectbox("Month posted", MONTHS, index=today.month - 1, key="month")
    year = b.selectbox("Year", list(range(today.year, today.year - 4, -1)), key="year")
    level = c.selectbox("Level", ["Work it out from the title"] + LEVELS, key="level")

    st.markdown("**Pay**")
    a, b, c = st.columns(3)
    period = a.radio("Pay is", ["Per year", "Per hour"], horizontal=True, key="period")
    pay_min = b.number_input("From *", min_value=0.0, step=1000.0, value=None, key="pay_min",
                             placeholder="75000 or 36.50")
    pay_max = c.number_input("To *", min_value=0.0, step=1000.0, value=None, key="pay_max",
                             placeholder="95000 or 48.00")

    st.markdown("**Requirements**")
    a, b, c = st.columns(3)
    yrs_min = a.number_input("Years of experience, minimum", min_value=0.0, max_value=40.0,
                             step=1.0, value=None, key="yrs_min")
    yrs_max = b.number_input("Maximum (if a range)", min_value=0.0, max_value=40.0, step=1.0,
                             value=None, key="yrs_max")
    pe = c.selectbox("PE license", ["Not stated"] + PE_OPTIONS, key="pe",
                     help="One option: a PE is one of several credentials the posting accepts.")
    a, b = st.columns(2)
    other = a.text_input("Other licenses or certifications", key="other", placeholder="EI, CFM")
    education = b.text_input("Education", key="education", placeholder="Bachelor's in civil engineering")
    st.markdown("**The job description**")
    description = st.text_area(
        "Paste the job description", key="description", height=200,
        placeholder="Copy the whole posting from the employer's page and paste it here.",
        help="The app pulls out a summary, the duties, required qualifications and desired "
             "traits, which people see when they click the posting. Reviewers can check them.")
    notes = st.text_area("Anything else worth knowing", key="notes",
                         placeholder="Bonus, remote days, benefits, how you heard about it")
    who = None if signed_in_email() else st.text_input(
        "Your name or email (optional)", key="who",
        help="Only reviewers see this, in case they have a question about the posting.")
    submitted = st.form_submit_button("Submit for review", type="primary")

if submitted:
    posting = Posting(
        title=title, employer=employer, location=location, url=url or None,
        pay_min=pay_min, pay_max=pay_max,
        pay_period="hour" if period == "Per hour" else "year",
        posted_month=date(year, MONTHS.index(month) + 1, 1),
        years_exp_min=yrs_min, years_exp_max=yrs_max,
        pe_required=None if pe == "Not stated" else pe,
        other_licenses=other or None, education=education or None,
        level=level if level in LEVELS else None, notes=notes or None,
        description=description or None,
        source="Submitted",
    )
    problems = validate(posting)
    if problems:
        st.error("Please fix these before submitting:\n\n" + "\n".join(f"- {p}" for p in problems))
    else:
        conn = get_conn()
        try:
            submitter = signed_in_email() or (who or "").strip() or "anonymous"
            add_posting(conn, posting, status="pending", submitted_by=submitter)
        except DuplicatePosting:
            st.warning(f"**{title}** at {employer} in {location} is already in the database "
                       "or waiting for review.")
        else:
            st.success(f"Thanks. **{title}** at {employer} is waiting for review.")
        finally:
            conn.close()
