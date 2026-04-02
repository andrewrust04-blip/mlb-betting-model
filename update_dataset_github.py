# update_dataset.py
# Daily dataset updater — appends new pitcher game rows to pitcher_game_features.parquet
#
# What this script does:
# 1. Loads your existing parquet dataset
# 2. Finds the most recent date already in the dataset
# 3. Pulls Statcast from (last_date + 1 day) through yesterday
# 4. Cleans, filters, and aggregates to one row per pitcher per game
# 5. Builds the same features as build_dataset.py (rolling K, IP, BF, season K/9, opponent K%)
# 6. Deduplicates against existing rows on (game_pk, pitcher_id)
# 7. Appends new rows and saves back to the same parquet file
#
# Safe to run every day — will no-op if dataset is already up to date.
# Does NOT retrain the model. Does NOT modify any other files.
#
# Run AFTER games have completed (next morning is ideal).

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

try:
    from pybaseball import statcast, playerid_reverse_lookup, cache
    cache.enable()
except ImportError:
    raise ImportError("Run: pip install pybaseball pandas numpy")

from config_github import (
    DATASET_PATH,
    MIN_IP_STARTER_THRESHOLD,
    ROLLING_WINDOW,
    FEATURE_COLS,
    TARGET_COL,
)

# =============================================================================
# HELPERS — same logic as build_dataset.py
# =============================================================================

def assign_pitching_team_and_side(df):
    df = df.copy()
    df["team"] = np.where(df["inning_topbot"] == "Top", df["home_team"], df["away_team"])
    df["opponent"] = np.where(df["inning_topbot"] == "Top", df["away_team"], df["home_team"])
    df["home_away"] = np.where(df["inning_topbot"] == "Top", 1, 0)
    return df


def map_event_to_outs(event_value):
    if pd.isna(event_value):
        return 0
    event_value = str(event_value).strip().lower()
    outs_map = {
        "strikeout": 1, "strikeout_double_play": 2,
        "field_out": 1, "force_out": 1,
        "double_play": 2, "triple_play": 3,
        "grounded_into_double_play": 2, "fielders_choice_out": 1,
        "sac_fly": 1, "sac_bunt": 1,
        "sac_fly_double_play": 2, "sac_bunt_double_play": 2,
        "double_play_ball": 2, "other_out": 1,
    }
    return outs_map.get(event_value, 0)


def build_pitcher_name_lookup(pitcher_ids):
    unique_ids = sorted({int(pid) for pid in pitcher_ids if pd.notna(pid)})
    if not unique_ids:
        return pd.DataFrame(columns=["pitcher_id", "pitcher_name"])
    try:
        lookup = playerid_reverse_lookup(unique_ids, key_type="mlbam").copy()
        expected = {"key_mlbam", "name_first", "name_last"}
        if expected.issubset(set(lookup.columns)):
            lookup["pitcher_id"] = pd.to_numeric(lookup["key_mlbam"], errors="coerce")
            lookup["pitcher_name"] = (
                lookup["name_first"].fillna("").str.strip()
                + " "
                + lookup["name_last"].fillna("").str.strip()
            ).str.strip()
            lookup = lookup[["pitcher_id", "pitcher_name"]].drop_duplicates()
            return lookup[lookup["pitcher_name"] != ""].copy()
    except Exception:
        pass
    fallback = pd.DataFrame({"pitcher_id": unique_ids})
    fallback["pitcher_name"] = fallback["pitcher_id"].astype(str)
    return fallback


def raw_statcast_to_game_rows(raw_df, season):
    """
    Convert raw Statcast pitch-level data into one row per pitcher per game.
    Mirrors the logic in build_dataset.py Steps 2-5.
    """
    required_cols = [
        "game_date", "game_pk", "pitcher", "batter", "at_bat_number",
        "pitch_number", "inning", "inning_topbot", "events",
        "home_team", "away_team", "game_type",
    ]
    missing = [c for c in required_cols if c not in raw_df.columns]
    if missing:
        raise ValueError(f"Missing Statcast columns: {missing}")

    pitch_df = raw_df[raw_df["game_type"] == "R"][required_cols].copy()
    pitch_df["game_date"] = pd.to_datetime(pitch_df["game_date"], errors="coerce")

    pitch_df = pitch_df.dropna(subset=[
        "game_date", "game_pk", "pitcher", "batter",
        "at_bat_number", "pitch_number", "inning", "inning_topbot",
    ]).copy()

    for col in ["pitcher", "batter", "at_bat_number", "pitch_number", "inning"]:
        pitch_df[col] = pd.to_numeric(pitch_df[col], errors="coerce")

    pitch_df = pitch_df.dropna(
        subset=["pitcher", "batter", "at_bat_number", "pitch_number", "inning"]
    ).copy()

    if pitch_df.empty:
        return pd.DataFrame()

    # One row per completed plate appearance
    pa_sort_cols = [
        "game_pk", "pitcher", "batter", "inning",
        "inning_topbot", "at_bat_number", "pitch_number"
    ]
    pitch_df = pitch_df.sort_values(pa_sort_cols).reset_index(drop=True)

    pa_key_cols = [
        "game_pk", "pitcher", "batter", "inning",
        "inning_topbot", "at_bat_number"
    ]
    pa_df = pitch_df.groupby(pa_key_cols, as_index=False, sort=False).tail(1).copy()

    pa_df = assign_pitching_team_and_side(pa_df)
    pa_df["is_strikeout"] = pa_df["events"].astype(str).str.lower().isin(
        ["strikeout", "strikeout_double_play"]
    ).astype(int)
    pa_df["outs_on_play"] = pa_df["events"].apply(map_event_to_outs)

    pa_df = pa_df.sort_values(
        ["game_date", "game_pk", "team", "inning", "at_bat_number"]
    ).reset_index(drop=True)
    pa_df["appearance_order"] = np.arange(len(pa_df))

    # Identify starters
    pitcher_first = (
        pa_df.groupby(["game_pk", "team", "pitcher"], as_index=False)
             .agg(first_appearance_order=("appearance_order", "min"))
    )
    starter_lookup = (
        pitcher_first
        .sort_values(["game_pk", "team", "first_appearance_order"])
        .groupby(["game_pk", "team"], as_index=False)
        .first()
        .rename(columns={"pitcher": "starter_pitcher"})
    )

    pa_df = pa_df.merge(
        starter_lookup[["game_pk", "team", "starter_pitcher"]],
        on=["game_pk", "team"], how="left"
    )
    pa_df["is_starter"] = (pa_df["pitcher"] == pa_df["starter_pitcher"]).astype(int)
    starter_pa_df = pa_df[pa_df["is_starter"] == 1].copy()

    if starter_pa_df.empty:
        return pd.DataFrame()

    # Aggregate to one row per pitcher per game
    game_df = (
        starter_pa_df.groupby(
            ["game_date", "game_pk", "pitcher", "team", "opponent", "home_away"],
            as_index=False
        )
        .agg(
            strikeouts=("is_strikeout", "sum"),
            batters_faced=("batter", "size"),
            outs_recorded=("outs_on_play", "sum"),
        )
    )

    game_df["innings_pitched"] = game_df["outs_recorded"] / 3.0
    game_df = game_df.rename(columns={"game_date": "date", "pitcher": "pitcher_id"})
    game_df["season"] = season

    # Filter out opener-like outings
    game_df = game_df[game_df["innings_pitched"] >= MIN_IP_STARTER_THRESHOLD].copy()

    if game_df.empty:
        return pd.DataFrame()

    # Add pitcher names
    name_lookup = build_pitcher_name_lookup(game_df["pitcher_id"].unique())
    game_df = game_df.merge(name_lookup, on="pitcher_id", how="left")
    game_df["pitcher_name"] = game_df["pitcher_name"].fillna(game_df["pitcher_id"].astype(str))

    game_df = game_df[[
        "date", "season", "game_pk", "pitcher_id", "pitcher_name",
        "team", "opponent", "home_away",
        "strikeouts", "batters_faced", "outs_recorded", "innings_pitched",
    ]].copy()

    return game_df


def rebuild_rolling_features(combined_df):
    """
    Rebuild rolling and season features for all rows, using no-leakage logic.
    Called after appending new rows so that rolling windows update correctly
    for pitchers who now have new starts in the dataset.

    This is fast — it only recomputes features, does not re-pull any data.
    """
    df = combined_df.sort_values(
        ["pitcher_id", "season", "date", "game_pk"]
    ).reset_index(drop=True)

    # Rolling last-5 features
    df["rolling_K_last_5"] = (
        df.groupby("pitcher_id", sort=False)["strikeouts"]
          .transform(lambda s: s.shift(1).rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).mean())
    )
    df["rolling_IP_last_5"] = (
        df.groupby("pitcher_id", sort=False)["innings_pitched"]
          .transform(lambda s: s.shift(1).rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).mean())
    )
    df["rolling_batters_faced_last_5"] = (
        df.groupby("pitcher_id", sort=False)["batters_faced"]
          .transform(lambda s: s.shift(1).rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).mean())
    )

    # -------------------------------------------------------------------------
    # PRIOR START COUNT THIS SEASON
    # -------------------------------------------------------------------------
    ps_groups = ["pitcher_id", "season"]
    df["prior_starts_this_season"] = df.groupby(ps_groups, sort=False).cumcount()

    # -------------------------------------------------------------------------
    # CURRENT SEASON-TO-DATE K/9 (uses only prior starts)
    # -------------------------------------------------------------------------
    df["_ks_shifted"] = df.groupby(ps_groups, sort=False)["strikeouts"].shift(1)
    df["_ip_shifted"] = df.groupby(ps_groups, sort=False)["innings_pitched"].shift(1)
    df["_cum_ks"] = df.groupby(ps_groups, sort=False)["_ks_shifted"].cumsum()
    df["_cum_ip"] = df.groupby(ps_groups, sort=False)["_ip_shifted"].cumsum()

    df["_season_k9_current"] = np.where(
        df["_cum_ip"] > 0,
        (df["_cum_ks"] / df["_cum_ip"]) * 9,
        np.nan
    )

    # -------------------------------------------------------------------------
    # LAST SEASON FULL-SEASON K/9
    # -------------------------------------------------------------------------
    season_totals = (
        df.groupby(["pitcher_id", "season"], as_index=False)
          .agg(
              season_strikeouts=("strikeouts", "sum"),
              season_ip=("innings_pitched", "sum")
          )
          .sort_values(["pitcher_id", "season"])
          .reset_index(drop=True)
    )

    season_totals["full_season_k9"] = np.where(
        season_totals["season_ip"] > 0,
        (season_totals["season_strikeouts"] / season_totals["season_ip"]) * 9,
        np.nan
    )

    season_totals["last_season_k9"] = (
        season_totals.groupby("pitcher_id", sort=False)["full_season_k9"].shift(1)
    )

    df = df.merge(
        season_totals[["pitcher_id", "season", "last_season_k9"]],
        on=["pitcher_id", "season"],
        how="left"
    )

    # -------------------------------------------------------------------------
    # EARLY-SEASON FALLBACK RULE:
    # if pitcher has < 5 prior starts this season, use last season K/9
    # otherwise use current season-to-date K/9
    # if last season K/9 is missing, fall back to current season-to-date K/9
    # -------------------------------------------------------------------------
    df["season_K_per_9"] = np.where(
        df["prior_starts_this_season"] < 5,
        df["last_season_k9"],
        df["_season_k9_current"]
    )

    df["season_K_per_9"] = df["season_K_per_9"].fillna(df["_season_k9_current"])

    df = df.drop(columns=[
        "_ks_shifted", "_ip_shifted", "_cum_ks", "_cum_ip",
        "_season_k9_current", "last_season_k9"
    ])

    # -------------------------------------------------------------------------
    # Opponent K% — no leakage (prior cumulative, pandas-3.0 safe)
    # -------------------------------------------------------------------------
    opp_daily = (
        df.groupby(["opponent", "season", "date"], as_index=False)
          .agg(day_k=("strikeouts", "sum"), day_bf=("batters_faced", "sum"))
          .sort_values(["opponent", "season", "date"])
          .reset_index(drop=True)
    )

    opp_daily["cum_k"] = (
        opp_daily.groupby(["opponent", "season"], sort=False)["day_k"].cumsum()
        - opp_daily["day_k"]
    )
    opp_daily["cum_bf"] = (
        opp_daily.groupby(["opponent", "season"], sort=False)["day_bf"].cumsum()
        - opp_daily["day_bf"]
    )
    opp_daily["opponent_k_pct"] = opp_daily["cum_k"] / opp_daily["cum_bf"]

    # Drop existing opponent_k_pct if present, then re-merge
    if "opponent_k_pct" in df.columns:
        df = df.drop(columns=["opponent_k_pct"])

    df = df.merge(
        opp_daily[["opponent", "season", "date", "opponent_k_pct"]],
        on=["opponent", "season", "date"],
        how="left"
    )

    return df


# =============================================================================
# STEP 1: LOAD EXISTING DATASET
# =============================================================================

print(f"Loading existing dataset from: {DATASET_PATH}")
existing_df = pd.read_parquet(DATASET_PATH)
existing_df["date"] = pd.to_datetime(existing_df["date"]).dt.normalize()

print(f"Existing rows: {len(existing_df):,}")
print(f"Existing date range: {existing_df['date'].min().date()} -> {existing_df['date'].max().date()}")

# =============================================================================
# STEP 2: DETERMINE PULL WINDOW
# =============================================================================

last_date = existing_df["date"].max()
pull_start = last_date + pd.Timedelta(days=1)

# Pull through yesterday — today's games aren't complete yet
yesterday = pd.Timestamp.today().normalize() - pd.Timedelta(days=1)

if pull_start > yesterday:
    print(f"\nDataset is already up to date through {last_date.date()}. Nothing to do.")
    raise SystemExit

pull_start_str = pull_start.strftime("%Y-%m-%d")
pull_end_str = yesterday.strftime("%Y-%m-%d")
season = yesterday.year

print(f"\nPulling Statcast from {pull_start_str} to {pull_end_str} (season {season})...")

# =============================================================================
# STEP 3: FETCH NEW STATCAST DATA
# =============================================================================

raw_df = statcast(start_dt=pull_start_str, end_dt=pull_end_str)

if raw_df is None or raw_df.empty:
    print("No Statcast rows returned for this date range. Nothing to append.")
    raise SystemExit

print(f"Fetched {len(raw_df):,} raw pitch rows")

# =============================================================================
# STEP 4: PROCESS INTO GAME ROWS
# =============================================================================

new_game_rows = raw_statcast_to_game_rows(raw_df, season)

if new_game_rows.empty:
    print("No qualifying starter rows found after filtering. Nothing to append.")
    raise SystemExit

new_game_rows["date"] = pd.to_datetime(new_game_rows["date"]).dt.normalize()

print(f"New game rows before dedup: {len(new_game_rows):,}")

# =============================================================================
# STEP 5: DEDUPLICATE AGAINST EXISTING DATASET
# =============================================================================

# Use (game_pk, pitcher_id) as the unique key — same as build_dataset.py logic
existing_keys = set(
    zip(
        existing_df["game_pk"].astype(str),
        existing_df["pitcher_id"].astype(str)
    )
)

new_game_rows["_key"] = (
    new_game_rows["game_pk"].astype(str) + "_" +
    new_game_rows["pitcher_id"].astype(str)
)

new_rows_deduped = new_game_rows[
    ~new_game_rows["_key"].isin(
        {f"{gp}_{pid}" for gp, pid in existing_keys}
    )
].drop(columns=["_key"]).copy()

print(f"New rows after dedup: {len(new_rows_deduped):,}")

if new_rows_deduped.empty:
    print("All fetched rows already exist in dataset. Nothing to append.")
    raise SystemExit

# =============================================================================
# STEP 6: COMBINE AND REBUILD FEATURES
# =============================================================================

# Drop existing feature columns from existing_df before combining
# so we can rebuild them cleanly for all rows
raw_cols = [
    "date", "season", "game_pk", "pitcher_id", "pitcher_name",
    "team", "opponent", "home_away",
    "strikeouts", "batters_faced", "outs_recorded", "innings_pitched",
]

existing_raw = existing_df[raw_cols].copy()
new_raw = new_rows_deduped[raw_cols].copy()

combined_raw = pd.concat([existing_raw, new_raw], ignore_index=True)
combined_raw = combined_raw.sort_values(
    ["pitcher_id", "season", "date", "game_pk"]
).reset_index(drop=True)

print(f"\nRebuilding rolling features across {len(combined_raw):,} total rows...")
combined_with_features = rebuild_rolling_features(combined_raw)

# =============================================================================
# STEP 7: FINALIZE AND SAVE
# =============================================================================

keep_cols = [
    "date", "season", "game_pk", "pitcher_id", "pitcher_name",
    "team", "opponent", "home_away",
    "batters_faced", "innings_pitched", "outs_recorded",
    TARGET_COL,
    "rolling_K_last_5", "rolling_IP_last_5", "rolling_batters_faced_last_5",
    "season_K_per_9", "opponent_k_pct",
]

df_final = (
    combined_with_features[keep_cols]
    .sort_values(["date", "game_pk", "pitcher_id"])
    .reset_index(drop=True)
)

print(f"\n=== Update Summary ===")
print(f"Rows before update: {len(existing_df):,}")
print(f"New rows added:     {len(new_rows_deduped):,}")
print(f"Rows after update:  {len(df_final):,}")
print(f"New date range:     {df_final['date'].min().date()} -> {df_final['date'].max().date()}")

print(f"\nNew rows added:")
display_cols = ["date", "pitcher_name", "team", "opponent", "strikeouts", "innings_pitched"]
print(
    new_rows_deduped[display_cols]
    .sort_values(["date", "pitcher_name"])
    .to_string(index=False, float_format=lambda x: f"{x:.1f}")
)

df_final.to_parquet(DATASET_PATH, index=False)
print(f"\nDataset saved to: {DATASET_PATH}")
print("\nupdate_dataset.py complete.")