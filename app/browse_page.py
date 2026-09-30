"""Browse approved postings: filters, a pay-range chart with a compare line, and a sortable table."""
import altair as alt
import pandas as pd
import streamlit as st

from common import get_conn
from salaries.postings import LEVELS, PE_OPTIONS, as_posted_text, experience_text, load

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
c1, c2, c3, c4 = st.columns([2, 2, 2, 1.4])
query = c1.text_input("Search", placeholder="Title, employer, city")
levels = c2.multiselect("Level", LEVELS, placeholder="All levels")
pe = c3.multiselect("PE", PE_OPTIONS + ["Not listed"], placeholder="Any")
compare = c4.number_input("Compare a salary ($/yr)", min_value=0, step=1000, value=0,
                          help="Draws a line on the chart and counts how many ranges it falls in.")

view = df.copy()
if query:
    text = (view["title"] + " " + view["employer"] + " " + view["location"]).str.lower()
    view = view[text.str.contains(query.lower(), regex=False)]
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
        label=paid["title"] + " · " + paid["employer"],
        mid=(paid["annual_min"] + paid["annual_max"]) / 2,
        level=paid["level"].fillna("Not set"),
    ).sort_values("mid")
    order = chart_df["label"].tolist()
    y = alt.Y("label:N", sort=order, title=None, axis=alt.Axis(labelLimit=320, labelOverlap=False))
    bars = alt.Chart(chart_df).mark_bar(height=10, cornerRadius=5).encode(
        x=alt.X("annual_min:Q", title="Annual pay", axis=alt.Axis(format="$,.0f"),
                  scale=alt.Scale(zero=False, nice=True)),
        x2="annual_max:Q",
        y=y,
        color=alt.Color("level:N", title="Level",
                        scale=alt.Scale(domain=LEVELS + ["Not set"], range=LEVEL_COLORS + ["#97a4ad"])),
        tooltip=[alt.Tooltip("title:N", title="Posting"), alt.Tooltip("employer:N", title="Employer"),
                 alt.Tooltip("annual_min:Q", title="From", format="$,.0f"),
                 alt.Tooltip("annual_max:Q", title="To", format="$,.0f"),
                 alt.Tooltip("level:N", title="Level")],
    )
    layers = [bars]
    if compare:
        rule_df = pd.DataFrame({"x": [compare]})
        layers.append(alt.Chart(rule_df).mark_rule(color="#1f6f8b", strokeDash=[4, 3], size=2)
                      .encode(x="x:Q"))
    st.altair_chart(alt.layer(*layers).properties(height=40 * len(chart_df) + 20),
                    use_container_width=True)

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
st.dataframe(
    table, hide_index=True, use_container_width=True,
    column_config={
        "Date": st.column_config.DateColumn("Date", format="MMM YYYY",
                                            help="Month posted, or first seen on CASFM"),
        "Annual min": st.column_config.NumberColumn(format="$%,.0f"),
        "Annual max": st.column_config.NumberColumn(format="$%,.0f"),
        "Link": st.column_config.LinkColumn("Link", display_text="Open"),
    },
)
st.caption("Click a column heading to sort. Level is inferred from the job title and experience "
           "when the posting doesn't say.")
st.download_button("Download these postings (CSV)", table.to_csv(index=False).encode(),
                   file_name="front_range_engineering_pay.csv", mime="text/csv")
