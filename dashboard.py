"""
dashboard.py
------------
Streamlit dashboard for the auto-updating mandi price dataset.
Run locally with:  streamlit run dashboard.py
Or deploy free on Streamlit Community Cloud pointing at this file.
"""

import os
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "prices.db")

st.set_page_config(page_title="Live Mandi Price Tracker", layout="wide")
st.title("📈 Live Commodity Price Tracker")
st.caption("Auto-updated daily from the official Agmarknet (data.gov.in) mandi price feed.")


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM mandi_prices", conn)
    conn.close()
    df["date_collected"] = pd.to_datetime(df["date_collected"])
    return df


if not os.path.exists(DB_PATH):
    st.warning("No data yet. Run `python fetch_prices.py` at least once to create the database.")
    st.stop()

df = load_data()

if df.empty:
    st.warning("Database exists but has no rows yet. Run fetch_prices.py to pull data.")
    st.stop()

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
commodities = sorted(df["commodity"].dropna().unique())
selected_commodity = st.sidebar.selectbox("Commodity", commodities)

districts = sorted(df[df["commodity"] == selected_commodity]["district"].dropna().unique())
selected_district = st.sidebar.multiselect("District (optional)", districts, default=districts[:3] if districts else [])

filtered = df[df["commodity"] == selected_commodity]
if selected_district:
    filtered = filtered[filtered["district"].isin(selected_district)]

# ---------- KPIs ----------
col1, col2, col3 = st.columns(3)
latest_date = filtered["date_collected"].max()
latest = filtered[filtered["date_collected"] == latest_date]

col1.metric("Latest Modal Price (avg)", f"₹{latest['modal_price'].mean():,.0f}")
col2.metric("Days of Data Collected", df["date_collected"].nunique())
col3.metric("Markets Tracked", filtered["market"].nunique())

# ---------- Trend chart ----------
daily_avg = (
    filtered.groupby("date_collected")["modal_price"]
    .mean()
    .reset_index()
    .sort_values("date_collected")
)

fig = px.line(
    daily_avg,
    x="date_collected",
    y="modal_price",
    title=f"{selected_commodity} — Average Modal Price Over Time",
    markers=True,
)
fig.update_layout(yaxis_title="Price (₹ per quintal)", xaxis_title="Date")
st.plotly_chart(fig, use_container_width=True)

# ---------- % change callout ----------
if len(daily_avg) >= 2:
    first_price = daily_avg.iloc[0]["modal_price"]
    last_price = daily_avg.iloc[-1]["modal_price"]
    pct_change = ((last_price - first_price) / first_price) * 100 if first_price else 0
    direction = "🔺 up" if pct_change > 0 else "🔻 down"
    st.info(
        f"**{selected_commodity}** is {direction} **{abs(pct_change):.1f}%** "
        f"since tracking began on {daily_avg.iloc[0]['date_collected'].date()}."
    )

# ---------- Market comparison table ----------
st.subheader("Latest Prices by Market")
latest_table = (
    latest[["market", "district", "min_price", "max_price", "modal_price"]]
    .sort_values("modal_price")
    .reset_index(drop=True)
)
st.dataframe(latest_table, use_container_width=True)

# ---------- Raw data ----------
with st.expander("View raw data"):
    st.dataframe(filtered.sort_values("date_collected", ascending=False), use_container_width=True)
