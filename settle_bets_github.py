# settle_bets.py
# Settle previously logged MLB pitcher strikeout bets.
#
# Outputs:
#   - updated bet_log.csv   (pipeline source of truth)
#   - updated bet_log.xlsx  (formatted, for viewing)

import warnings
warnings.filterwarnings("ignore")

import os
import numpy as np
import pandas as pd

try:
    from pybaseball import statcast
except ImportError:
    raise ImportError("Run: pip install pybaseball")

from config_github import BET_LOG_PATH
from export_excel_github import export_bet_log

# =============================================================================
# HELPERS
# =============================================================================

def calc_profit_units(odds, bet_result):
    if pd.isna(odds): return np.nan
    odds = float(odds)
    if bet_result == "win":
        return round(100.0 / abs(odds), 4) if odds < 0 else round(odds / 100.0, 4)
    if bet_result == "loss":  return -1.0
    if bet_result == "push":  return  0.0
    return np.nan

def normalize_bet_log_types(df):
    df = df.copy()
    df["date"]       = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    df["pitcher_id"] = pd.to_numeric(df["pitcher_id"], errors="coerce")
    df["line"]       = pd.to_numeric(df["line"], errors="coerce")
    df["odds"]       = pd.to_numeric(df["odds"], errors="coerce")
    if "actual_strikeouts" not in df.columns: df["actual_strikeouts"] = np.nan
    if "bet_result"        not in df.columns: df["bet_result"]        = ""
    if "profit_units"      not in df.columns: df["profit_units"]      = np.nan
    if "settled"           not in df.columns: df["settled"]           = False
    df["settled"] = df["settled"].astype(str).str.lower().map({"true": True, "false": False}).fillna(df["settled"])
    return df

def build_daily_pitcher_strikeout_table(target_date):
    date_str = pd.to_datetime(target_date).strftime("%Y-%m-%d")
    print(f"Pulling Statcast for {date_str} ...")
    raw = statcast(start_dt=date_str, end_dt=date_str)
    if raw is None or raw.empty:
        print(f"No Statcast rows returned for {date_str}")
        return pd.DataFrame(columns=["game_date", "pitcher_id", "actual_strikeouts"])

    required_cols = ["game_date", "game_pk", "pitcher", "batter",
                     "inning", "inning_topbot", "at_bat_number", "pitch_number", "events"]
    missing = [c for c in required_cols if c not in raw.columns]
    if missing: raise ValueError(f"Missing Statcast columns for settlement: {missing}")

    df = raw[required_cols].copy()
    df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce").dt.normalize()
    for col in ["pitcher", "batter", "inning", "at_bat_number", "pitch_number"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["game_date", "pitcher", "batter", "inning",
                            "inning_topbot", "at_bat_number", "pitch_number"]).copy()

    df = df.sort_values(["game_pk", "pitcher", "batter", "inning",
                          "inning_topbot", "at_bat_number", "pitch_number"]).reset_index(drop=True)
    pa_df = df.groupby(["game_pk", "pitcher", "batter", "inning",
                         "inning_topbot", "at_bat_number"], as_index=False, sort=False).tail(1).copy()
    pa_df["is_strikeout"] = pa_df["events"].astype(str).str.lower().isin(
        ["strikeout", "strikeout_double_play"]).astype(int)

    out = (pa_df.groupby(["game_date", "pitcher"], as_index=False)
           .agg(actual_strikeouts=("is_strikeout", "sum"))
           .rename(columns={"pitcher": "pitcher_id"}))
    out["pitcher_id"] = pd.to_numeric(out["pitcher_id"], errors="coerce")
    return out

def grade_bet(actual_strikeouts, line, bet_side):
    if pd.isna(actual_strikeouts) or pd.isna(line) or pd.isna(bet_side): return ""
    actual, line, bet_side = float(actual_strikeouts), float(line), str(bet_side).strip().lower()
    if not float(line).is_integer():
        if bet_side == "over":  return "win" if actual > line else "loss"
        if bet_side == "under": return "win" if actual < line else "loss"
        return ""
    if bet_side == "over":
        return "win" if actual > line else "push" if actual == line else "loss"
    if bet_side == "under":
        return "win" if actual < line else "push" if actual == line else "loss"
    return ""

# =============================================================================
# STEP 1: LOAD BET LOG
# =============================================================================

if not os.path.exists(BET_LOG_PATH):
    print(f"bet_log.csv not found: {BET_LOG_PATH}")
    print("No existing bet log yet. Skipping settlement.")
    raise SystemExit

print(f"Loading bet log from: {BET_LOG_PATH}")
bet_log = pd.read_csv(BET_LOG_PATH)
bet_log = normalize_bet_log_types(bet_log)
print(f"Total bets in log: {len(bet_log):,}")

unsettled = bet_log[bet_log["settled"] != True].copy()
if unsettled.empty:
    print("No unsettled bets found. Nothing to do.")
    raise SystemExit
print(f"Unsettled bets: {len(unsettled):,}")

# =============================================================================
# STEP 2: PULL NEEDED STATCAST DATES
# =============================================================================

needed_dates  = sorted(unsettled["date"].dropna().dt.strftime("%Y-%m-%d").unique())
daily_results = []
for d in needed_dates:
    daily_table = build_daily_pitcher_strikeout_table(d)
    if not daily_table.empty:
        daily_results.append(daily_table)

if daily_results:
    actuals = pd.concat(daily_results, ignore_index=True)
else:
    actuals = pd.DataFrame(columns=["game_date", "pitcher_id", "actual_strikeouts"])

actuals["game_date"]  = pd.to_datetime(actuals["game_date"], errors="coerce").dt.normalize()
actuals["pitcher_id"] = pd.to_numeric(actuals["pitcher_id"], errors="coerce")
print(f"\nActual pitcher-date rows fetched: {len(actuals):,}")

# =============================================================================
# STEP 3: MERGE ACTUALS INTO UNSETTLED BETS
# =============================================================================

unsettled = unsettled.merge(actuals, left_on=["date", "pitcher_id"],
                            right_on=["game_date", "pitcher_id"], how="left")
unsettled["actual_strikeouts"] = unsettled["actual_strikeouts_y"].combine_first(
    unsettled["actual_strikeouts_x"])
drop_cols = [c for c in ["game_date", "actual_strikeouts_x", "actual_strikeouts_y"]
             if c in unsettled.columns]
unsettled = unsettled.drop(columns=drop_cols)

# =============================================================================
# STEP 4: GRADE BETS
# =============================================================================

unsettled["bet_result"]   = unsettled.apply(
    lambda r: grade_bet(r["actual_strikeouts"], r["line"], r["bet_side"]), axis=1)
unsettled["profit_units"] = unsettled.apply(
    lambda r: calc_profit_units(r["odds"], r["bet_result"]), axis=1)
unsettled["settled"]      = unsettled["bet_result"].isin(["win", "loss", "push"])

# =============================================================================
# STEP 5: WRITE BACK TO MAIN BET LOG
# =============================================================================

settle_key = ["date", "pitcher_id", "line", "bet_side"]
bet_log = bet_log.merge(
    unsettled[settle_key + ["actual_strikeouts", "bet_result", "profit_units", "settled"]],
    on=settle_key, how="left", suffixes=("", "_new"))

for col in ["actual_strikeouts", "bet_result", "profit_units", "settled"]:
    new_col = f"{col}_new"
    if new_col in bet_log.columns:
        if col == "bet_result":
            bet_log[col] = bet_log[new_col].where(bet_log[new_col].fillna("").ne(""), bet_log[col])
        else:
            bet_log[col] = bet_log[new_col].combine_first(bet_log[col])
        bet_log = bet_log.drop(columns=[new_col])

bet_log = normalize_bet_log_types(bet_log)
bet_log.to_csv(BET_LOG_PATH, index=False)

# =============================================================================
# STEP 6: PRINT SUMMARY
# =============================================================================

just_settled = bet_log[bet_log["settled"] == True].copy()
print(f"\nUpdated bet log saved to: {BET_LOG_PATH}")

if just_settled.empty:
    print("No bets were settled.")
    raise SystemExit

summary = just_settled["bet_result"].value_counts(dropna=False)
wins    = int(summary.get("win",  0))
losses  = int(summary.get("loss", 0))
pushes  = int(summary.get("push", 0))
profit  = just_settled["profit_units"].dropna().sum()

print("\n=== SETTLEMENT SUMMARY ===")
print(f"Wins:   {wins}")
print(f"Losses: {losses}")
print(f"Pushes: {pushes}")
print(f"Profit: {profit:.3f} units")

print("\n=== RECENTLY SETTLED BETS ===")
display_cols = ["date", "pitcher_name", "line", "bet_side", "odds",
                "actual_strikeouts", "bet_result", "profit_units"]
existing_display_cols = [c for c in display_cols if c in bet_log.columns]
print(
    just_settled[existing_display_cols]
    .sort_values(["date", "pitcher_name", "line"])
    .tail(30)
    .to_string(index=False, float_format=lambda x: f"{x:.3f}")
)

# =============================================================================
# EXCEL EXPORT
# =============================================================================

try:
    export_bet_log(bet_log)
except Exception as e:
    print(f"Warning: bet_log.xlsx export failed: {e}")

print("\nsettle_bets.py complete.")
