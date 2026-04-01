import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="MLB Dashboard", layout="wide")

# =========================
# LIGHTER UI STYLE
# =========================
st.markdown("""
<style>
.stApp { background: #f7f9fc; color: #1e293b; }
.metric-box { background: white; padding: 12px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# =========================
# LOAD DATA
# =========================
BASE_URL = "https://raw.githubusercontent.com/andrewrust04-blip/mlb-betting-model/main/"

@st.cache_data(ttl=300)
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
# HEADER
# =========================
st.title("⚾ MLB Strikeout Dashboard")

# =========================
# TODAY METRICS
# =========================
if not filtered_bets.empty:
    today_profit = filtered_bets.get("profit_units", pd.Series()).sum()
    today_bets = len(filtered_bets)
else:
    today_profit = 0
    today_bets = 0

col1, col2, col3 = st.columns(3)
col1.metric("Today's Bets", today_bets)
col2.metric("Today's Profit", f"{today_profit:.2f}u")
col3.metric("Avg Edge", f"{filtered_bets['edge'].mean()*100:.1f}%" if not filtered_bets.empty else "0%")

# =========================
# TOP PLAYS
# =========================
st.subheader("🔥 Top Plays Today")

if not filtered_bets.empty:
    top_plays = filtered_bets.sort_values("edge", ascending=False).head(5)
    st.dataframe(top_plays[["pitcher_name","line","bet_side","edge","recommended_units"]], use_container_width=True)

# =========================
# FILTER
# =========================
st.subheader("Today's Bets")

filter_option = st.selectbox("Filter", ["All","Overs","Unders","High Edge (>10%)"])

df = filtered_bets.copy()

if filter_option == "Overs":
    df = df[df["bet_side"] == "over"]
elif filter_option == "Unders":
    df = df[df["bet_side"] == "under"]
elif filter_option == "High Edge (>10%)":
    df = df[df["edge"] > 0.10]

# =========================
# MAIN TABLE (SORTED)
# =========================
if not df.empty:
    df = df.sort_values("edge", ascending=False)

    st.dataframe(df, use_container_width=True)

# =========================
# BANKROLL TRACKING
# =========================
st.subheader("📈 Bankroll")

if not bet_log.empty:
    bet_log["profit_units"] = pd.to_numeric(bet_log["profit_units"], errors="coerce").fillna(0)
    bet_log["bankroll"] = 100 + bet_log["profit_units"].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=bet_log["date"],
        y=bet_log["bankroll"],
        mode="lines",
        line=dict(width=3)
    ))

    st.plotly_chart(fig, use_container_width=True)

# =========================
# PERFORMANCE BREAKDOWN
# =========================
st.subheader("Performance Breakdown")

col1, col2, col3 = st.columns(3)

with col1:
    st.write("By Line")
    st.dataframe(by_line)

with col2:
    st.write("By Edge")
    st.dataframe(by_edge)

with col3:
    st.write("Over / Under")
    st.dataframe(by_side)

# =========================
# BET LOG
# =========================
st.subheader("Full Bet Log")

if not bet_log.empty:
    st.dataframe(bet_log.sort_values("date", ascending=False), use_container_width=True)
