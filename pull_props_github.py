# pull_props.py
# Pull MLB player props using The Odds API

import requests
import pandas as pd
from config_github import BASE_DIR

# ============================
# CONFIG
# ============================

API_KEY = "09f8bf6699fc944dec706ca8eb5e99ea"  # <-- replace this

SPORT = "baseball_mlb"
REGIONS = "us"
ODDS_FORMAT = "american"
TARGET_BOOKMAKER = "FanDuel"

# Output file
OUTPUT_PATH = f"{BASE_DIR}/sportsbook_lines.csv"

# ============================
# STEP 1: GET MLB EVENTS
# ============================

events_url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events"

params = {
    "apiKey": API_KEY
}

print("Fetching MLB events...")

events_response = requests.get(events_url, params=params)

print(events_response.status_code)
print(events_response.text)

events = events_response.json()

print(f"Found {len(events)} events")

# ============================
# STEP 2: LOOP THROUGH EVENTS
# ============================

all_props = []

for event in events:
    event_id = event["id"]
    commence_time = event["commence_time"]

    print(f"Processing event: {event_id}")

    odds_url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{event_id}/odds"

    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "oddsFormat": ODDS_FORMAT,
        "markets": "pitcher_strikeouts"
    }

    odds_response = requests.get(odds_url, params=params)

    if odds_response.status_code != 200:
        print(f"Failed to fetch odds for event {event_id}")
        continue

    data = odds_response.json()

    print(data.keys())
    print([b["title"] for b in data.get("bookmakers", [])])

    # ============================
    # STEP 3: PARSE DATA
    # ============================

    bookmakers = data.get("bookmakers", [])

    for book in bookmakers:
        book_name = book["title"]

        if book_name != TARGET_BOOKMAKER:
            continue

        for market in book.get("markets", []):

            print(book_name, market["key"])

            if "strikeout" not in market["key"]:
                continue

            for outcome in market.get("outcomes", []):

                player_name = outcome.get("description")
                line = outcome.get("point")
                odds = outcome.get("price")
                side = outcome.get("name")  # Over / Under

                all_props.append({
                    "date": pd.to_datetime(commence_time, utc=True).strftime("%Y-%m-%d"),
                    "bookmaker": book_name,
                    "player_name": player_name,
                    "line": line,
                    "side": side,
                    "odds": odds
                })

# ============================
# STEP 4: SAVE
# ============================

df = pd.DataFrame(all_props)

if df.empty:
    print("No props found. (Likely API limitation on free tier or no lines posted yet)")
else:
    print(df.head())

df.to_csv(OUTPUT_PATH, index=False)
print(f"Saved to: {OUTPUT_PATH}")