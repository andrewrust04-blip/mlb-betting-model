# pull_props_github.py
# Pull MLB pitcher strikeout props using The Odds API
# UPDATED: uses events endpoint + event-odds endpoint for player props
# Writes empty file (headers only) if API fails or no props

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
MARKETS = "pitcher_strikeouts"
ODDS_FORMAT = "american"
DATE_FORMAT = "iso"
TARGET_BOOKMAKER = "fanduel"

OUTPUT_PATH = f"{BASE_DIR}/sportsbook_lines.csv"

EVENTS_URL = f"https://api.the-odds-api.com/v4/sports/{SPORT}/events"

# Player props must be pulled per event:
# /v4/sports/{sport}/events/{eventId}/odds
def event_odds_url(event_id):
    return f"https://api.the-odds-api.com/v4/sports/{SPORT}/events/{event_id}/odds"

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
# HELPER: SAFE GET
# ============================

def safe_get(url, params, timeout=30):
    try:
        response = requests.get(url, params=params, timeout=timeout)
        return response
    except Exception as e:
        print(f"Request failed for {url}: {e}")
        return None

# ============================
# STEP 1: GET EVENTS
# ============================

print("Fetching MLB events...")

events_params = {
    "apiKey": API_KEY,
    "dateFormat": DATE_FORMAT,
}

events_response = safe_get(EVENTS_URL, events_params, timeout=30)

if events_response is None:
    write_empty_props_file()
    raise SystemExit(0)

print(f"Events status code: {events_response.status_code}")

if events_response.status_code != 200:
    print("Events pull failed.")
    print(f"Response text: {events_response.text}")
    write_empty_props_file()
    raise SystemExit(0)

try:
    events_data = events_response.json()
except Exception as e:
    print(f"Failed to parse events JSON: {e}")
    write_empty_props_file()
    raise SystemExit(0)

if not isinstance(events_data, list) or len(events_data) == 0:
    print("No MLB events returned.")
    write_empty_props_file()
    raise SystemExit(0)

print(f"Found {len(events_data)} MLB events")

# ============================
# STEP 2: GET PROPS FOR EACH EVENT
# ============================

all_props = []
successful_event_calls = 0

for event in events_data:
    event_id = event.get("id")
    commence_time = event.get("commence_time")

    if not event_id:
        continue

    odds_params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
        "dateFormat": DATE_FORMAT,
        "bookmakers": TARGET_BOOKMAKER,
    }

    response = safe_get(event_odds_url(event_id), odds_params, timeout=30)

    if response is None:
        print(f"Skipping event {event_id}: request failed")
        continue

    print(f"Event {event_id} status code: {response.status_code}")

    if response.status_code != 200:
        print(f"Skipping event {event_id}: bad status")
        print(f"Response text: {response.text}")
        continue

    try:
        event_data = response.json()
    except Exception as e:
        print(f"Skipping event {event_id}: JSON parse failed: {e}")
        continue

    successful_event_calls += 1

    bookmakers = event_data.get("bookmakers", [])
    if not bookmakers:
        continue

    # Convert event start time to NY date
    try:
        event_date = (
            pd.to_datetime(commence_time, utc=True)
            .tz_convert("America/New_York")
            .strftime("%Y-%m-%d")
        )
    except Exception:
        continue

    for book in bookmakers:
        book_key = str(book.get("key", "")).lower()
        if book_key != TARGET_BOOKMAKER:
            continue

        book_title = book.get("title", "FanDuel")

        for market in book.get("markets", []):
            if str(market.get("key", "")).lower() != MARKETS:
                continue

            for outcome in market.get("outcomes", []):
                player_name = outcome.get("description")
                line = outcome.get("point")
                odds = outcome.get("price")
                side = outcome.get("name")

                if pd.isna(player_name) or pd.isna(line) or pd.isna(odds) or pd.isna(side):
                    continue

                all_props.append({
                    "date": event_date,
                    "bookmaker": book_title,
                    "player_name": player_name,
                    "line": line,
                    "side": str(side).strip().lower(),
                    "odds": odds
                })

print(f"Successful event-odds calls: {successful_event_calls}")
print(f"Raw props collected: {len(all_props)}")

# ============================
# STEP 3: BUILD DATAFRAME
# ============================

df = pd.DataFrame(all_props)

if df.empty:
    print("No valid pitcher strikeout props found.")
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

print(f"\nSaved sportsbook lines to: {OUTPUT_PATH}")
print("pull_props_github.py complete.")
