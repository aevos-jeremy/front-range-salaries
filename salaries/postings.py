"""Adding, reviewing and reading salary postings."""
import hashlib
import re
from dataclasses import dataclass, fields
from datetime import date

import pandas as pd

from salaries.describe import extract

HOURS_PER_YEAR = 2080
LEVELS = ["Entry", "Mid", "Senior", "Lead"]
PE_OPTIONS = ["Required", "One option", "Not required"]


class DuplicatePosting(Exception):
    """The same title, employer and location is already in the database."""


@dataclass
class Posting:
    title: str
    employer: str
    location: str
    pay_min: float | None = None
    pay_max: float | None = None
    pay_period: str | None = None          # 'year' or 'hour'
    url: str | None = None
    source: str = "Submitted"
    posted_month: date | None = None
    years_exp_min: float | None = None
    years_exp_max: float | None = None
    pe_required: str | None = None
    other_licenses: str | None = None
    education: str | None = None
    level: str | None = None
    notes: str | None = None
    summary: str | None = None
    responsibilities: str | None = None      # one item per line
    qualifications: str | None = None
    desired_traits: str | None = None
    description: str | None = None           # full pasted or scraped text


def posting_key(title, employer, location):
    norm = "|".join(" ".join((s or "").lower().split()) for s in (title, employer, location))
    return hashlib.sha1(norm.encode()).hexdigest()[:12]


def annualize(amount, period):
    if amount is None:
        return None
    return round(float(amount) * (HOURS_PER_YEAR if period == "hour" else 1))


def infer_level(title, years_min=None):
    """Entry / Mid / Senior / Lead from the job title, then from years of experience."""
    t = (title or "").lower()
    if re.search(r"\b(principal|director|leader|lead)\b", t):
        return "Lead"
    if re.search(r"\b(senior|sr|iv|v)\b", t):
        return "Senior"
    if re.search(r"\b(entry|junior|jr|intern)\b|\bi$", t):
        return "Entry"
    if years_min is not None:
        return "Entry" if years_min < 3 else "Mid" if years_min < 7 else "Senior"
    if re.search(r"\b(ii|iii)\b", t):
        return "Mid"
    return None


def pe_from_licenses(text):
    """Map the scraper's license text ('PE', 'EI, CFM', 'PM II: PE, EI...') to PE_OPTIONS."""
    if not text:
        return None
    if re.match(r"\s*PE\b", text):
        return "Required"
    if re.search(r"\bPE\b", text):
        return "One option"
    return "Not required"


def validate(p):
    """Returns a list of problems a person can fix; empty when the posting is fine."""
    problems = []
    for name in ("title", "employer", "location"):
        if not (getattr(p, name) or "").strip():
            problems.append(f"Enter the {name.replace('_', ' ')}.")
    if p.pay_min is None or p.pay_max is None:
        problems.append("Enter both ends of the pay range.")
    elif p.pay_min <= 0 or p.pay_max < p.pay_min:
        problems.append("The pay range needs a minimum above zero and a maximum at least as high.")
    elif p.pay_period == "hour" and p.pay_max > 500:
        problems.append("That looks like a yearly salary. Change the pay period to Per year.")
    elif p.pay_period == "year" and p.pay_min < 20000:
        problems.append("That looks like an hourly rate. Change the pay period to Per hour.")
    if p.pay_period not in ("year", "hour"):
        problems.append("Choose whether the pay is per year or per hour.")
    if (p.years_exp_min is not None and p.years_exp_max is not None
            and p.years_exp_max < p.years_exp_min):
        problems.append("Maximum years of experience is less than the minimum.")
    if p.url and not re.match(r"https?://", p.url.strip()):
        problems.append("The link should start with http:// or https://.")
    return problems


def add_posting(conn, p, status="pending", submitted_by=None):
    """Insert a posting. Raises DuplicatePosting if it's already there. Returns its id."""
    key = posting_key(p.title, p.employer, p.location)
    values = {f.name: getattr(p, f.name) for f in fields(Posting)}
    for name in ("title", "employer", "location", "url", "other_licenses", "education", "notes",
                 "summary", "responsibilities", "qualifications", "desired_traits", "description"):
        if isinstance(values[name], str):
            values[name] = values[name].strip() or None
    # Fill whatever wasn't given from the full description text.
    for name, found in extract(values["description"]).items():
        values[name] = values[name] or found
    values["level"] = values["level"] or infer_level(p.title, p.years_exp_min)
    values.update(posting_key=key, status=status, submitted_by=submitted_by,
                  annual_min=annualize(p.pay_min, p.pay_period),
                  annual_max=annualize(p.pay_max, p.pay_period))
    cols = list(values)
    with conn.transaction():
        row = conn.execute(
            f"INSERT INTO salary_posting ({', '.join(cols)}) "
            f"VALUES ({', '.join('%s' for _ in cols)}) "
            "ON CONFLICT (posting_key) DO NOTHING RETURNING posting_id",
            [values[c] for c in cols]).fetchone()
    if row is None:
        raise DuplicatePosting(p.title)
    return row["posting_id"]


def review(conn, posting_id, approve, reviewer, note=None):
    with conn.transaction():
        conn.execute(
            "UPDATE salary_posting SET status=%s, reviewed_by=%s, reviewed_at=now(), review_note=%s "
            "WHERE posting_id=%s",
            ("approved" if approve else "rejected", reviewer, note, posting_id))


def load(conn, status="approved"):
    rows = conn.execute(
        "SELECT * FROM salary_posting WHERE status=%s ORDER BY posted_month DESC NULLS LAST, title",
        (status,)).fetchall()
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for c in ("pay_min", "pay_max", "annual_min", "annual_max", "years_exp_min", "years_exp_max"):
        df[c] = pd.to_numeric(df[c])
    df["posted_month"] = pd.to_datetime(df["posted_month"])
    return df


def experience_text(lo, hi):
    if pd.isna(lo):
        return None
    lo_s = f"{lo:g}"
    return f"{lo_s}–{hi:g} yrs" if not pd.isna(hi) else f"{lo_s}+ yrs"


def as_posted_text(lo, hi, period):
    if pd.isna(lo):
        return None
    if period == "hour":
        return f"${lo:,.2f}–${hi:,.2f}/hr"
    return f"${lo / 1000:,.0f}k–${hi / 1000:,.0f}k/yr"
