import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

# =========================
# LOAD DATA FROM GITHUB
# =========================
BASE_URL = "https://raw.githubusercontent.com/andrewrust04-blip/mlb-betting-model/main/"

def load_csv(file):
    try:
        return pd.read_csv(BASE_URL + file)
    except:
        return pd.DataFrame()

bet_log = load_csv("bet_log.csv")
filtered_bets = load_csv("filtered_bets.csv")
summary = load_csv("dashboard_summary.csv")
by_line = load_csv("dashboard_by_line.csv")
by_edge = load_csv("dashboard_by_edge.csv")
by_side = load_csv("dashboard_by_side.csv")

# =========================
# TITLE
# =========================
st.title("MLB Strikeout Betting Dashboard")

# =========================
# TODAY'S BETS
# =========================
st.header("Today's Bets")

if not filtered_bets.empty:
    st.dataframe(filtered_bets, use_container_width=True)
else:
    st.write("No bets today.")

# =========================
# SUMMARY
# =========================
st.header("Performance Summary")

if not summary.empty:
    cols = st.columns(len(summary))
    for i, row in summary.iterrows():
        cols[i].metric(row["metric"], row["value"])
else:
    st.write("No summary data yet.")

# =========================
# BET LOG
# =========================
st.header("Bet Log")

if not bet_log.empty:
    st.dataframe(bet_log, use_container_width=True)
else:
    st.write("No bet log yet.")

# =========================
# PERFORMANCE TABLES
# =========================
st.header("Performance Breakdown")

col1, col2 = st.columns(2)

with col1:
    st.subheader("By Line")
    if not by_line.empty:
        st.dataframe(by_line, use_container_width=True)

    st.subheader("By Edge")
    if not by_edge.empty:
        st.dataframe(by_edge, use_container_width=True)

with col2:
    st.subheader("Over vs Under")
    if not by_side.empty:
        st.dataframe(by_side, use_container_width=True)

# =========================
# PROFIT OVER TIME
# =========================
st.header("Profit Over Time")

if not bet_log.empty and "profit_units" in bet_log.columns:
    bet_log["date"] = pd.to_datetime(bet_log["date"])
    bet_log = bet_log.sort_values("date")
    bet_log["cum_profit"] = bet_log["profit_units"].cumsum()

    st.line_chart(bet_log.set_index("date")["cum_profit"])
