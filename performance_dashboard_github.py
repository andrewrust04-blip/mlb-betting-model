# performance_dashboard.py
# Analyze MLB pitcher strikeout betting performance.
#
# What this script does:
# 1. Loads bet_log.csv
# 2. Keeps only settled bets
# 3. Shows overall performance
# 4. Compares flat staking vs recommended sizing vs Kelly sizing
# 5. Breaks down performance by side, line, and edge bucket
# 6. Shows top and worst bets
#
# Output:
#   console summary only

import os
import sys
import numpy as np
import pandas as pd

from config_github import BET_LOG_PATH


# =============================================================================
# LOAD DATA
# =============================================================================

if not os.path.exists(BET_LOG_PATH):
    raise FileNotFoundError(f"bet_log.csv not found: {BET_LOG_PATH}")

df = pd.read_csv(BET_LOG_PATH)

# -----------------------------------------------------------------------------
# CLEAN TYPES
# -----------------------------------------------------------------------------

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["profit_units"] = pd.to_numeric(df.get("profit_units"), errors="coerce")
df["edge"] = pd.to_numeric(df.get("edge"), errors="coerce")
df["odds"] = pd.to_numeric(df.get("odds"), errors="coerce")
df["line"] = pd.to_numeric(df.get("line"), errors="coerce")

if "recommended_units" in df.columns:
    df["recommended_units"] = pd.to_numeric(df["recommended_units"], errors="coerce")
else:
    df["recommended_units"] = 1.0

if "kelly_units" in df.columns:
    df["kelly_units"] = pd.to_numeric(df["kelly_units"], errors="coerce")
else:
    df["kelly_units"] = 0.0

if "settled" in df.columns:
    df["settled"] = (
        df["settled"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False})
    )
else:
    df["settled"] = False

if "bet_result" not in df.columns:
    df["bet_result"] = ""

# -----------------------------------------------------------------------------
# KEEP ONLY SETTLED BETS
# -----------------------------------------------------------------------------

df = df[df["settled"] == True].copy()

if df.empty:
    print("No settled bets yet.")
    sys.exit()

# =============================================================================
# BUILD STAKING COMPARISON COLUMNS
# =============================================================================

# Flat staking = 1 unit per bet
df["profit_flat"] = df["profit_units"]

# Recommended staking
df["recommended_units"] = df["recommended_units"].fillna(1.0)
df["profit_recommended"] = df["profit_units"] * df["recommended_units"]

# Kelly staking
df["kelly_units"] = df["kelly_units"].fillna(0.0)
df["profit_kelly"] = df["profit_units"] * df["kelly_units"]

# Risk amounts
df["risk_flat"] = 1.0
df["risk_recommended"] = df["recommended_units"]
df["risk_kelly"] = df["kelly_units"]

# =============================================================================
# OVERALL PERFORMANCE
# =============================================================================

total_bets = len(df)
wins = int((df["bet_result"] == "win").sum())
losses = int((df["bet_result"] == "loss").sum())
pushes = int((df["bet_result"] == "push").sum())

decision_bets = wins + losses
win_rate = wins / decision_bets if decision_bets > 0 else np.nan

flat_profit = df["profit_flat"].sum()
recommended_profit = df["profit_recommended"].sum()
kelly_profit = df["profit_kelly"].sum()

flat_risk = df["risk_flat"].sum()
recommended_risk = df["risk_recommended"].sum()
kelly_risk = df["risk_kelly"].sum()

flat_roi = flat_profit / flat_risk if flat_risk > 0 else np.nan
recommended_roi = recommended_profit / recommended_risk if recommended_risk > 0 else np.nan
kelly_roi = kelly_profit / kelly_risk if kelly_risk > 0 else np.nan

print("\n=== OVERALL PERFORMANCE ===")
print(f"Settled Bets:        {total_bets}")
print(f"Wins:                {wins}")
print(f"Losses:              {losses}")
print(f"Pushes:              {pushes}")
print(f"Win Rate:            {win_rate:.3f}" if pd.notna(win_rate) else "Win Rate:            n/a")
print(f"Flat Profit:         {flat_profit:.3f} units")
print(f"Flat ROI:            {flat_roi:.3f}" if pd.notna(flat_roi) else "Flat ROI:            n/a")
print(f"Recommended Profit:  {recommended_profit:.3f} units")
print(f"Recommended ROI:     {recommended_roi:.3f}" if pd.notna(recommended_roi) else "Recommended ROI:     n/a")
print(f"Kelly Profit:        {kelly_profit:.3f} units")
print(f"Kelly ROI:           {kelly_roi:.3f}" if pd.notna(kelly_roi) else "Kelly ROI:           n/a")

# =============================================================================
# SIDE BREAKDOWN
# =============================================================================

print("\n=== OVER vs UNDER PERFORMANCE ===")

side_summary = (
    df.groupby("bet_side", dropna=False)
    .agg(
        bets=("bet_side", "count"),
        wins=("bet_result", lambda x: (x == "win").sum()),
        losses=("bet_result", lambda x: (x == "loss").sum()),
        pushes=("bet_result", lambda x: (x == "push").sum()),
        flat_profit=("profit_flat", "sum"),
        rec_profit=("profit_recommended", "sum"),
        kelly_profit=("profit_kelly", "sum"),
        flat_risk=("risk_flat", "sum"),
        rec_risk=("risk_recommended", "sum"),
        kelly_risk=("risk_kelly", "sum"),
    )
    .reset_index()
)

side_summary["win_rate"] = np.where(
    (side_summary["wins"] + side_summary["losses"]) > 0,
    side_summary["wins"] / (side_summary["wins"] + side_summary["losses"]),
    np.nan
)
side_summary["flat_roi"] = side_summary["flat_profit"] / side_summary["flat_risk"]
side_summary["rec_roi"] = np.where(side_summary["rec_risk"] > 0, side_summary["rec_profit"] / side_summary["rec_risk"], np.nan)
side_summary["kelly_roi"] = np.where(side_summary["kelly_risk"] > 0, side_summary["kelly_profit"] / side_summary["kelly_risk"], np.nan)

print(side_summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

# =============================================================================
# LINE BREAKDOWN
# =============================================================================

print("\n=== PERFORMANCE BY LINE ===")

line_summary = (
    df.groupby("line", dropna=False)
    .agg(
        bets=("line", "count"),
        wins=("bet_result", lambda x: (x == "win").sum()),
        losses=("bet_result", lambda x: (x == "loss").sum()),
        pushes=("bet_result", lambda x: (x == "push").sum()),
        flat_profit=("profit_flat", "sum"),
        rec_profit=("profit_recommended", "sum"),
        kelly_profit=("profit_kelly", "sum"),
        flat_risk=("risk_flat", "sum"),
        rec_risk=("risk_recommended", "sum"),
        kelly_risk=("risk_kelly", "sum"),
    )
    .reset_index()
    .sort_values("line")
)

line_summary["win_rate"] = np.where(
    (line_summary["wins"] + line_summary["losses"]) > 0,
    line_summary["wins"] / (line_summary["wins"] + line_summary["losses"]),
    np.nan
)
line_summary["flat_roi"] = line_summary["flat_profit"] / line_summary["flat_risk"]
line_summary["rec_roi"] = np.where(line_summary["rec_risk"] > 0, line_summary["rec_profit"] / line_summary["rec_risk"], np.nan)
line_summary["kelly_roi"] = np.where(line_summary["kelly_risk"] > 0, line_summary["kelly_profit"] / line_summary["kelly_risk"], np.nan)

print(line_summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

# =============================================================================
# EDGE BUCKET PERFORMANCE
# =============================================================================

print("\n=== EDGE BUCKET PERFORMANCE ===")

bins = [0, 0.05, 0.075, 0.10, 0.15, 1.00]
labels = ["0-5%", "5-7.5%", "7.5-10%", "10-15%", "15%+"]

df["edge_bucket"] = pd.cut(df["edge"], bins=bins, labels=labels, include_lowest=True)

edge_summary = (
    df.groupby("edge_bucket", dropna=False, observed=False)
    .agg(
        bets=("edge", "count"),
        wins=("bet_result", lambda x: (x == "win").sum()),
        losses=("bet_result", lambda x: (x == "loss").sum()),
        pushes=("bet_result", lambda x: (x == "push").sum()),
        avg_edge=("edge", "mean"),
        flat_profit=("profit_flat", "sum"),
        rec_profit=("profit_recommended", "sum"),
        kelly_profit=("profit_kelly", "sum"),
        flat_risk=("risk_flat", "sum"),
        rec_risk=("risk_recommended", "sum"),
        kelly_risk=("risk_kelly", "sum"),
    )
    .reset_index()
)

edge_summary["win_rate"] = np.where(
    (edge_summary["wins"] + edge_summary["losses"]) > 0,
    edge_summary["wins"] / (edge_summary["wins"] + edge_summary["losses"]),
    np.nan
)
edge_summary["flat_roi"] = np.where(edge_summary["flat_risk"] > 0, edge_summary["flat_profit"] / edge_summary["flat_risk"], np.nan)
edge_summary["rec_roi"] = np.where(edge_summary["rec_risk"] > 0, edge_summary["rec_profit"] / edge_summary["rec_risk"], np.nan)
edge_summary["kelly_roi"] = np.where(edge_summary["kelly_risk"] > 0, edge_summary["kelly_profit"] / edge_summary["kelly_risk"], np.nan)

print(edge_summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

# =============================================================================
# DATE BREAKDOWN
# =============================================================================

print("\n=== DAILY PERFORMANCE ===")

daily_summary = (
    df.groupby(df["date"].dt.date)
    .agg(
        bets=("date", "count"),
        flat_profit=("profit_flat", "sum"),
        rec_profit=("profit_recommended", "sum"),
        kelly_profit=("profit_kelly", "sum"),
        flat_risk=("risk_flat", "sum"),
        rec_risk=("risk_recommended", "sum"),
        kelly_risk=("risk_kelly", "sum"),
    )
    .reset_index()
    .rename(columns={"date": "bet_date"})
)

daily_summary["flat_roi"] = np.where(daily_summary["flat_risk"] > 0, daily_summary["flat_profit"] / daily_summary["flat_risk"], np.nan)
daily_summary["rec_roi"] = np.where(daily_summary["rec_risk"] > 0, daily_summary["rec_profit"] / daily_summary["rec_risk"], np.nan)
daily_summary["kelly_roi"] = np.where(daily_summary["kelly_risk"] > 0, daily_summary["kelly_profit"] / daily_summary["kelly_risk"], np.nan)

print(daily_summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

# =============================================================================
# TOP / WORST BETS
# =============================================================================

display_cols = [
    "date", "pitcher_name", "team", "opponent", "line", "bet_side",
    "odds", "edge", "recommended_units", "kelly_units",
    "actual_strikeouts", "bet_result", "profit_flat", "profit_recommended", "profit_kelly"
]
display_cols = [c for c in display_cols if c in df.columns]

print("\n=== TOP 10 EDGES ===")
print(
    df.sort_values("edge", ascending=False)[display_cols]
    .head(10)
    .to_string(index=False, float_format=lambda x: f"{x:.3f}")
)

print("\n=== TOP 10 WINNERS (FLAT) ===")
print(
    df.sort_values("profit_flat", ascending=False)[display_cols]
    .head(10)
    .to_string(index=False, float_format=lambda x: f"{x:.3f}")
)

print("\n=== TOP 10 LOSERS (FLAT) ===")
print(
    df.sort_values("profit_flat", ascending=True)[display_cols]
    .head(10)
    .to_string(index=False, float_format=lambda x: f"{x:.3f}")
)


# =============================================================================
# CALIBRATION ANALYSIS
# =============================================================================

print("\n=== CALIBRATION (MODEL PROB vs ACTUAL WIN RATE) ===")

# Only use bets that have a result
calib_df = df[df["bet_result"].isin(["win", "loss"])].copy()

if calib_df.empty:
    print("No settled bets available for calibration.")
else:
    # Create probability buckets
    bins = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
    labels = ["50-55%", "55-60%", "60-65%", "65-70%", "70-75%", "75-80%"]

    calib_df["prob_bucket"] = pd.cut(calib_df["model_prob"], bins=bins, labels=labels)

    calibration_table = (
        calib_df.groupby("prob_bucket")
        .agg(
            bets=("model_prob", "count"),
            wins=("bet_result", lambda x: (x == "win").sum())
        )
        .reset_index()
    )

    calibration_table["win_rate"] = calibration_table["wins"] / calibration_table["bets"]

    print(calibration_table.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

print("\nperformance_dashboard.py complete.")

# =============================================================================
# SAVE OUTPUTS FOR STREAMLIT UI
# =============================================================================

# ---- SUMMARY ----
summary_df = pd.DataFrame({
    "metric": [
        "total_bets", "wins", "losses", "pushes",
        "win_rate", "flat_profit", "flat_roi",
        "recommended_profit", "recommended_roi",
        "kelly_profit", "kelly_roi"
    ],
    "value": [
        total_bets, wins, losses, pushes,
        win_rate, flat_profit, flat_roi,
        recommended_profit, recommended_roi,
        kelly_profit, kelly_roi
    ]
})

summary_df.to_csv("dashboard_summary.csv", index=False)

# ---- BY LINE ----
line_summary.to_csv("dashboard_by_line.csv", index=False)

# ---- BY EDGE ----
edge_summary.to_csv("dashboard_by_edge.csv", index=False)

# ---- BY SIDE ----
side_summary.to_csv("dashboard_by_side.csv", index=False)

# ---- CALIBRATION ----
calibration_table.to_csv("dashboard_calibration.csv", index=False)

print("\nSaved dashboard CSV files for Streamlit.")