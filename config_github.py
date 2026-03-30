# config.py
# Shared configuration for the MLB pitcher strikeout betting project.
# All scripts import from here — change values in one place, affects all scripts.

import os

# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Intermediate dataset saved by build_dataset.py, loaded by train_model.py
DATASET_PATH = os.path.join(BASE_DIR, "pitcher_game_features.parquet")

# Predictions saved by train_model.py, loaded by betting_report.py
PREDICTIONS_PATH = os.path.join(BASE_DIR, "predictions.parquet")

# Final betting report saved by betting_report.py
REPORT_PATH = os.path.join(BASE_DIR, "betting_report.csv")

# Saved model objects from train_model.py
MODEL_PATH = os.path.join(BASE_DIR, "nb_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "scaler.pkl")

# Live outputs
SPORTSBOOK_LINES_PATH = os.path.join(BASE_DIR, "sportsbook_lines.csv")
LIVE_PREDICTIONS_PATH = os.path.join(BASE_DIR, "live_predictions.csv")
FILTERED_BETS_PATH = os.path.join(BASE_DIR, "filtered_bets.csv")
BET_LOG_PATH = os.path.join(BASE_DIR, "bet_log.csv")

# =============================================================================
# DATA PIPELINE
# =============================================================================

# Seasons to pull. Comment out seasons you don't need.
SEASON_DATES = {
    2025: ("2025-03-20", "2025-09-29"),
    2024: ("2024-03-28", "2024-09-29"),
    2023: ("2023-03-30", "2023-10-01"),
    2022: ("2022-04-07", "2022-10-05"),
    2021: ("2021-04-01", "2021-10-03"),
}

# Minimum innings pitched to qualify as a true starting pitcher outing.
# Openers typically pitch 1-2 innings; 3.0 IP cleanly excludes most of them.
MIN_IP_STARTER_THRESHOLD = 3.0

# =============================================================================
# FEATURE ENGINEERING
# =============================================================================

# Rolling window size (in starts) for rolling features
ROLLING_WINDOW = 5

FEATURE_COLS = [
    "rolling_K_last_5",
    "rolling_IP_last_5",
    "rolling_batters_faced_last_5",
    "season_K_per_9",
    "opponent_k_pct",
    "home_away",
]

TARGET_COL = "strikeouts"

# =============================================================================
# SIMULATION
# =============================================================================

# Monte Carlo draws per pitcher-game.
# 1000 gives stable probability estimates (~1.6% std error at p=0.5).
N_SIMS = 1000

# Negative Binomial overdispersion parameter (NB2 parameterization).
# variance = mu + NB_ALPHA * mu^2
# alpha=0.05 established in v7 as reasonable after testing.
NB_ALPHA = 0.05

# Clip simulated draws at this maximum (removes unrealistic tail values)
SIM_CLIP_MAX = 15

# Integer thresholds for P(K >= N) columns
PROB_THRESHOLDS = [2, 3, 4, 5, 6, 7, 8, 9]

# Expanded half-line thresholds for live betting / backtesting
HALF_LINE_THRESHOLDS = [3.5, 4.5, 5.5, 6.5, 7.5, 8.5]

# =============================================================================
# LIVE BET FILTERING
# =============================================================================

# Minimum edge required for a bet to qualify
BET_EDGE_THRESHOLD = 0.05

# If True, allow multiple bets on the same pitcher across different lines.
# If False, keep only the single best edge per pitcher.
ALLOW_MULTIPLE_BETS_PER_PITCHER = False

# =============================================================================
# SPORTSBOOK ODDS (HARDCODED PLACEHOLDERS — REPLACE WITH SCRAPED LINES LATER)
# =============================================================================
# Format: { line: (over_odds, under_odds) } in American odds
# Example: -110 means risk $110 to win $100

SPORTSBOOK_LINES = {
    3.5: (-140, 110),
    4.5: (-115, -105),
    5.5: (-110, -110),
    6.5: (-105, -115),
    7.5: (120, -150),
    8.5: (160, -200),
}

# =============================================================================
# VALIDATION / DIAGNOSTICS
# =============================================================================

# Print warning if a pitcher-season has more starts than this
MAX_REASONABLE_STARTS = 40

# Number of sample pitchers to print in validation block
SAMPLE_PITCHERS_TO_PRINT = 10

# Calibration bin threshold (used in diagnostics panel B)
CALIB_THRESHOLD = 5