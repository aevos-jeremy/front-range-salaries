"""Approve or reject postings people have submitted."""
import hmac

import streamlit as st

from common import current_user, get_conn, get_settings, is_admin
from salaries.postings import as_posted_text, experience_text, load, review

st.title("Review submissions")

if not is_admin():
    settings = get_settings()
    if not settings.admin_password:
        st.info("Only reviewers can approve submissions. Ask the app owner to add your "
                "email to the reviewer list.")
        st.stop()
    pw = st.text_input("Reviewer password", type="password")
    if pw and hmac.compare_digest(pw, settings.admin_password):
        st.session_state["admin_unlocked"] = True
        st.rerun()
    elif pw:
        st.error("That password isn't right.")
    st.stop()

conn = get_conn()
try:
    pending = load(conn, status="pending")
    if pending.empty:
        st.success("Nothing is waiting for review.")
        st.stop()
    st.caption(f"{len(pending)} waiting. Approved postings show up on Browse pay right away.")
    for row in pending.itertuples():
        with st.container(border=True):
            st.markdown(f"**{row.title}** · {row.employer} · {row.location}")
            details = [
                as_posted_text(row.pay_min, row.pay_max, row.pay_period),
                experience_text(row.years_exp_min, row.years_exp_max),
                f"PE: {row.pe_required}" if row.pe_required else None,
                row.level,
                row.posted_month.strftime("%b %Y") if row.posted_month is not None else None,
            ]
            st.write(" · ".join(d for d in details if d).replace("$", "\\$"))
            if row.other_licenses or row.education:
                st.caption(" · ".join(x for x in (row.other_licenses, row.education) if x))
            if row.notes:
                st.caption(row.notes)
            if row.summary:
                st.write(row.summary.replace("$", "\\$"))
            found = [label for field, label in (("responsibilities", "duties"),
                                                ("qualifications", "required qualifications"),
                                                ("desired_traits", "desired traits"))
                     if getattr(row, field)]
            if row.description:
                with st.expander("Job description" + (f" (found {', '.join(found)})" if found else "")):
                    st.text(row.description)
            if row.url:
                st.markdown(f"[Open the posting]({row.url})")
            st.caption(f"Submitted by {row.submitted_by or 'unknown'} on "
                       f"{row.submitted_at:%b %d, %Y}")
            a, b, _ = st.columns([1, 1, 4])
            if a.button("Approve", key=f"ok{row.posting_id}", type="primary"):
                review(conn, row.posting_id, True, current_user())
                st.rerun()
            if b.button("Reject", key=f"no{row.posting_id}"):
                review(conn, row.posting_id, False, current_user())
                st.rerun()
finally:
    conn.close()
