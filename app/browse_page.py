"""Browse approved postings: filters, a pay-range chart with a compare line, and a sortable table."""
import altair as alt
import pandas as pd
import streamlit as st

from common import get_conn
from salaries.postings import LEVELS, PE_OPTIONS, as_posted_text, experience_text, load

def _md(text):
    """Escape dollar signs so Streamlit doesn't read a pay range as math."""
    return str(text).replace("$", "\\$")


def _bullets(text):
    items = [line.strip() for line in str(text).split("\n") if line.strip()]
    return "\n".join(f"- {_md(i)}" for i in items)


def show_details(row):
    """The panel under the table for the posting someone clicked."""
    with st.container(border=True):
        st.subheader(row["title"])
        where = f"{row['employer']} · {row['location']}"
        if isinstance(row["url"], str) and row["url"]:
            where += f" · [Open the posting]({row['url']})"
        st.markdown(_md(where))
        facts = [as_posted_text(row["pay_min"], row["pay_max"], row["pay_period"]),
                 experience_text(row["years_exp_min"], row["years_exp_max"]),
                 f"PE {row['pe_required'].lower()}" if isinstance(row["pe_required"], str) else None,
                 row["level"] if isinstance(row["level"], str) else None]
        st.markdown(_md(" · ".join(f for f in facts if f)))
        if isinstance(row.get("summary"), str) and row["summary"]:
            st.markdown(_md(row["summary"]))
        cols = st.columns(3)
        shown = False
        for col, (field, label) in zip(cols, [("responsibilities", "What you'd do"),
                                               ("qualifications", "Required"),
                                               ("desired_traits", "Desired traits")]):
            value = row.get(field)
            if isinstance(value, str) and value.strip():
                col.markdown(f"**{label}**\n\n{_bullets(value)}")
                shown = True
        if not shown and not (isinstance(row.get("summary"), str) and row["summary"]):
            st.caption("No description captured for this posting yet. Open the posting "
                       "for the full text.")
        notes = row.get("notes")
        if isinstance(notes, str) and notes:
            st.caption(_md(notes))
        archive = row.get("description")
        if isinstance(archive, str) and archive.strip():
            when = row.get("archived_at")
            label = "Archived posting"
            if when is not None and not pd.isna(when):
                label += f" (saved {pd.Timestamp(when):%b %d, %Y})"
            with st.expander(label):
                st.caption("The posting's text as it read when saved, kept in case the link "
                           "stops working.")
                st.text(archive)


LEVEL_COLORS = ["#3b8f6b", "#1f6f8b", "#6a4fa3", "#b0493a"]   # Entry, Mid, Senior, Lead

st.title("Front Range Engineering Pay")
st.caption("Civil and water-resources job postings along the Front Range, from the CASFM "
           "Help Wanted board and postings people have added. Hourly pay is converted to "
           "annual at 2,080 hours.")

conn = get_conn()
try:
    df = load(conn)
finally:
    conn.close()

if df.empty:
    st.info("No postings yet. Use **Add a posting** to enter the first one.")
    st.stop()

# ---- Filters ----------------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns([2, 1.6, 1.6, 1.6, 1.4])
query = c1.text_input("Search", placeholder="Title, employer, city")
year_options = sorted(df["posted_month"].dropna().dt.year.unique().tolist(), reverse=True)
years = c2.multiselect("Year posted", year_options, placeholder="All years")
levels = c3.multiselect("Level", LEVELS, placeholder="All levels")
pe = c4.multiselect("PE", PE_OPTIONS + ["Not listed"], placeholder="Any")
compare = c5.number_input("Compare a salary ($/yr)", min_value=0, step=1000, value=0,
                          help="Draws a line on the chart and counts how many ranges it falls in.")

view = df.copy()
if query:
    text = (view["title"] + " " + view["employer"] + " " + view["location"]).str.lower()
    view = view[text.str.contains(query.lower(), regex=False)]
if years:
    view = view[view["posted_month"].dt.year.isin(years)]
if levels:
    view = view[view["level"].isin(levels)]
if pe:
    pe_col = view["pe_required"].fillna("Not listed")
    view = view[pe_col.isin(pe)]

paid = view.dropna(subset=["annual_min", "annual_max"])

# ---- Summary ----------------------------------------------------------------
m = st.columns(4)
m[0].metric("Postings", len(view))
if not paid.empty:
    mid = ((paid["annual_min"] + paid["annual_max"]) / 2).median()
    m[1].metric("Median midpoint", f"${mid:,.0f}")
    # "\$" keeps Streamlit from reading a pair of dollar signs as math.
    m[2].metric("Lowest to highest", f"\\${paid['annual_min'].min() / 1000:,.0f}k–"
                                     f"\\${paid['annual_max'].max() / 1000:,.0f}k")
    if compare:
        inside = ((paid["annual_min"] <= compare) & (paid["annual_max"] >= compare)).sum()
        below = (paid["annual_min"] > compare).sum()
        m[3].metric(f"${compare:,.0f} is inside", f"{inside} of {len(paid)} ranges",
                    help=f"Below the bottom of {below} ranges.")

# ---- Chart ------------------------------------------------------------------
if not paid.empty:
    st.subheader("Annual pay range by posting")
    chart_df = paid.assign(
        label=paid["title"] + " · " + paid["employer"] + " · "
        + paid["posted_month"].dt.strftime("%b %Y").fillna(""),
        mid=(paid["annual_min"] + paid["annual_max"]) / 2,
        level=paid["level"].fillna("Not set"),
    ).sort_values("mid")
    # Pad the x range so one or two postings still get a readable scale.
    lo, hi = chart_df["annual_min"].min(), chart_df["annual_max"].max()
    if compare:
        lo, hi = min(lo, compare), max(hi, compare)
    pad = max((hi - lo) * 0.05, 5000)
    x_start = (lo - pad) // 5000 * 5000
    x_scale = alt.Scale(domain=[x_start, hi + pad], nice=False)
    chart_df["x_start"] = x_start
    # Each posting's name sits on its own line above its bar, so long names never
    # squeeze the plot or run into each other.
    y = alt.Y("label:N", sort=chart_df["label"].tolist(), title=None, axis=None)
    base = alt.Chart(chart_df).encode(y=y)
    bars = base.mark_bar(height=12, cornerRadius=6, yOffset=8).encode(
        x=alt.X("annual_min:Q", title="Annual pay", scale=x_scale,
                axis=alt.Axis(format="$,.0f", tickCount=6, gridColor="#e6e9ec", orient="top")),
        x2="annual_max:Q",
        color=alt.Color("level:N", title="Level",
                        legend=alt.Legend(orient="top", direction="horizontal"),
                        scale=alt.Scale(domain=LEVELS + ["Not set"], range=LEVEL_COLORS + ["#97a4ad"])),
        tooltip=[alt.Tooltip("title:N", title="Posting"), alt.Tooltip("employer:N", title="Employer"),
                 alt.Tooltip("annual_min:Q", title="From", format="$,.0f"),
                 alt.Tooltip("annual_max:Q", title="To", format="$,.0f"),
                 alt.Tooltip("level:N", title="Level")],
    )
    names = base.mark_text(align="left", baseline="middle", yOffset=-9, fontSize=12,
                           color="#39424a").encode(x="x_start:Q", text="label:N")
    layers = [bars, names]
    if compare:
        rule_df = pd.DataFrame({"x": [compare]})
        layers.append(alt.Chart(rule_df).mark_rule(color="#1f6f8b", strokeDash=[4, 3], size=2)
                      .encode(x="x:Q"))
    st.altair_chart(alt.layer(*layers).properties(height=alt.Step(46)), width="stretch")

# ---- Table ------------------------------------------------------------------
st.subheader("Postings")
table = pd.DataFrame({
    "Posting": view["title"],
    "Employer": view["employer"],
    "Date": view["posted_month"],
    "Level": view["level"],
    "Annual min": view["annual_min"],
    "Annual max": view["annual_max"],
    "Experience": [experience_text(a, b) or "Not listed"
                   for a, b in zip(view["years_exp_min"], view["years_exp_max"])],
    "PE": view["pe_required"].fillna("Not listed"),
    "As posted": [as_posted_text(a, b, p) for a, b, p in
                  zip(view["pay_min"], view["pay_max"], view["pay_period"])],
    "Location": view["location"],
    "Source": view["source"],
    "Link": view["url"],
})
picked = st.dataframe(
    table, hide_index=True, width="stretch", key="postings_table",
    on_select="rerun", selection_mode="single-row",
    column_config={
        "Date": st.column_config.DateColumn("Date", format="MMM YYYY",
                                            help="Month posted, or first seen on CASFM"),
        "Annual min": st.column_config.NumberColumn(format="$%,.0f"),
        "Annual max": st.column_config.NumberColumn(format="$%,.0f"),
        "Link": st.column_config.LinkColumn("Link", display_text="Open"),
    },
)
st.caption("Click a row to see what the job asks for. Click a column heading to sort. Level is "
           "inferred from the job title and experience when the posting doesn't say.")
rows = picked.selection.rows if picked is not None else []
if rows:
    show_details(view.iloc[rows[0]])
else:
    st.info("Select a posting in the table to see its summary, duties, required "
            "qualifications and desired traits here.")

st.download_button("Download these postings (CSV)", table.to_csv(index=False).encode(),
                   file_name="front_range_engineering_pay.csv", mime="text/csv")
