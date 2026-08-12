"""
fetch_prices.py
----------------
Pulls today's commodity (mandi/vegetable) prices from the official
Agmarknet dataset on data.gov.in, and appends them to a local SQLite
database. Designed to be run daily (manually, or via GitHub Actions cron)
so the database grows into a real historical time series.

Setup:
    1. Get a free API key: data.gov.in -> sign up -> My Account -> API Keys
    2. Set it as an environment variable AGMARKNET_API_KEY
       (locally: export AGMARKNET_API_KEY=xxxx
        in GitHub Actions: add it as a repo secret, see workflow file)
    3. Edit STATE / COMMODITIES below to whatever you want to track.
"""

import os
import sqlite3
import sys
from datetime import date

import requests

# ---------- CONFIG ----------
API_KEY = os.environ.get("AGMARKNET_API_KEY")
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"  # Agmarknet daily mandi prices
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "prices.db")

# Filter to a state and a handful of commodities to keep the dataset focused.
# Leave COMMODITIES = [] to pull everything for the state (larger, slower).
STATE = "Telangana"
COMMODITIES = ["Onion", "Tomato", "Potato", "Rice", "Wheat"]

PAGE_LIMIT = 500  # records per API page (API max is usually 1000-2000)
# ---------- END CONFIG ----------


def fetch_page(offset: int, commodity: str | None = None) -> list[dict]:
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": PAGE_LIMIT,
        "offset": offset,
        "filters[state]": STATE,
    }
    if commodity:
        params["filters[commodity]"] = commodity

    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    return payload.get("records", [])


def fetch_all_records() -> list[dict]:
    all_records = []
    commodities_to_pull = COMMODITIES if COMMODITIES else [None]

    for commodity in commodities_to_pull:
        offset = 0
        while True:
            records = fetch_page(offset, commodity)
            if not records:
                break
            all_records.extend(records)
            offset += PAGE_LIMIT
            if len(records) < PAGE_LIMIT:
                break  # last page for this commodity

    return all_records


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mandi_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_collected TEXT NOT NULL,
            arrival_date TEXT,
            state TEXT,
            district TEXT,
            market TEXT,
            commodity TEXT,
            variety TEXT,
            min_price REAL,
            max_price REAL,
            modal_price REAL
        )
        """
    )
    conn.commit()


def insert_records(conn: sqlite3.Connection, records: list[dict]) -> int:
    today = date.today().isoformat()
    rows = []
    for r in records:
        try:
            rows.append(
                (
                    today,
                    r.get("arrival_date"),
                    r.get("state"),
                    r.get("district"),
                    r.get("market"),
                    r.get("commodity"),
                    r.get("variety"),
                    float(r.get("min_price") or 0),
                    float(r.get("max_price") or 0),
                    float(r.get("modal_price") or 0),
                )
            )
        except (TypeError, ValueError):
            continue  # skip malformed rows rather than crash the whole run

    conn.executemany(
        """
        INSERT INTO mandi_prices
        (date_collected, arrival_date, state, district, market,
         commodity, variety, min_price, max_price, modal_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def main():
    if not API_KEY:
        print("ERROR: AGMARKNET_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    print(f"Fetching prices for state={STATE}, commodities={COMMODITIES or 'ALL'}...")
    records = fetch_all_records()
    print(f"Fetched {len(records)} raw records from Agmarknet.")

    inserted = insert_records(conn, records)
    print(f"Inserted {inserted} rows into {DB_PATH}.")

    conn.close()


if __name__ == "__main__":
    main()
