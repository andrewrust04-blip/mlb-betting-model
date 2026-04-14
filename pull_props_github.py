# pull_props_github.py
# Pull MLB pitcher strikeout props using The Odds API
# Based on old working version:
#   1. Get MLB events
#   2. Loop through events
#   3. Pull event-specific odds for pitcher_strikeouts
#   4. Save sportsbook_lines.csv
#
# Updated to:
#   - use GitHub secret via ODDS_API_KEY
#   - fail safely
#   - write empty file (headers only) if API fails or no props are found

import os
import requests
import pandas as pd
from config_github import BASE_DIR

# ============================
# CONFIG
# ============================

API_KEY = os.getenv("ODDS_API_KEY")
if not API_KEY:
    raise ValueError("ODDS_API_KEY environment variable not found.")

SPORT = "baseball_mlb"
REGIONS = "us"
ODDS_FORMAT = "american"
DATE_FORMAT = "iso"
TARGET_BOOKMAKER = "FanDuel"

OUTPUT_PATH = f"{BASE_DIR}/sportsbook_lines.csv"

# ============================
# HELPER: WRITE EMPTY FILE
# ============================

def write_empty_props_file():
    empty_df = pd.DataFrame(columns=[
        "date",
        "bookmaker",
        "player_name",
        "line",
        "side",
        "odds"
    ])
    empty_df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote EMPTY sportsbook lines file -> {OUTPUT_PATH}")

# ============================
# STEP 1: GET MLB EVENTS
# ============================

events_url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events"
events_params = {
    "apiKey": API_KEY,
    "dateFormat": DATE_FORMAT,
}

print("Fetching MLB events...")

try:
    events_response = requests.get(events_url, params=events_params, timeout=30)
except Exception as e:
    print(f"Failed to fetch MLB events: {e}")
    write_empty_props_file()
    raise SystemExit(0)

print(f"Events status code: {events_response.status_code}")

if events_response.status_code != 200:
    print("Events request failed.")
    print(f"Response text: {events_response.text}")
    write_empty_props_file()
    raise SystemExit(0)

try:
    events = events_response.json()
except Exception as e:
    print(f"Failed to parse events JSON: {e}")
    write_empty_props_file()
    raise SystemExit(0)

if not isinstance(events, list) or len(events) == 0:
    print("No MLB events returned.")
    write_empty_props_file()
    raise SystemExit(0)

print(f"Found {len(events)} events")

# ============================
# STEP 2: LOOP THROUGH EVENTS
# ============================

all_props = []

for event in events:
    event_id = event.get("id")
    commence_time = event.get("commence_time")

    if not event_id or not commence_time:
        continue

    print(f"Processing event: {event_id}")

    odds_url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{event_id}/odds"
    odds_params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "oddsFormat": ODDS_FORMAT,
        "dateFormat": DATE_FORMAT,
        "markets": "pitcher_strikeouts"
    }

    try:
        odds_response = requests.get(odds_url, params=odds_params, timeout=30)
    except Exception as e:
        print(f"Failed to fetch odds for event {event_id}: {e}")
        continue

    print(f"Event {event_id} status code: {odds_response.status_code}")

    if odds_response.status_code != 200:
        print(f"Failed to fetch odds for event {event_id}")
        print(f"Response text: {odds_response.text}")
        continue

    try:
        data = odds_response.json()
    except Exception as e:
        print(f"Failed to parse odds JSON for event {event_id}: {e}")
        continue

    bookmakers = data.get("bookmakers", [])

    for book in bookmakers:
        book_name = book.get("title", "")

        # Match exactly like your old working version
        if book_name != TARGET_BOOKMAKER:
            continue

        for market in book.get("markets", []):
            market_key = str(market.get("key", "")).lower()

            if "strikeout" not in market_key:
                continue

            for outcome in market.get("outcomes", []):
                player_name = outcome.get("description")
                line = outcome.get("point")
                odds = outcome.get("price")
                side = outcome.get("name")  # Over / Under

                if pd.isna(player_name) or pd.isna(line) or pd.isna(odds) or pd.isna(side):
                    continue

                try:
                    event_date = (
                        pd.to_datetime(commence_time, utc=True)
                        .tz_convert("America/New_York")
                        .strftime("%Y-%m-%d")
                    )
                except Exception:
                    continue

                all_props.append({
                    "date": event_date,
                    "bookmaker": book_name,
                    "player_name": player_name,
                    "line": line,
                    "side": str(side).strip().lower(),
                    "odds": odds
                })

# ============================
# STEP 3: BUILD DATAFRAME
# ============================

df = pd.DataFrame(all_props)

if df.empty:
    print("No props found. Likely no lines posted yet or market unavailable.")
    write_empty_props_file()
    raise SystemExit(0)

df["line"] = pd.to_numeric(df["line"], errors="coerce")
df["odds"] = pd.to_numeric(df["odds"], errors="coerce")

df = df.dropna(subset=["player_name", "line", "side", "odds"]).copy()

if df.empty:
    print("Props empty after cleaning.")
    write_empty_props_file()
    raise SystemExit(0)

df = df.sort_values(["date", "player_name", "line", "side"]).reset_index(drop=True)

# ============================
# STEP 4: SAVE FILE
# ============================

print("\nSample props:")
print(df.head(10).to_string(index=False))

df.to_csv(OUTPUT_PATH, index=False)
print(f"\nSaved to: {OUTPUT_PATH}")
print("pull_props_github.py complete.")
