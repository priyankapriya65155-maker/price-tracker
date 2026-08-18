# ⛽ Live Petrol & Diesel Price Tracker

A self-updating dashboard that tracks daily petrol and diesel prices across
14 Indian cities — no static dataset, no manual downloads. A scraper runs
automatically every day, stores the results, and a live dashboard reflects
the latest data the moment it's collected.

**🔗 Live dashboard:** https://price-tracker-g5infnvqoztmyjvkymsat2.streamlit.app/

---

## Why I built this

Most portfolio projects analyze a dataset that's already been collected —
Titanic, IPL scores, a Kaggle CSV. I wanted to build something that
collects its *own* data, every day, without me touching it. Fuel prices
change daily and there's no clean, permission-free API for it, so I built
a small pipeline that reads the same public price tables a person would
see by visiting the page directly, and turns that into a growing time
series automatically.

## How it works

```
 ┌──────────────────┐     ┌───────────────┐     ┌──────────────────────┐
 │ GitHub Actions    │────▶│ fetch_prices  │────▶│  data/prices.db       │
 │ (daily cron job)  │     │     .py       │     │  (SQLite, appends —   │
 └──────────────────┘     └───────────────┘     │   never overwrites)   │
                                                   └──────────┬────────────┘
                                                              │
                                                              ▼
                                                   ┌──────────────────────┐
                                                   │   dashboard.py        │
                                                   │ (Streamlit, reads     │
                                                   │  live from the DB)    │
                                                   └──────────────────────┘
```

1. **`fetch_prices.py`** — visits GoodReturns.in's petrol and diesel price
   pages, extracts the city-price table, and appends today's prices to a
   SQLite database with a `date_collected` column. Every run adds new
   rows; nothing is ever overwritten, so the database becomes a real
   historical record over time.
2. **`.github/workflows/update_prices.yml`** — a GitHub Actions workflow
   that runs `fetch_prices.py` once a day on a cron schedule, then commits
   the updated database straight back into the repo. This is what makes
   the project "live" — it runs on GitHub's servers, not my own machine.
3. **`dashboard.py`** — a Streamlit app that reads the database and shows:
   - Latest average price and day-over-day % change
   - A price trend line as more days of data accumulate
   - A city-by-city comparison table
   - Filters for fuel type (petrol/diesel) and city

## Tech stack
`Python` · `pandas` · `requests` · `SQLite` · `Streamlit` · `Plotly` · `GitHub Actions`

## Project structure
```
price-tracker/
├── fetch_prices.py               # daily scraper → SQLite
├── dashboard.py                  # Streamlit dashboard
├── requirements.txt
├── data/
│   └── prices.db                 # grows daily, committed by Actions
└── .github/workflows/
    └── update_prices.yml         # the "alarm clock" — daily cron
```

## Running it yourself

```bash
pip install -r requirements.txt
python fetch_prices.py       # pulls today's prices into data/prices.db
streamlit run dashboard.py   # view the dashboard locally
```

No API key or signup required — the whole pipeline runs on public,
freely accessible pages.

To get your own copy auto-updating daily: fork this repo, and GitHub
Actions will start running the scraper on its own schedule (or trigger it
manually from the **Actions** tab any time).

## What I'd add next
- LPG price tracking, using the same scrape-and-append pattern
- A petrol-vs-diesel price gap chart over time
- Alerts/flags when a city's price jumps more than a set threshold in a day
- Comparing tracked price trends against major news events (tax changes,
  crude oil price swings)

## About this project
Built as a data analytics portfolio project to demonstrate: automated
data pipelines, working with real (not pre-cleaned) data, scheduling and
orchestration, and shipping a usable end product rather than just a
notebook.
