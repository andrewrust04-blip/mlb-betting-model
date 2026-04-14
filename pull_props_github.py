# pull_props_github.py
# Pull MLB pitcher strikeout props using The Odds API
# Optimized to use ONE odds request per run (instead of looping through every event)

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
TARGET_BOOKMAKER = "fanduel"   # Odds API bookmaker key, not display name

OUTPUT_PATH = f"{BASE_DIR}/sportsbook_lines.csv"

# Single-call odds endpoint
ODDS_URL = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"

params = {
    "apiKey": API_KEY,
    "regions": REGIONS,
    "markets": MARKETS,
    "oddsFormat": ODDS_FORMAT,
    "dateFormat": DATE_FORMAT,
    "bookmakers": TARGET_BOOKMAKER,
}

print("Fetching MLB pitcher strikeout props in one request...")
response = requests.get(ODDS_URL, params=params, timeout=30)

print(f"Status code: {response.status_code}")

# ============================
# FAIL SAFELY — DO NOT OVERWRITE OLD FILE
# ============================

if response.status_code != 200:
    print("Props pull failed.")
    print(f"Response text: {response.text}")
    print(f"Keeping existing file unchanged: {OUTPUT_PATH}")
    raise SystemExit(0)

try:
    data = response.json()
except Exception as e:
    print(f"Failed to parse JSON response: {e}")
    print(f"Keeping existing file unchanged: {OUTPUT_PATH}")
    raise SystemExit(0)

if not isinstance(data, list) or len(data) == 0:
    print("Odds API returned no events.")
    print(f"Keeping existing file unchanged: {OUTPUT_PATH}")
    raise SystemExit(0)

print(f"Found {len(data)} events in odds response")

# ============================
# PARSE DATA
# ============================

all_props = []

for event in data:
    commence_time = event.get("commence_time")
    bookmakers = event.get("bookmakers", [])

    if not bookmakers:
        continue

    # Convert event start time to Eastern date for your workflow / dashboard
    event_date = pd.to_datetime(commence_time, utc=True).tz_convert("America/New_York").strftime("%Y-%m-%d")

    for book in bookmakers:
        book_key = str(book.get("key", "")).lower()

        if book_key != TARGET_BOOKMAKER:
            continue

        book_title = book.get("title", "FanDuel")

        for market in book.get("markets", []):
            market_key = str(market.get("key", "")).lower()

            if market_key != MARKETS:
                continue

            for outcome in market.get("outcomes", []):
                player_name = outcome.get("description")
                line = outcome.get("point")
                odds = outcome.get("price")
                side = outcome.get("name")  # Over / Under

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

# ============================
# SAVE ONLY IF VALID DATA EXISTS
# ============================

df = pd.DataFrame(all_props)

if df.empty:
    print("No valid FanDuel pitcher strikeout props found.")
    print(f"Keeping existing file unchanged: {OUTPUT_PATH}")
    raise SystemExit(0)

# Clean types
df["line"] = pd.to_numeric(df["line"], errors="coerce")
df["odds"] = pd.to_numeric(df["odds"], errors="coerce")
df = df.dropna(subset=["player_name", "line", "side", "odds"]).copy()

if df.empty:
    print("Props file became empty after cleaning.")
    print(f"Keeping existing file unchanged: {OUTPUT_PATH}")
    raise SystemExit(0)

df = df.sort_values(["date", "player_name", "line", "side"]).reset_index(drop=True)

print("\nSample props:")
print(df.head(10).to_string(index=False))

df.to_csv(OUTPUT_PATH, index=False)
print(f"\nSaved sportsbook lines to: {OUTPUT_PATH}")
print("pull_props_github.py complete.")
