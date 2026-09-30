-- One row per job posting. Postings from the CASFM scraper arrive approved;
-- postings people submit through the app wait in 'pending' until reviewed.
CREATE TABLE IF NOT EXISTS salary_posting (
    posting_id     BIGSERIAL PRIMARY KEY,
    posting_key    TEXT NOT NULL UNIQUE,      -- title|employer|location, normalized
    title          TEXT NOT NULL,
    employer       TEXT NOT NULL,
    location       TEXT NOT NULL,
    url            TEXT,
    source         TEXT NOT NULL,             -- 'CASFM' or 'Submitted'
    posted_month   DATE,                      -- first day of the month posted / first seen
    pay_min        NUMERIC,
    pay_max        NUMERIC,
    pay_period     TEXT CHECK (pay_period IN ('year', 'hour')),
    annual_min     NUMERIC,                   -- hourly x 2080
    annual_max     NUMERIC,
    years_exp_min  NUMERIC,
    years_exp_max  NUMERIC,
    pe_required    TEXT CHECK (pe_required IN ('Required', 'One option', 'Not required')),
    other_licenses TEXT,
    education      TEXT,
    level          TEXT CHECK (level IN ('Entry', 'Mid', 'Senior', 'Lead')),
    notes          TEXT,
    status         TEXT NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('approved', 'pending', 'rejected')),
    submitted_by   TEXT,
    submitted_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_by    TEXT,
    reviewed_at    TIMESTAMPTZ,
    review_note    TEXT
);

CREATE INDEX IF NOT EXISTS salary_posting_status ON salary_posting (status);

-- What the job asks for, shown when someone clicks a posting. List columns hold one
-- item per line. description is the full text the rest was pulled from, when we have it.
ALTER TABLE salary_posting ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE salary_posting ADD COLUMN IF NOT EXISTS responsibilities TEXT;
ALTER TABLE salary_posting ADD COLUMN IF NOT EXISTS qualifications TEXT;
ALTER TABLE salary_posting ADD COLUMN IF NOT EXISTS desired_traits TEXT;
ALTER TABLE salary_posting ADD COLUMN IF NOT EXISTS description TEXT;
