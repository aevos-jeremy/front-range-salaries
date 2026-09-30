# Front Range Engineering Pay

A small web application that shows what civil and water-resources engineering jobs
along Colorado's Front Range pay, so young engineers can see their market rate.

- **Browse pay**: filter by level and PE requirement, search by title, employer or city,
  and type in a salary to see how many posted ranges it falls inside. Every column in
  the table sorts, and the filtered table downloads as a CSV.
- **Add a posting**: anyone who can open the app can submit a posting they've seen.
  Submissions wait for review.
- **Review submissions**: reviewers approve or reject what people submit. Approved
  postings show up on Browse pay right away.

Postings from the CASFM Help Wanted board come in through `tools/import_casfm.py`,
which reads the SQLite file the CASFM scraper writes.

## Running it on your own computer

You need Python 3.11 or newer.

```
python -m venv .venv
.venv\Scripts\activate          (Windows)   or   source .venv/bin/activate
pip install -r requirements.txt
```

Put the settings in `.streamlit/secrets.toml` (private; never committed):

```
DATABASE_URL = "postgresql://..."
ADMIN_EMAILS = "you@example.com, colleague@example.com"
ADMIN_PASSWORD = "pick-something"
```

- `DATABASE_URL` is the shared PostgreSQL database. The app creates its one table,
  `salary_posting`, the first time it connects, so it can share a database with
  other apps.
- `ADMIN_EMAILS` are the signed-in viewers of the hosted app who may review.
- `ADMIN_PASSWORD` unlocks reviewing for anyone who enters it. Use it on your own
  computer, where nobody is signed in. Leave it out to allow reviewing by email only.

Then start the app:

```
streamlit run app/app.py --server.address localhost
```

On Windows you can double-click `start_app.bat` instead.

## CASFM postings

The app loads `reference_data/casfm_postings.csv` every time it starts, so a new database
fills itself. To update that file from the CASFM scraper's SQLite file:

```
python tools/import_casfm.py path\to\salary.db
```

Then commit and push the CSV; Streamlit restarts the hosted app and loads it. Only postings
with a pay range are included. Loading never changes anything people submitted.

## Hosting it on Streamlit Community Cloud

Deploy `app/app.py` from this repository and paste the three settings above into
**Advanced settings > Secrets** (later: the app's menu > Settings > Secrets).

Community Cloud allows one private app per workspace, so this app can run public.
Nothing secret is in the repository, and anything a visitor submits waits for review.
Public visitors aren't signed in, so the form asks for an optional name or email and
reviewers unlock the review page with `ADMIN_PASSWORD`.

## Tests

```
pytest
```

Tests need `DATABASE_URL`. Each test works in its own temporary schema that is deleted
afterwards, so real data is never touched.

## Project layout

```
app/          Streamlit pages
salaries/     Database schema, settings, and posting rules
tools/        Command-line utilities (CASFM import)
tests/        Automated tests
```
