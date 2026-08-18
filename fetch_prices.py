"""
fetch_prices.py
----------------
Pulls today's petrol and diesel prices for major Indian cities from
GoodReturns.in — a public webpage, no login, no API key needed.
Appends the results to a local SQLite database so it builds up a
day-by-day price history over time.

This is designed to be run automatically once a day (via the GitHub
Actions workflow in .github/workflows/update_prices.yml), so the
database keeps growing on its own.
"""

import io
import os
import sqlite3
from datetime import date

import pandas as pd
import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "prices.db")

PAGES = {
    "Petrol": "https://www.goodreturns.in/petrol-price.html",
    "Diesel": "https://www.goodreturns.in/diesel-price.html",
}

HEADERS = {
    # A normal browser user-agent, so the site serves the regular page
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def fetch_city_table(fuel_type: str, url: str) -> pd.DataFrame:
    """Downloads the page and pulls out the 'Metro Cities & State Capitals' table."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    tables = pd.read_html(io.StringIO(resp.text))

    # Find the table that has City / Price / Price Change columns
    target = None
    for t in tables:
        cols = [str(c).strip().lower() for c in t.columns]
        if "city" in cols and "price" in cols:
            target = t
            break

    if target is None:
        raise ValueError(f"Could not find the city price table on {url}")

    target = target.rename(columns={c: str(c).strip() for c in target.columns})
    target["fuel_type"] = fuel_type
    return target[["fuel_type", "City", "Price", "Price Change"]]


def clean_price(value) -> float:
    """Turns '₹111.31' or similar text into a plain float."""
    if pd.isna(value):
        return None
    text = str(value).replace("₹", "").replace(",", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fuel_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_collected TEXT NOT NULL,
            fuel_type TEXT NOT NULL,
            city TEXT NOT NULL,
            price REAL,
            price_change REAL
        )
        """
    )
    conn.commit()


def insert_rows(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    today = date.today().isoformat()
    rows = [
        (
            today,
            row["fuel_type"],
            row["City"],
            clean_price(row["Price"]),
            clean_price(row["Price Change"]),
        )
        for _, row in df.iterrows()
    ]

    conn.executemany(
        """
        INSERT INTO fuel_prices (date_collected, fuel_type, city, price, price_change)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    total_inserted = 0
    for fuel_type, url in PAGES.items():
        print(f"Fetching {fuel_type} prices from {url} ...")
        df = fetch_city_table(fuel_type, url)
        inserted = insert_rows(conn, df)
        total_inserted += inserted
        print(f"  -> inserted {inserted} {fuel_type} rows")

    print(f"Done. Total rows inserted today: {total_inserted}")
    conn.close()


if __name__ == "__main__":
    main()
