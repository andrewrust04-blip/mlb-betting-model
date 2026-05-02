# config_github.py
# Shared configuration for the MLB pitcher strikeout betting project.
# All scripts import from here — change values in one place, affects all scripts.

import os

# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Intermediate dataset saved by build_dataset.py, loaded by train_model.py
DATASET_PATH = os.path.join(BASE_DIR, "pitcher_game_features.parquet")

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

# Rolling window size, in starts, for rolling features.
ROLLING_WINDOW = 5

# League-average strikeout rate used as a fallback/stabilizer.
# This is approximate and can be adjusted later if we want.
LEAGUE_K_PCT = 0.22

# Controls pitcher K-rate blending.
# Higher number = prior-season K rate matters longer into the new season.
# Lower number = current-season K rate takes over faster.
PITCHER_K_RATE_STABILIZER_BF = 150

# Controls opponent K% blending.
# This makes opponent K% rely more on prior-season data early in the year,
# then gradually rely more on current-season opponent K% as sample size grows.
OPPONENT_K_STABILIZER_BF = 600

# Cap days rest so weird long gaps/injuries do not dominate the model.
DAYS_REST_CAP = 14

# Features used by the Negative Binomial model.
# These must exist in pitcher_game_features.parquet before training.
FEATURE_COLS = [
    # Pitcher strikeout skill
    "rolling_K_rate_last_5",
    "blended_K_rate",

    # Pitcher opportunity/workload
    "rolling_IP_last_5",
    "rolling_batters_faced_last_5",
    "rolling_pitch_count_last_5",
    "days_rest",

    # Opponent strikeout tendency
    "smoothed_opponent_k_pct",

    # Game context
    "home_away",
]

TARGET_COL = "strikeouts"

# =============================================================================
# SIMULATION
# =============================================================================

# Monte Carlo draws per pitcher-game.
# 1000 gives stable probability estimates.
N_SIMS = 1000

# Negative Binomial overdispersion parameter.
# NB2 parameterization: variance = mu + NB_ALPHA * mu^2
NB_ALPHA = 0.05

# Clip simulated draws at this maximum to remove unrealistic tail values.
SIM_CLIP_MAX = 15

# Integer thresholds for P(K >= N) columns.
PROB_THRESHOLDS = [2, 3, 4, 5, 6, 7, 8, 9]

# Half-line thresholds for live betting/backtesting.
HALF_LINE_THRESHOLDS = [3.5, 4.5, 5.5, 6.5, 7.5, 8.5]

# =============================================================================
# LIVE BET FILTERING
# =============================================================================

# Minimum edge required for a bet to qualify.
BET_EDGE_THRESHOLD = 0.05

# If True, allow multiple bets on the same pitcher across different lines.
# If False, keep only the single best edge per pitcher.
ALLOW_MULTIPLE_BETS_PER_PITCHER = False

# =============================================================================
# SPORTSBOOK ODDS PLACEHOLDERS
# =============================================================================
# Format: {line: (over_odds, under_odds)} in American odds.
# These are only fallback placeholders. Live props come from sportsbook_lines.csv.

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

# Print warning if a pitcher-season has more starts than this.
MAX_REASONABLE_STARTS = 40

# Number of sample pitchers to print in validation block.
SAMPLE_PITCHERS_TO_PRINT = 10

# Calibration bin threshold used in diagnostics.
CALIB_THRESHOLD = 5