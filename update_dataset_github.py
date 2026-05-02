# update_dataset_github.py
# Daily dataset updater — appends new pitcher game rows to pitcher_game_features.parquet
#
# What this script does:
# 1. Loads your existing parquet dataset
# 2. Finds the most recent date already in the dataset
# 3. Pulls Statcast from (last_date + 1 day) through yesterday
# 4. Cleans, filters, and aggregates to one row per starting pitcher per game
# 5. Builds the same no-leakage features as build_dataset.py
# 6. Deduplicates against existing rows on (game_pk, pitcher_id)
# 7. Appends new rows and saves back to the same parquet file
#
# Safe to run every day — will no-op if dataset is already up to date.
# Does NOT retrain the model. Does NOT modify any other files.
#
# Run AFTER games have completed. Next morning is ideal.

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
    LEAGUE_K_PCT,
    PITCHER_K_RATE_STABILIZER_BF,
    OPPONENT_K_STABILIZER_BF,
    DAYS_REST_CAP,
    FEATURE_COLS,
    TARGET_COL,
)

# =============================================================================
# HELPERS
# =============================================================================

def safe_divide(numerator, denominator, default=np.nan):
    """
    Safely divide two pandas Series/arrays while avoiding pandas nullable NA errors.

    This prevents crashes like:
        TypeError: boolean value of NA is ambiguous

    It returns default when the denominator is missing, zero, or invalid.
    """
    num = pd.to_numeric(numerator, errors="coerce")
    den = pd.to_numeric(denominator, errors="coerce")

    result = pd.Series(default, index=num.index, dtype="float64")
    valid = den.notna() & num.notna() & (den > 0)

    result.loc[valid] = num.loc[valid] / den.loc[valid]
    return result


def assign_pitching_team_and_side(df):
    """Derive pitching team, opponent batting team, and home_away from inning half."""
    df = df.copy()

    df["team"] = np.where(df["inning_topbot"] == "Top", df["home_team"], df["away_team"])
    df["opponent"] = np.where(df["inning_topbot"] == "Top", df["away_team"], df["home_team"])
    df["home_away"] = np.where(df["inning_topbot"] == "Top", 1, 0)

    return df


def map_event_to_outs(event_value):
    """Map plate appearance outcome to approximate outs recorded."""
    if pd.isna(event_value):
        return 0

    event_value = str(event_value).strip().lower()

    outs_map = {
        "strikeout": 1,
        "strikeout_double_play": 2,
        "field_out": 1,
        "force_out": 1,
        "double_play": 2,
        "triple_play": 3,
        "grounded_into_double_play": 2,
        "fielders_choice_out": 1,
        "sac_fly": 1,
        "sac_bunt": 1,
        "sac_fly_double_play": 2,
        "sac_bunt_double_play": 2,
        "double_play_ball": 2,
        "other_out": 1,
    }

    return outs_map.get(event_value, 0)


def build_pitcher_name_lookup(pitcher_ids):
    """Return a DataFrame mapping pitcher_id -> pitcher_name using pybaseball lookup."""
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


def raw_statcast_to_game_rows(raw_df):
    """
    Convert raw Statcast pitch-level data into one row per starting pitcher per game.
    Mirrors build_dataset.py.
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

    pitch_df = assign_pitching_team_and_side(pitch_df)

    # -------------------------------------------------------------------------
    # One row per completed plate appearance
    # -------------------------------------------------------------------------

    pa_sort_cols = [
        "game_pk", "pitcher", "batter", "inning", "inning_topbot",
        "at_bat_number", "pitch_number",
    ]

    pitch_df = pitch_df.sort_values(pa_sort_cols).reset_index(drop=True)

    pa_key_cols = [
        "game_pk", "pitcher", "batter", "inning", "inning_topbot", "at_bat_number",
    ]

    pa_df = pitch_df.groupby(pa_key_cols, as_index=False, sort=False).tail(1).copy()

    pa_df["is_strikeout"] = pa_df["events"].astype(str).str.lower().isin(
        ["strikeout", "strikeout_double_play"]
    ).astype(int)

    pa_df["outs_on_play"] = pa_df["events"].apply(map_event_to_outs)

    pa_df = pa_df.sort_values(
        ["game_date", "game_pk", "team", "inning", "at_bat_number"]
    ).reset_index(drop=True)

    pa_df["appearance_order"] = np.arange(len(pa_df))

    # -------------------------------------------------------------------------
    # Identify starters
    # -------------------------------------------------------------------------

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
        on=["game_pk", "team"],
        how="left",
    )

    pa_df["is_starter"] = (pa_df["pitcher"] == pa_df["starter_pitcher"]).astype(int)
    starter_pa_df = pa_df[pa_df["is_starter"] == 1].copy()

    if starter_pa_df.empty:
        return pd.DataFrame()

    # Pitch count must come from pitch-level rows, not PA rows.
    pitch_with_starter_df = pitch_df.merge(
        starter_lookup[["game_pk", "team", "starter_pitcher"]],
        on=["game_pk", "team"],
        how="left",
    )

    pitch_with_starter_df["is_starter"] = (
        pitch_with_starter_df["pitcher"] == pitch_with_starter_df["starter_pitcher"]
    ).astype(int)

    starter_pitch_df = pitch_with_starter_df[
        pitch_with_starter_df["is_starter"] == 1
    ].copy()

    # -------------------------------------------------------------------------
    # Aggregate to one row per starting pitcher game
    # -------------------------------------------------------------------------

    game_df = (
        starter_pa_df.groupby(
            ["game_date", "game_pk", "pitcher", "team", "opponent", "home_away"],
            as_index=False,
        )
        .agg(
            strikeouts=("is_strikeout", "sum"),
            batters_faced=("batter", "size"),
            outs_recorded=("outs_on_play", "sum"),
        )
    )

    pitch_count_df = (
        starter_pitch_df.groupby(["game_pk", "team", "pitcher"], as_index=False)
        .agg(pitch_count=("pitch_number", "size"))
    )

    game_df = game_df.merge(
        pitch_count_df,
        on=["game_pk", "team", "pitcher"],
        how="left",
    )

    game_df["pitch_count"] = pd.to_numeric(game_df["pitch_count"], errors="coerce")
    game_df["innings_pitched"] = pd.to_numeric(game_df["outs_recorded"], errors="coerce") / 3.0
    game_df["game_K_rate"] = safe_divide(game_df["strikeouts"], game_df["batters_faced"])

    game_df = game_df.rename(columns={"game_date": "date", "pitcher": "pitcher_id"})
    game_df["date"] = pd.to_datetime(game_df["date"]).dt.normalize()
    game_df["season"] = game_df["date"].dt.year

    game_df = game_df[
        game_df["innings_pitched"] >= MIN_IP_STARTER_THRESHOLD
    ].copy()

    if game_df.empty:
        return pd.DataFrame()

    name_lookup = build_pitcher_name_lookup(game_df["pitcher_id"].unique())
    game_df = game_df.merge(name_lookup, on="pitcher_id", how="left")
    game_df["pitcher_name"] = game_df["pitcher_name"].fillna(
        game_df["pitcher_id"].astype(str)
    )

    game_df = game_df[[
        "date", "season", "game_pk", "pitcher_id", "pitcher_name",
        "team", "opponent", "home_away",
        "strikeouts", "batters_faced", "outs_recorded", "innings_pitched",
        "pitch_count", "game_K_rate",
    ]].copy()

    return game_df


def rebuild_features(combined_df):
    """
    Rebuild model features on combined historical + new rows.
    Uses no-leakage logic by shifting prior starts before calculating features.
    """
    df = combined_df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()

    numeric_cols = [
        "strikeouts", "batters_faced", "outs_recorded",
        "innings_pitched", "pitch_count", "game_K_rate",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values(["pitcher_id", "date", "game_pk"]).reset_index(drop=True)

    # -------------------------------------------------------------------------
    # Rolling pitcher features
    # -------------------------------------------------------------------------

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

    df["rolling_pitch_count_last_5"] = (
        df.groupby("pitcher_id", sort=False)["pitch_count"]
        .transform(lambda s: s.shift(1).rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).mean())
    )

    df["_k_shifted_all"] = df.groupby("pitcher_id", sort=False)["strikeouts"].shift(1)
    df["_bf_shifted_all"] = df.groupby("pitcher_id", sort=False)["batters_faced"].shift(1)

    df["_rolling_k_sum_last_5"] = (
        df.groupby("pitcher_id", sort=False)["_k_shifted_all"]
        .transform(lambda s: s.rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).sum())
    )

    df["_rolling_bf_sum_last_5"] = (
        df.groupby("pitcher_id", sort=False)["_bf_shifted_all"]
        .transform(lambda s: s.rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW).sum())
    )

    df["rolling_K_rate_last_5"] = safe_divide(
        df["_rolling_k_sum_last_5"],
        df["_rolling_bf_sum_last_5"],
    )

    # -------------------------------------------------------------------------
    # Days rest
    # -------------------------------------------------------------------------

    df["previous_start_date"] = df.groupby("pitcher_id", sort=False)["date"].shift(1)
    df["days_rest"] = (df["date"] - df["previous_start_date"]).dt.days
    df["days_rest"] = pd.to_numeric(df["days_rest"], errors="coerce")
    df["days_rest"] = df["days_rest"].clip(lower=0, upper=DAYS_REST_CAP)

    # -------------------------------------------------------------------------
    # Season-to-date pitcher K rate
    # -------------------------------------------------------------------------

    ps_groups = ["pitcher_id", "season"]

    df["_ks_shifted_season"] = df.groupby(ps_groups, sort=False)["strikeouts"].shift(1)
    df["_bf_shifted_season"] = df.groupby(ps_groups, sort=False)["batters_faced"].shift(1)
    df["_ip_shifted_season"] = df.groupby(ps_groups, sort=False)["innings_pitched"].shift(1)

    df["_cum_ks_season"] = df.groupby(ps_groups, sort=False)["_ks_shifted_season"].cumsum()
    df["_cum_bf_season"] = df.groupby(ps_groups, sort=False)["_bf_shifted_season"].cumsum()
    df["_cum_ip_season"] = df.groupby(ps_groups, sort=False)["_ip_shifted_season"].cumsum()

    df["season_K_rate"] = safe_divide(df["_cum_ks_season"], df["_cum_bf_season"])
    df["season_K_per_9"] = safe_divide(df["_cum_ks_season"], df["_cum_ip_season"]) * 9

    # -------------------------------------------------------------------------
    # Prior-season pitcher K rate
    # -------------------------------------------------------------------------

    pitcher_season_rates = (
        df.groupby(["pitcher_id", "season"], as_index=False)
        .agg(
            full_season_k=("strikeouts", "sum"),
            full_season_bf=("batters_faced", "sum"),
        )
    )

    pitcher_season_rates["full_season_K_rate"] = safe_divide(
        pitcher_season_rates["full_season_k"],
        pitcher_season_rates["full_season_bf"],
    )

    prior_pitcher_rates = pitcher_season_rates[[
        "pitcher_id", "season", "full_season_K_rate",
    ]].copy()

    prior_pitcher_rates["season"] = prior_pitcher_rates["season"] + 1
    prior_pitcher_rates = prior_pitcher_rates.rename(
        columns={"full_season_K_rate": "prior_season_K_rate"}
    )

    if "prior_season_K_rate" in df.columns:
        df = df.drop(columns=["prior_season_K_rate"])

    df = df.merge(
        prior_pitcher_rates,
        on=["pitcher_id", "season"],
        how="left",
    )

    # -------------------------------------------------------------------------
    # Blended pitcher K rate
    # -------------------------------------------------------------------------

    df["pitcher_current_weight"] = safe_divide(
        df["_cum_bf_season"],
        df["_cum_bf_season"] + PITCHER_K_RATE_STABILIZER_BF,
        default=0.0,
    )

    pitcher_prior_component = df["prior_season_K_rate"].fillna(LEAGUE_K_PCT)
    pitcher_current_component = df["season_K_rate"].fillna(pitcher_prior_component)

    df["blended_K_rate"] = (
        df["pitcher_current_weight"] * pitcher_current_component
        + (1.0 - df["pitcher_current_weight"]) * pitcher_prior_component
    )

    # -------------------------------------------------------------------------
    # Opponent K% weighted blend
    # -------------------------------------------------------------------------

    opp_daily = (
        df.groupby(["opponent", "season", "date"], as_index=False)
        .agg(day_k=("strikeouts", "sum"), day_bf=("batters_faced", "sum"))
        .sort_values(["opponent", "season", "date"])
        .reset_index(drop=True)
    )

    opp_daily["current_prior_opp_k"] = (
        opp_daily.groupby(["opponent", "season"], sort=False)["day_k"].cumsum()
        - opp_daily["day_k"]
    )

    opp_daily["current_prior_opp_bf"] = (
        opp_daily.groupby(["opponent", "season"], sort=False)["day_bf"].cumsum()
        - opp_daily["day_bf"]
    )

    opp_daily["opponent_k_pct"] = safe_divide(
        opp_daily["current_prior_opp_k"],
        opp_daily["current_prior_opp_bf"],
    )

    opp_season_rates = (
        df.groupby(["opponent", "season"], as_index=False)
        .agg(
            opp_season_k=("strikeouts", "sum"),
            opp_season_bf=("batters_faced", "sum"),
        )
    )

    opp_season_rates["prior_opponent_k_pct"] = safe_divide(
        opp_season_rates["opp_season_k"],
        opp_season_rates["opp_season_bf"],
    )

    prior_opp_rates = opp_season_rates[[
        "opponent", "season", "prior_opponent_k_pct",
    ]].copy()

    prior_opp_rates["season"] = prior_opp_rates["season"] + 1

    drop_before_merge = [
        "current_prior_opp_bf",
        "opponent_k_pct",
        "prior_opponent_k_pct",
    ]

    existing_drop = [col for col in drop_before_merge if col in df.columns]
    if existing_drop:
        df = df.drop(columns=existing_drop)

    df = df.merge(
        opp_daily[[
            "opponent", "season", "date",
            "current_prior_opp_bf", "opponent_k_pct",
        ]],
        on=["opponent", "season", "date"],
        how="left",
    )

    df = df.merge(
        prior_opp_rates,
        on=["opponent", "season"],
        how="left",
    )

    df["opponent_current_weight"] = safe_divide(
        df["current_prior_opp_bf"],
        df["current_prior_opp_bf"] + OPPONENT_K_STABILIZER_BF,
        default=0.0,
    )

    opponent_prior_component = df["prior_opponent_k_pct"].fillna(LEAGUE_K_PCT)
    opponent_current_component = df["opponent_k_pct"].fillna(opponent_prior_component)

    df["smoothed_opponent_k_pct"] = (
        df["opponent_current_weight"] * opponent_current_component
        + (1.0 - df["opponent_current_weight"]) * opponent_prior_component
    )

    temp_cols = [
        "_k_shifted_all", "_bf_shifted_all",
        "_rolling_k_sum_last_5", "_rolling_bf_sum_last_5",
        "previous_start_date",
        "_ks_shifted_season", "_bf_shifted_season", "_ip_shifted_season",
        "_cum_ks_season", "_cum_bf_season", "_cum_ip_season",
    ]

    temp_cols = [col for col in temp_cols if col in df.columns]
    df = df.drop(columns=temp_cols)

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

# Pull through yesterday because today's games are not complete yet.
yesterday = pd.Timestamp.today().normalize() - pd.Timedelta(days=1)

if pull_start > yesterday:
    print(f"\nDataset is already up to date through {last_date.date()}. Nothing to do.")
    raise SystemExit

pull_start_str = pull_start.strftime("%Y-%m-%d")
pull_end_str = yesterday.strftime("%Y-%m-%d")

print(f"\nPulling Statcast from {pull_start_str} to {pull_end_str}...")

# =============================================================================
# STEP 3: FETCH NEW STATCAST DATA
# =============================================================================

raw_df = statcast(start_dt=pull_start_str, end_dt=pull_end_str)

print("RAW ROWS:", 0 if raw_df is None else len(raw_df))

if raw_df is None or raw_df.empty:
    print("No Statcast rows returned for this date range. Nothing to append.")
    raise SystemExit

print(f"Fetched {len(raw_df):,} raw pitch rows")

# =============================================================================
# STEP 4: PROCESS INTO GAME ROWS
# =============================================================================

new_game_rows = raw_statcast_to_game_rows(raw_df)

if new_game_rows.empty:
    print("No qualifying starter rows found after filtering. Nothing to append.")
    raise SystemExit

new_game_rows["date"] = pd.to_datetime(new_game_rows["date"]).dt.normalize()

print(f"New game rows before dedup: {len(new_game_rows):,}")

# =============================================================================
# STEP 5: DEDUPLICATE AGAINST EXISTING DATASET
# =============================================================================

existing_key_strings = {
    f"{gp}_{pid}"
    for gp, pid in zip(
        existing_df["game_pk"].astype(str),
        existing_df["pitcher_id"].astype(str),
    )
}

new_game_rows["_key"] = (
    new_game_rows["game_pk"].astype(str)
    + "_"
    + new_game_rows["pitcher_id"].astype(str)
)

new_rows_deduped = new_game_rows[
    ~new_game_rows["_key"].isin(existing_key_strings)
].drop(columns=["_key"]).copy()

print(f"New rows after dedup: {len(new_rows_deduped):,}")

if new_rows_deduped.empty:
    print("All fetched rows already exist in dataset. Nothing to append.")
    raise SystemExit

# =============================================================================
# STEP 6: COMBINE RAW ROWS AND REBUILD FEATURES
# =============================================================================

raw_cols = [
    "date", "season", "game_pk", "pitcher_id", "pitcher_name",
    "team", "opponent", "home_away",
    "strikeouts", "batters_faced", "outs_recorded", "innings_pitched",
    "pitch_count", "game_K_rate",
]

missing_existing_raw_cols = [col for col in raw_cols if col not in existing_df.columns]

if missing_existing_raw_cols:
    raise ValueError(
        "Existing dataset is missing columns needed by the updated feature builder.\n"
        f"Missing: {missing_existing_raw_cols}\n\n"
        "This usually means pitcher_game_features.parquet was created by the old build_dataset.py.\n"
        "Rebuild the dataset locally with the updated build_dataset.py, then commit/push the new parquet file."
    )

missing_new_raw_cols = [col for col in raw_cols if col not in new_rows_deduped.columns]

if missing_new_raw_cols:
    raise ValueError(f"New game rows are missing expected columns: {missing_new_raw_cols}")

existing_raw = existing_df[raw_cols].copy()
new_raw = new_rows_deduped[raw_cols].copy()

combined_raw = pd.concat([existing_raw, new_raw], ignore_index=True)

combined_raw = combined_raw.drop_duplicates(
    subset=["game_pk", "pitcher_id"],
    keep="last",
)

combined_raw = combined_raw.sort_values(
    ["pitcher_id", "date", "game_pk"]
).reset_index(drop=True)

print(f"\nRebuilding features across {len(combined_raw):,} total rows...")

combined_with_features = rebuild_features(combined_raw)

# =============================================================================
# STEP 7: FINALIZE AND SAVE
# =============================================================================

keep_cols = [
    "date", "season", "game_pk", "pitcher_id", "pitcher_name",
    "team", "opponent", "home_away",

    # Target and base game stats
    TARGET_COL,
    "batters_faced", "innings_pitched", "outs_recorded", "pitch_count", "game_K_rate",

    # Old diagnostic features
    "rolling_K_last_5", "season_K_per_9", "opponent_k_pct",

    # New model features
    "rolling_K_rate_last_5",
    "blended_K_rate",
    "rolling_IP_last_5",
    "rolling_batters_faced_last_5",
    "rolling_pitch_count_last_5",
    "days_rest",
    "smoothed_opponent_k_pct",

    # Helpful diagnostic columns
    "season_K_rate",
    "prior_season_K_rate",
    "pitcher_current_weight",
    "prior_opponent_k_pct",
    "opponent_current_weight",
]

missing_keep_cols = [col for col in keep_cols if col not in combined_with_features.columns]

if missing_keep_cols:
    raise ValueError(f"Missing expected final columns: {missing_keep_cols}")

missing_feature_cols = [col for col in FEATURE_COLS if col not in combined_with_features.columns]

if missing_feature_cols:
    raise ValueError(f"Missing configured FEATURE_COLS after rebuild: {missing_feature_cols}")

# Create keys so we append only the rows that were newly pulled today.
combined_with_features["_key"] = (
    combined_with_features["game_pk"].astype(str)
    + "_"
    + combined_with_features["pitcher_id"].astype(str)
)

new_rows_deduped["_key"] = (
    new_rows_deduped["game_pk"].astype(str)
    + "_"
    + new_rows_deduped["pitcher_id"].astype(str)
)

new_key_set = set(new_rows_deduped["_key"])

new_feature_rows = combined_with_features[
    combined_with_features["_key"].isin(new_key_set)
].copy()

# Do not drop new rows with missing rolling features.
# Keeping them gives future starts the history needed to eventually build rolling features.
# Existing rows are preserved exactly so the dataset does not shrink each daily update.
existing_final = existing_df[keep_cols].copy()
new_feature_rows = new_feature_rows[keep_cols].copy()

df_final = pd.concat([existing_final, new_feature_rows], ignore_index=True)

df_final = (
    df_final
    .drop_duplicates(subset=["game_pk", "pitcher_id"], keep="last")
    .sort_values(["date", "game_pk", "pitcher_id"])
    .reset_index(drop=True)
)

print("\n=== Update Summary ===")
print(f"Rows before update: {len(existing_df):,}")
print(f"New rows added:     {len(new_feature_rows):,}")
print(f"Rows after update:  {len(df_final):,}")
print(f"New date range:     {df_final['date'].min().date()} -> {df_final['date'].max().date()}")

print("\nFeature NA counts for newly added rows:")
print(new_feature_rows[FEATURE_COLS].isna().sum().sort_values(ascending=False).to_string())

print("\nNew rows added:")
display_cols = [
    "date", "pitcher_name", "team", "opponent",
    "strikeouts", "innings_pitched", "pitch_count",
]

print(
    new_feature_rows[display_cols]
    .sort_values(["date", "pitcher_name"])
    .to_string(index=False, float_format=lambda x: f"{x:.1f}")
)

df_final.to_parquet(DATASET_PATH, index=False)

print(f"\nDataset saved to: {DATASET_PATH}")
print("\nupdate_dataset_github.py complete.")