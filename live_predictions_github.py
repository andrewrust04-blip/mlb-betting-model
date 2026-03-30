# live_predictions.py
# Build live MLB pitcher strikeout predictions for a target date.
#
# Outputs:
#   - live_predictions.csv
#   - filtered_bets.csv      (pipeline source of truth)
#   - filtered_bets.xlsx     (formatted, for viewing)
#   - updated bet_log.csv    (pipeline source of truth)
#   - updated bet_log.xlsx   (formatted, for viewing)

import warnings
warnings.filterwarnings("ignore")

import os
import pickle
import requests
import unicodedata

import numpy as np
import pandas as pd
import statsmodels.api as sm

from config_github import (
    DATASET_PATH, FEATURE_COLS, N_SIMS, NB_ALPHA, SIM_CLIP_MAX,
    PROB_THRESHOLDS, HALF_LINE_THRESHOLDS, MODEL_PATH, SCALER_PATH,
    SPORTSBOOK_LINES_PATH, LIVE_PREDICTIONS_PATH, FILTERED_BETS_PATH,
    BET_LOG_PATH, BET_EDGE_THRESHOLD, ALLOW_MULTIPLE_BETS_PER_PITCHER,
)
from export_excel_github import export_filtered_bets, export_bet_log

# =============================================================================
# CONFIG
# =============================================================================

TARGET_DATE      = pd.Timestamp.today().normalize().strftime("%Y-%m-%d")
MLB_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"

TEAM_ABBR_MAP = {
    "Arizona Diamondbacks": "AZ", "Atlanta Braves": "ATL", "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS", "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE", "Colorado Rockies": "COL",
    "Detroit Tigers": "DET", "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD", "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL", "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Athletics": "OAK", "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT", "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL", "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX", "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH",
}


# Stabilized opponent K%
LEAGUE_K_PCT = 0.22
STABILIZER_BF = 200
# =============================================================================
# HELPERS
# =============================================================================

def normalize_name(name):
    if pd.isna(name): return ""
    name = str(name).strip().lower()
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("utf-8")
    return " ".join(name.split())

def american_odds_to_implied(odds):
    odds = float(odds)
    return abs(odds) / (abs(odds) + 100) if odds < 0 else 100 / (odds + 100)

def get_bet_size(edge):
    if pd.isna(edge) or edge < BET_EDGE_THRESHOLD: return 0.0
    if edge < 0.075:  return 0.5
    if edge < 0.10:   return 1.0
    if edge < 0.15:   return 1.5
    return 2.0

def kelly_fraction(prob, odds):
    if pd.isna(prob) or pd.isna(odds): return 0.0
    prob, odds = float(prob), float(odds)
    b = odds / 100.0 if odds > 0 else 100.0 / abs(odds)
    return max(((prob * (b + 1.0)) - 1.0) / b, 0.0)

def get_kelly_units(prob, odds, bankroll_fraction=0.25, max_units=2.0):
    return round(min(max(kelly_fraction(prob, odds) * bankroll_fraction * 10.0, 0.0), max_units), 2)

def simulate_nb_draws(mu_array, alpha, n_sims, clip_max, rng):
    mu = np.asarray(mu_array, dtype=float)
    r  = np.clip(1.0 / alpha, 1e-6, None)
    p  = np.clip(r / (r + mu), 1e-9, 1.0 - 1e-9)
    draws = np.empty((len(mu), n_sims), dtype=np.int32)
    for i in range(len(mu)):
        draws[i] = np.clip(rng.negative_binomial(r, p[i], size=n_sims), 0, clip_max)
    return draws

def get_probable_pitchers_for_date(target_date):
    params   = {"sportId": 1, "date": target_date, "hydrate": "probablePitcher"}
    response = requests.get(MLB_SCHEDULE_URL, params=params, timeout=30)
    response.raise_for_status()
    data     = response.json()
    rows     = []
    for date_block in data.get("dates", []):
        for game in date_block.get("games", []):
            game_pk = game.get("gamePk")
            teams   = game.get("teams", {})
            home    = teams.get("home", {})
            away    = teams.get("away", {})
            ha      = TEAM_ABBR_MAP.get(home.get("team", {}).get("name"))
            aa      = TEAM_ABBR_MAP.get(away.get("team", {}).get("name"))
            hp      = home.get("probablePitcher", {})
            ap      = away.get("probablePitcher", {})
            if hp:
                rows.append({"date": pd.to_datetime(target_date), "game_pk": game_pk,
                             "pitcher_id": hp.get("id"), "pitcher_name": hp.get("fullName"),
                             "team": ha, "opponent": aa, "home_away": 0})
            if ap:
                rows.append({"date": pd.to_datetime(target_date), "game_pk": game_pk,
                             "pitcher_id": ap.get("id"), "pitcher_name": ap.get("fullName"),
                             "team": aa, "opponent": ha, "home_away": 1})
    live_df = pd.DataFrame(rows)
    if live_df.empty:
        print(f"No probable pitchers found for {target_date}.")
        return live_df
    live_df["pitcher_id"]       = pd.to_numeric(live_df["pitcher_id"], errors="coerce")
    live_df["pitcher_name_norm"]= live_df["pitcher_name"].apply(normalize_name)
    return live_df

def build_live_features(live_df, hist_df, target_date):
    target_ts     = pd.to_datetime(target_date)
    target_season = target_ts.year
    prior_season  = target_season - 1
    hist_prior    = hist_df[hist_df["date"] < target_ts].copy()
    hist_prior    = hist_prior.sort_values(["pitcher_id", "date", "game_pk"]).reset_index(drop=True)

    feature_rows, skipped_rows = [], []

    for _, row in live_df.iterrows():
        pitcher_id   = row["pitcher_id"]
        pitcher_name = row["pitcher_name"]

        if pd.isna(pitcher_id):
            skipped_rows.append({"pitcher_name": pitcher_name, "reason": "missing pitcher_id from schedule"})
            continue

        pitcher_hist      = hist_prior[hist_prior["pitcher_id"] == pitcher_id].copy()
        season_hist       = pitcher_hist[pitcher_hist["season"] == target_season].copy()
        prior_season_hist = pitcher_hist[pitcher_hist["season"] == prior_season].copy()

        if len(pitcher_hist) < 5:
            skipped_rows.append({"pitcher_name": pitcher_name, "reason": "fewer than 5 prior starts in dataset"})
            continue

        last_5 = pitcher_hist.tail(5)
        season_ip = season_hist["innings_pitched"].sum()
        season_k  = season_hist["strikeouts"].sum()

        if season_ip > 0:
            season_k_per_9 = (season_k / season_ip) * 9
        else:
            prior_ip = prior_season_hist["innings_pitched"].sum()
            prior_k  = prior_season_hist["strikeouts"].sum()
            if prior_ip <= 0:
                skipped_rows.append({"pitcher_name": pitcher_name,
                                     "reason": f"no usable pitcher K/9 history for {target_season} or {prior_season}"})
                continue
            season_k_per_9 = (prior_k / prior_ip) * 9

        opponent = row["opponent"]

        opp_cur = hist_prior[
            (hist_prior["season"] == target_season) &
            (hist_prior["opponent"] == opponent)
        ]
        opp_bf_c = opp_cur["batters_faced"].sum()
        opp_k_c = opp_cur["strikeouts"].sum()

        if opp_bf_c > 0:
            opponent_k_pct = (opp_k_c + LEAGUE_K_PCT * STABILIZER_BF) / (opp_bf_c + STABILIZER_BF)
        else:
            opp_pri = hist_prior[
                (hist_prior["season"] == prior_season) &
                (hist_prior["opponent"] == opponent)
            ]
            opp_bf_p = opp_pri["batters_faced"].sum()
            opp_k_p = opp_pri["strikeouts"].sum()

            if opp_bf_p <= 0:
                skipped_rows.append({
                    "pitcher_name": pitcher_name,
                    "reason": f"no usable opponent K% history for {opponent} in {target_season} or {prior_season}"
                })
                continue

            opponent_k_pct = (opp_k_p + LEAGUE_K_PCT * STABILIZER_BF) / (opp_bf_p + STABILIZER_BF)

        feature_rows.append({
            "date": pd.to_datetime(target_date), "season": target_season,
            "game_pk": row["game_pk"], "pitcher_id": int(pitcher_id),
            "pitcher_name": pitcher_name, "team": row["team"],
            "opponent": opponent, "home_away": int(row["home_away"]),
            "rolling_K_last_5":             last_5["strikeouts"].mean(),
            "rolling_IP_last_5":            last_5["innings_pitched"].mean(),
            "rolling_batters_faced_last_5": last_5["batters_faced"].mean(),
            "season_K_per_9":  season_k_per_9,
            "opponent_k_pct":  opponent_k_pct,
            "prior_starts_total":       len(pitcher_hist),
            "prior_starts_this_season": len(season_hist),
        })

    return pd.DataFrame(feature_rows), pd.DataFrame(skipped_rows)

def load_and_parse_sportsbook_lines(target_date):
    if not os.path.exists(SPORTSBOOK_LINES_PATH):
        print(f"No sportsbook lines file found at: {SPORTSBOOK_LINES_PATH}")
        return pd.DataFrame()
    lines = pd.read_csv(SPORTSBOOK_LINES_PATH)
    if lines.empty:
        print("sportsbook_lines.csv exists but is empty.")
        return pd.DataFrame()
    if "date" in lines.columns:
        lines["date"] = pd.to_datetime(lines["date"], errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
        lines = lines[lines["date"] == pd.to_datetime(target_date).normalize()].copy()
    if lines.empty:
        print(f"No sportsbook lines found for {target_date}.")
        return pd.DataFrame()
    lines["line"] = pd.to_numeric(lines["line"], errors="coerce")
    lines = lines[lines["line"].isin(HALF_LINE_THRESHOLDS)].copy()
    if lines.empty:
        print(f"No sportsbook lines matched configured thresholds for {target_date}.")
        return pd.DataFrame()
    if {"player_name", "line", "side", "odds"}.issubset(lines.columns):
        lines["pitcher_name_norm"] = lines["player_name"].apply(normalize_name)
        lines["side"] = lines["side"].astype(str).str.strip().str.lower()
        wide = (lines.pivot_table(index=["date", "pitcher_name_norm", "line"],
                                  columns="side", values="odds", aggfunc="first").reset_index())
        wide.columns.name = None
        if "over"  in wide.columns: wide = wide.rename(columns={"over":  "over_odds"})
        if "under" in wide.columns: wide = wide.rename(columns={"under": "under_odds"})
        return wide
    if {"pitcher_name", "line", "over_odds", "under_odds"}.issubset(lines.columns):
        lines["pitcher_name_norm"] = lines["pitcher_name"].apply(normalize_name)
        return lines[["date", "pitcher_name_norm", "line", "over_odds", "under_odds"]].copy()
    print("sportsbook_lines.csv format not recognized.")
    return pd.DataFrame()

# =============================================================================
# STEP 1: LOAD HISTORICAL DATASET
# =============================================================================

print(f"Loading historical dataset from: {DATASET_PATH}")
hist_df = pd.read_parquet(DATASET_PATH)
hist_df["date"] = pd.to_datetime(hist_df["date"]).dt.normalize()
print(f"Loaded {len(hist_df):,} historical rows")
print(f"Historical range: {hist_df['date'].min().date()} -> {hist_df['date'].max().date()}")

# =============================================================================
# STEP 2: PULL TODAY'S PROBABLE STARTERS
# =============================================================================

print(f"\nPulling probable starters for {TARGET_DATE}...")
live_df = get_probable_pitchers_for_date(TARGET_DATE)
if live_df.empty:
    raise SystemExit("No probable pitchers found. Exiting.")
print(f"Found {len(live_df):,} probable starters")
print(live_df[["pitcher_name", "team", "opponent", "home_away"]].to_string(index=False))

# =============================================================================
# STEP 3: BUILD LIVE FEATURES
# =============================================================================

print(f"\nBuilding live feature rows for {TARGET_DATE}...")
features_df, skipped_df = build_live_features(live_df, hist_df, TARGET_DATE)
if not skipped_df.empty:
    print("\nSkipped pitchers:")
    print(skipped_df.to_string(index=False))
if features_df.empty:
    raise SystemExit("No live rows had enough prior data to score. Exiting.")
print(f"\nBuilt features for {len(features_df):,} pitchers")

# =============================================================================
# STEP 4: LOAD TRAINED MODEL + SCALER
# =============================================================================

if not os.path.exists(MODEL_PATH):  raise FileNotFoundError(f"Missing model file: {MODEL_PATH}")
if not os.path.exists(SCALER_PATH): raise FileNotFoundError(f"Missing scaler file: {SCALER_PATH}")

with open(MODEL_PATH,  "rb") as f: nb_model = pickle.load(f)
with open(SCALER_PATH, "rb") as f: scaler   = pickle.load(f)
print(f"\nLoaded model from: {MODEL_PATH}")
print(f"Loaded scaler from: {SCALER_PATH}")

# =============================================================================
# STEP 5: SCORE LIVE GAMES
# =============================================================================

X_live        = features_df[FEATURE_COLS].copy()
X_live_scaled = scaler.transform(X_live)
X_live_nb     = sm.add_constant(X_live_scaled, has_constant="add")
mu_live       = np.asarray(nb_model.predict(X_live_nb))

print(f"\nRunning {N_SIMS:,} simulations per live pitcher...")
rng   = np.random.default_rng(seed=42)
draws = simulate_nb_draws(mu_live, NB_ALPHA, N_SIMS, SIM_CLIP_MAX, rng)

sim_mean, sim_median, sim_std = draws.mean(axis=1), np.median(draws, axis=1), draws.std(axis=1)

prob_cols, half_line_cols = {}, {}
for thresh in PROB_THRESHOLDS:
    prob_cols[f"p_over_{thresh}"] = (draws >= thresh).mean(axis=1)
for line in HALF_LINE_THRESHOLDS:
    label  = str(line).replace(".", "_")
    p_over = (draws >= int(np.floor(line) + 1)).mean(axis=1)
    half_line_cols[f"p_over_{label}"]  = p_over
    half_line_cols[f"p_under_{label}"] = 1.0 - p_over

results = features_df[[
    "date", "season", "game_pk", "pitcher_id", "pitcher_name",
    "team", "opponent", "home_away", "prior_starts_total", "prior_starts_this_season"
]].copy()
results["predicted_mean"]    = np.round(mu_live, 3)
results["simulated_mean"]    = np.round(sim_mean, 3)
results["simulated_median"]  = sim_median.astype(int)
results["simulated_std"]     = np.round(sim_std, 3)
results["pitcher_name_norm"] = results["pitcher_name"].apply(normalize_name)
for col, vals in prob_cols.items():      results[col] = np.round(vals, 4)
for col, vals in half_line_cols.items(): results[col] = np.round(vals, 4)

# =============================================================================
# STEP 6: MERGE WITH SPORTSBOOK LINES
# =============================================================================

lines_wide = load_and_parse_sportsbook_lines(TARGET_DATE)

if not lines_wide.empty:
    betting_df = results.copy()

    for line in HALF_LINE_THRESHOLDS:
        label = str(line).replace(".", "_")
        tmp   = lines_wide[lines_wide["line"] == line].copy()
        if tmp.empty: continue
        tmp = tmp[["pitcher_name_norm", "over_odds", "under_odds"]].rename(columns={
            "over_odds": f"over_odds_{label}", "under_odds": f"under_odds_{label}"})
        betting_df = betting_df.merge(tmp, on="pitcher_name_norm", how="left")
        betting_df[f"implied_over_{label}"]  = betting_df[f"over_odds_{label}"].apply(
            lambda x: round(american_odds_to_implied(x), 4) if pd.notna(x) else np.nan)
        betting_df[f"implied_under_{label}"] = betting_df[f"under_odds_{label}"].apply(
            lambda x: round(american_odds_to_implied(x), 4) if pd.notna(x) else np.nan)
        betting_df[f"edge_over_{label}"]  = np.round(betting_df[f"p_over_{label}"]  - betting_df[f"implied_over_{label}"],  4)
        betting_df[f"edge_under_{label}"] = np.round(betting_df[f"p_under_{label}"] - betting_df[f"implied_under_{label}"], 4)

    edge_cols = [c for c in betting_df.columns if c.startswith("edge_")]
    betting_df["best_edge"] = betting_df[edge_cols].max(axis=1, skipna=True)
    betting_df = betting_df.sort_values("best_edge", ascending=False)

    # =========================================================================
    # STEP 6B: BUILD FILTERED BETS + ADD SIZING
    # =========================================================================

    bet_rows = []
    for _, row in betting_df.iterrows():
        for line in HALF_LINE_THRESHOLDS:
            label = str(line).replace(".", "_")
            for side in ("over", "under"):
                odds_col    = f"{side}_odds_{label}"
                implied_col = f"implied_{side}_{label}"
                edge_col    = f"edge_{side}_{label}"
                prob_col    = f"p_{side}_{label}"
                if odds_col not in betting_df.columns or edge_col not in betting_df.columns:
                    continue
                edge_val = row.get(edge_col, np.nan)
                if pd.notna(edge_val) and edge_val >= BET_EDGE_THRESHOLD and pd.notna(row.get(odds_col, np.nan)):
                    bet_rows.append({
                        "date": row["date"], "season": row["season"], "game_pk": row["game_pk"],
                        "pitcher_id": row["pitcher_id"], "pitcher_name": row["pitcher_name"],
                        "team": row["team"], "opponent": row["opponent"], "home_away": row["home_away"],
                        "line": float(line), "bet_side": side, "odds": row.get(odds_col, np.nan),
                        "model_prob":    row.get(prob_col,    np.nan),
                        "implied_prob":  row.get(implied_col, np.nan),
                        "edge":          edge_val,
                        "predicted_mean":   row["predicted_mean"],
                        "simulated_mean":   row["simulated_mean"],
                        "simulated_median": row["simulated_median"],
                        "simulated_std":    row["simulated_std"],
                    })

    filtered_bets = pd.DataFrame(bet_rows)

    if not filtered_bets.empty:
        if not ALLOW_MULTIPLE_BETS_PER_PITCHER:
            filtered_bets = (
                filtered_bets.sort_values(["pitcher_id", "edge"], ascending=[True, False])
                .groupby(["date", "pitcher_id"], as_index=False).head(1)
                .reset_index(drop=True)
            )
        filtered_bets["recommended_units"] = filtered_bets["edge"].apply(get_bet_size)
        filtered_bets["kelly_units"]       = filtered_bets.apply(
            lambda r: get_kelly_units(r["model_prob"], r["odds"]), axis=1)
        filtered_bets["actual_strikeouts"] = np.nan
        filtered_bets["bet_result"]        = ""
        filtered_bets["profit_units"]      = np.nan
        filtered_bets["settled"]           = False
        filtered_bets = filtered_bets.sort_values("edge", ascending=False).reset_index(drop=True)

        print("\n=== FILTERED BETS ===")
        print(filtered_bets[[
            "pitcher_name", "team", "opponent", "line", "bet_side",
            "odds", "model_prob", "implied_prob", "edge",
            "recommended_units", "kelly_units"
        ]].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

        # Save CSVs (pipeline source of truth — do not remove)
        filtered_bets.to_csv(FILTERED_BETS_PATH, index=False)
        print(f"\nSaved filtered bets to: {FILTERED_BETS_PATH}")

        if os.path.exists(BET_LOG_PATH):
            bet_log = pd.read_csv(BET_LOG_PATH)
        else:
            bet_log = pd.DataFrame()

        key_cols = ["date", "pitcher_id", "line", "bet_side", "odds"]
        filtered_bets["date"] = pd.to_datetime(filtered_bets["date"], errors="coerce").dt.normalize()

        if bet_log.empty:
            updated_bet_log = filtered_bets.copy()
        else:
            bet_log["date"] = pd.to_datetime(bet_log["date"], errors="coerce").dt.normalize()
            for col in filtered_bets.columns:
                if col not in bet_log.columns: bet_log[col] = np.nan
            for col in bet_log.columns:
                if col not in filtered_bets.columns: filtered_bets[col] = np.nan
            filtered_bets = filtered_bets[bet_log.columns]
            existing_keys = set(
                tuple(x) for x in bet_log[key_cols].itertuples(index=False, name=None)
                if all(pd.notna(v) for v in x)
            )
            new_rows = filtered_bets[
                ~filtered_bets[key_cols].apply(tuple, axis=1).isin(existing_keys)
            ].copy()
            updated_bet_log = bet_log.copy() if new_rows.empty else pd.concat([bet_log, new_rows], ignore_index=True)

        updated_bet_log.to_csv(BET_LOG_PATH, index=False)
        print(f"Updated bet log saved to: {BET_LOG_PATH}")

        # =====================================================================
        # EXCEL EXPORTS
        # =====================================================================
        try:
            export_filtered_bets(filtered_bets)
        except Exception as e:
            print(f"Warning: filtered_bets.xlsx export failed: {e}")

        try:
            export_bet_log(updated_bet_log)
        except Exception as e:
            print(f"Warning: bet_log.xlsx export failed: {e}")

    else:
        print(f"\nNo bets met the edge threshold of {BET_EDGE_THRESHOLD:.1%}.")

    print("\n=== CLEAN LIVE BETTING VIEW ===")
    print(betting_df.head(25).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    betting_df.to_csv(LIVE_PREDICTIONS_PATH, index=False)
    print(f"\nSaved clean betting view to: {LIVE_PREDICTIONS_PATH}")

else:
    print("\nNo sportsbook lines found.")
    results.to_csv(LIVE_PREDICTIONS_PATH, index=False)
    print(f"Saved live prediction file without sportsbook lines to: {LIVE_PREDICTIONS_PATH}")

# =============================================================================
# STEP 7: QUICK TOP MODEL PLAYS
# =============================================================================

print("\n=== TOP MODEL OVER PLAYS ===")
over_cols = [f"p_over_{str(line).replace('.', '_')}" for line in HALF_LINE_THRESHOLDS]
print(
    results[["pitcher_name", "team", "opponent", "predicted_mean", "simulated_mean"] + over_cols]
    .sort_values(f"p_over_{str(HALF_LINE_THRESHOLDS[min(2, len(HALF_LINE_THRESHOLDS)-1)]).replace('.', '_')}", ascending=False)
    .head(15).to_string(index=False, float_format=lambda x: f"{x:.3f}")
)
print("\n=== TOP MODEL UNDER PLAYS ===")
under_cols = [f"p_under_{str(line).replace('.', '_')}" for line in HALF_LINE_THRESHOLDS]
print(
    results[["pitcher_name", "team", "opponent", "predicted_mean", "simulated_mean"] + under_cols]
    .sort_values(f"p_under_{str(HALF_LINE_THRESHOLDS[min(2, len(HALF_LINE_THRESHOLDS)-1)]).replace('.', '_')}", ascending=False)
    .head(15).to_string(index=False, float_format=lambda x: f"{x:.3f}")
)

print("\nlive_predictions.py complete.")