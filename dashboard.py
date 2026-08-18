"""
dashboard.py
------------
Streamlit dashboard for the auto-updating petrol/diesel price dataset.
Run locally with:  streamlit run dashboard.py
Or deploy free on Streamlit Community Cloud pointing at this file.
"""

import os
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "prices.db")

st.set_page_config(page_title="Live Fuel Price Tracker", layout="wide")
st.title("⛽ Live Petrol & Diesel Price Tracker")
st.caption("Auto-updated daily from GoodReturns.in — city-wise fuel prices across India.")


@st.cache_data(ttl=3600)
def load_data() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM fuel_prices", conn)
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
fuel_type = st.sidebar.radio("Fuel type", sorted(df["fuel_type"].unique()))

cities = sorted(df[df["fuel_type"] == fuel_type]["city"].dropna().unique())
selected_cities = st.sidebar.multiselect("Cities", cities, default=cities[:5] if cities else [])

filtered = df[df["fuel_type"] == fuel_type]
if selected_cities:
    filtered = filtered[filtered["city"].isin(selected_cities)]

# ---------- KPIs ----------
col1, col2, col3 = st.columns(3)
latest_date = filtered["date_collected"].max()
latest = filtered[filtered["date_collected"] == latest_date]

col1.metric(f"Latest Avg {fuel_type} Price", f"₹{latest['price'].mean():,.2f}")
col2.metric("Days of Data Collected", df["date_collected"].nunique())
col3.metric("Cities Tracked", filtered["city"].nunique())

# ---------- Trend chart ----------
daily_avg = (
    filtered.groupby("date_collected")["price"]
    .mean()
    .reset_index()
    .sort_values("date_collected")
)

fig = px.line(
    daily_avg,
    x="date_collected",
    y="price",
    title=f"{fuel_type} — Average Price Over Time (selected cities)",
    markers=True,
)
fig.update_layout(yaxis_title="Price (₹ per litre)", xaxis_title="Date")
st.plotly_chart(fig, use_container_width=True)

# ---------- % change callout ----------
if len(daily_avg) >= 2:
    first_price = daily_avg.iloc[0]["price"]
    last_price = daily_avg.iloc[-1]["price"]
    pct_change = ((last_price - first_price) / first_price) * 100 if first_price else 0
    direction = "🔺 up" if pct_change > 0 else "🔻 down"
    st.info(
        f"**{fuel_type}** is {direction} **{abs(pct_change):.2f}%** "
        f"since tracking began on {daily_avg.iloc[0]['date_collected'].date()}."
    )

# ---------- City comparison table ----------
st.subheader(f"Latest {fuel_type} Prices by City")
latest_table = (
    latest[["city", "price", "price_change"]]
    .sort_values("price")
    .reset_index(drop=True)
)
st.dataframe(latest_table, use_container_width=True)

# ---------- Raw data ----------
with st.expander("View raw data"):
    st.dataframe(filtered.sort_values("date_collected", ascending=False), use_container_width=True)
