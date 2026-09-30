from datetime import date

import pytest

from salaries.postings import (DuplicatePosting, Posting, add_posting, annualize, infer_level,
                               load, pe_from_licenses, review, validate)


def sample(**kw):
    base = dict(title="Project Engineer", employer="Example Engineering", location="Denver, CO",
                pay_min=70000, pay_max=85000, pay_period="year", posted_month=date(2026, 9, 1))
    base.update(kw)
    return Posting(**base)


def test_annualize_hourly():
    assert annualize(48.25, "hour") == 100360
    assert annualize(90000, "year") == 90000


@pytest.mark.parametrize("title,years,level", [
    ("Civil Sector Leader (PE)", None, "Lead"),
    ("Dam Safety Engineer IV", None, "Senior"),
    ("Engineer II", None, "Mid"),
    ("Project Engineer", 1, "Entry"),
    ("Project Engineer", None, None),
])
def test_infer_level(title, years, level):
    assert infer_level(title, years) == level


def test_pe_from_licenses():
    assert pe_from_licenses("PE (Colorado)") == "Required"
    assert pe_from_licenses("PM II: PE, EI, PMP") == "One option"
    assert pe_from_licenses("EI, CFM") == "Not required"
    assert pe_from_licenses(None) is None


def test_validate_catches_swapped_period():
    assert any("hourly" in p for p in validate(sample(pay_min=36, pay_max=48, pay_period="year")))
    assert any("yearly" in p for p in validate(sample(pay_period="hour")))
    assert validate(sample()) == []
    assert validate(sample(title=" ")) == ["Enter the title."]


def test_submission_waits_for_review(conn):
    pid = add_posting(conn, sample(), submitted_by="someone@example.com")
    assert load(conn).empty
    assert len(load(conn, "pending")) == 1
    review(conn, pid, True, "reviewer@example.com")
    df = load(conn)
    assert df.iloc[0]["annual_max"] == 85000
    assert df.iloc[0]["level"] is None or df.iloc[0]["level"] in ("Entry", "Mid", "Senior", "Lead")


def test_duplicate_is_rejected(conn):
    add_posting(conn, sample())
    with pytest.raises(DuplicatePosting):
        add_posting(conn, sample(title="project  engineer", location="denver, co"))
