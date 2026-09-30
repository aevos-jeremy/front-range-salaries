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


def test_description_fills_sections(conn):
    text = ("Riverside Engineering is hiring a Project Engineer to design stormwater systems for "
            "Front Range towns. You will work on projects from planning through construction.\n"
            "Responsibilities:\n- Design detention ponds\n- Prepare plan sets\n"
            "Requirements\n- EI certificate\n- Bachelor's in civil engineering\n"
            "Nice to have\n- HEC-RAS\n"
            "Benefits\n- 401k\n")
    add_posting(conn, sample(description=text))
    row = load(conn, "pending").iloc[0]
    assert row["summary"].startswith("Riverside Engineering is hiring")
    assert row["responsibilities"] == "Design detention ponds\nPrepare plan sets"
    assert row["qualifications"] == "EI certificate\nBachelor's in civil engineering"
    assert row["desired_traits"] == "HEC-RAS"


def test_typed_sections_beat_extracted(conn):
    add_posting(conn, sample(description="Duties:\n- Pulled from text\n", responsibilities="Typed in"))
    assert load(conn, "pending").iloc[0]["responsibilities"] == "Typed in"


def test_seed_reload_drops_renamed_postings(conn):
    from salaries.casfm import prune, upsert
    row = dict(title="Engineer (title not recorded)", employer="Rocksol", location="Colorado",
               url=None, posted_month="2024-11-01", pay_min=95000.0, pay_max=125000.0,
               pay_period="year", years_exp_min=9.0, years_exp_max=None, pe_required="Required",
               other_licenses=None, education=None, level="Senior", notes=None, summary=None,
               responsibilities=None, qualifications=None, desired_traits=None,
               description=None, archived_at=None, source="CASFM (logged by hand)")
    upsert(conn, [row])
    renamed = dict(row, title="Project Engineer")
    prune(conn, [renamed])
    upsert(conn, [renamed])
    titles = [r["title"] for r in conn.execute("SELECT title FROM salary_posting").fetchall()]
    assert titles == ["Project Engineer"]
