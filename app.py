import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="MLB Strikeout Dashboard",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# CUSTOM CSS — Navy Pro Look
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* ── Reset & Base ── */
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}
#MainMenu, footer, header { visibility: hidden; }

.stApp {
    background: #060d1f;
    background-image:
        radial-gradient(ellipse 80% 40% at 50% -10%, rgba(30,80,180,0.18) 0%, transparent 70%),
        repeating-linear-gradient(0deg, transparent, transparent 39px, rgba(255,255,255,0.02) 39px, rgba(255,255,255,0.02) 40px),
        repeating-linear-gradient(90deg, transparent, transparent 39px, rgba(255,255,255,0.02) 39px, rgba(255,255,255,0.02) 40px);
}

.block-container {
    padding: 1.5rem 1rem 3rem 1rem !important;
    max-width: 1200px !important;
}

/* ── Header ── */
.dash-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
    padding: 0 2px 20px 2px;
    border-bottom: 1px solid rgba(99,150,255,0.15);
    margin-bottom: 20px;
}
.dash-title {
    font-size: clamp(20px, 4vw, 28px);
    font-weight: 700;
    color: #e8eeff;
    letter-spacing: -0.03em;
    line-height: 1;
}
.dash-title span { color: #4d8fff; }
.dash-pill {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    background: rgba(77,143,255,0.12);
    border: 1px solid rgba(77,143,255,0.3);
    color: #7eb5ff;
    padding: 4px 12px;
    border-radius: 20px;
    white-space: nowrap;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(99,150,255,0.12);
    border-radius: 10px;
    padding: 4px;
    margin-bottom: 20px;
}
.stTabs [data-baseweb="tab"] {
    height: 36px;
    padding: 0 18px;
    font-size: 13px;
    font-weight: 500;
    color: #8fafd4;
    background: transparent;
    border: none;
    border-radius: 7px;
    letter-spacing: 0.01em;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    color: #e8eeff !important;
    background: rgba(77,143,255,0.2) !important;
    box-shadow: 0 0 0 1px rgba(77,143,255,0.35) !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding: 0; }

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, rgba(10,25,60,0.9) 0%, rgba(6,18,45,0.95) 100%);
    border: 1px solid rgba(77,143,255,0.18);
    border-radius: 12px;
    padding: 16px 18px 14px 18px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
[data-testid="metric-container"]:hover {
    border-color: rgba(77,143,255,0.4);
}
[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #1a4fff, #4d8fff, transparent);
    border-radius: 12px 12px 0 0;
}
[data-testid="metric-container"] label {
    color: #8fafd4 !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: clamp(22px, 3vw, 30px) !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    font-family: 'IBM Plex Mono', monospace !important;
    line-height: 1.1 !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 12px !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* ── Section headers ── */
.section-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #7a9cc4;
    margin: 0 0 10px 2px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(77,143,255,0.3), transparent);
}

/* ── Dataframe ── */
.stDataFrame {
    border: 1px solid rgba(77,143,255,0.15) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    background: rgba(6,15,40,0.8) !important;
}
[data-testid="stDataFrameResizable"] {
    border-radius: 12px;
}
/* Dataframe header row */
[data-testid="stDataFrameResizable"] thead th {
    background: rgba(10,25,65,0.95) !important;
    color: #8fafd4 !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid rgba(77,143,255,0.2) !important;
}
[data-testid="stDataFrameResizable"] tbody tr {
    border-bottom: 1px solid rgba(77,143,255,0.06) !important;
}
[data-testid="stDataFrameResizable"] tbody tr:hover td {
    background: rgba(77,143,255,0.1) !important;
}
[data-testid="stDataFrameResizable"] tbody td {
    color: #dde8f8 !important;
    font-size: 13px !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* ── Selectbox / filters ── */
.stSelectbox label, .stMultiSelect label, .stDateInput label {
    font-size: 10px !important;
    font-weight: 700 !important;
    color: #8fafd4 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}
[data-baseweb="select"] {
    background: rgba(6,15,40,0.9) !important;
    border: 1px solid rgba(77,143,255,0.2) !important;
    border-radius: 8px !important;
}
[data-baseweb="select"] > div {
    background: transparent !important;
    color: #dde8f8 !important;
    font-size: 13px !important;
    border-color: rgba(77,143,255,0.2) !important;
}
[data-baseweb="popover"] {
    background: #0a1940 !important;
    border: 1px solid rgba(77,143,255,0.25) !important;
}
[data-baseweb="menu"] {
    background: #0a1940 !important;
}
[data-baseweb="option"] {
    color: #dde8f8 !important;
    background: #0a1940 !important;
    font-size: 13px !important;
}
[data-baseweb="option"]:hover {
    background: rgba(77,143,255,0.15) !important;
}

/* ── Date input ── */
[data-baseweb="input"] {
    background: rgba(6,15,40,0.9) !important;
    border-color: rgba(77,143,255,0.2) !important;
    color: #a8bde8 !important;
    border-radius: 8px !important;
}
[data-baseweb="input"] input {
    color: #dde8f8 !important;
    font-size: 13px !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

/* ── Win/Loss badge colours inside tables ── */
.badge-win  { color: #34d399; font-weight: 600; }
.badge-loss { color: #f87171; font-weight: 600; }

/* ── Mobile responsive tweaks ── */
@media (max-width: 768px) {
    .block-container { padding: 1rem 0.5rem 3rem 0.5rem !important; }
    .dash-title { font-size: 20px; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 22px !important; }
    .stTabs [data-baseweb="tab"] { padding: 0 10px; font-size: 12px; }
    [data-testid="stDataFrameResizable"] tbody td { font-size: 11px !important; }
}

/* ── Divider ── */
hr {
    border: none;
    border-top: 1px solid rgba(77,143,255,0.1);
    margin: 1.25rem 0;
}

/* ── Vertical spacing util ── */
.gap { margin-top: 18px; }
</style>
""", unsafe_allow_html=True)

# =========================
# LOAD DATA FROM GITHUB
# =========================
BASE_URL = "https://raw.githubusercontent.com/andrewrust04-blip/mlb-betting-model/main/"

@st.cache_data(ttl=300)
def load_csv(file):
    try:
        return pd.read_csv(BASE_URL + file)
    except Exception:
        return pd.DataFrame()

bet_log       = load_csv("bet_log.csv")
filtered_bets = load_csv("filtered_bets.csv")
summary       = load_csv("dashboard_summary.csv")
by_line       = load_csv("dashboard_by_line.csv")
by_edge       = load_csv("dashboard_by_edge.csv")
by_side       = load_csv("dashboard_by_side.csv")

# =========================
# COLUMNS
# =========================
DISPLAY_COLS_TODAY = [
    "pitcher_name", "team", "opponent", "frame_away",
    "bet_side", "line", "odds", "model_prob", "implied_prob",
    "edge", "predicted_mean", "recommended_units", "kelly_units",
]
DISPLAY_COLS_LOG = [
    "date", "pitcher_name", "team", "opponent",
    "bet_side", "line", "odds", "edge",
    "predicted_mean", "actual_strikeouts",
    "bet_result", "profit_units",
]
COL_LABELS = {
    "pitcher_name": "Pitcher",
    "team": "Team",
    "opponent": "Opp",
    "frame_away": "H/A",
    "bet_side": "Side",
    "line": "Line",
    "odds": "Odds",
    "model_prob": "Model%",
    "implied_prob": "Impl%",
    "edge": "Edge",
    "predicted_mean": "Pred K",
    "simulated_mean": "Sim K",
    "recommended_units": "Rec U",
    "kelly_units": "Kelly U",
    "date": "Date",
    "actual_strikeouts": "Act K",
    "bet_result": "Result",
    "profit_units": "P/L (u)",
}

def safe_cols(df, cols):
    return [c for c in cols if c in df.columns]

# =========================
# HEADER
# =========================
today_str = pd.Timestamp.now().strftime("%b %d, %Y")
n_today   = len(filtered_bets) if not filtered_bets.empty else 0

st.markdown(f"""
<div class="dash-header">
  <div class="dash-title">⚾ MLB <span>Strikeout</span> Dashboard</div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
    <div class="dash-pill">📅 {today_str}</div>
    <div class="dash-pill">🎯 {n_today} bets today</div>
  </div>
</div>
""", unsafe_allow_html=True)

# =========================
# TABS
# =========================
tab1, tab2 = st.tabs(["📊  Dashboard", "📋  Bet Log"])

# ── Plotly shared layout ──
PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(6,15,40,0.6)",
    font=dict(family="IBM Plex Mono", color="#5a7099"),
    margin=dict(l=0, r=0, t=8, b=0),
    xaxis=dict(
        showgrid=False,
        tickfont=dict(size=10, color="#3a5280"),
        linecolor="rgba(77,143,255,0.15)",
        tickformat="%b %d",
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="rgba(77,143,255,0.08)",
        tickfont=dict(size=10, color="#3a5280"),
        tickformat="+.1f",
        ticksuffix="u",
        zeroline=True,
        zerolinecolor="rgba(77,143,255,0.25)",
        zerolinewidth=1,
    ),
    hoverlabel=dict(
        bgcolor="#0a1940",
        bordercolor="rgba(77,143,255,0.4)",
        font=dict(color="#ccdaff", size=12, family="IBM Plex Mono"),
    ),
)

# ===================================================
# TAB 1 — DASHBOARD
# ===================================================
with tab1:

    # ── Season metrics ──
    if not summary.empty:
        st.markdown('<div class="section-label">Season Performance</div>', unsafe_allow_html=True)
        n_metrics = min(len(summary), 6)
        metric_cols = st.columns(n_metrics)
        for i, row in summary.iterrows():
            if i < len(metric_cols):
                metric_cols[i].metric(
                    label=str(row.get("metric", "")),
                    value=str(row.get("value", "")),
                )
        st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

    # ── Today's bets ──
    st.markdown('<div class="section-label">Today\'s Bets</div>', unsafe_allow_html=True)

    if not filtered_bets.empty:
        display = filtered_bets[safe_cols(filtered_bets, DISPLAY_COLS_TODAY)].copy()

        col_cfg = {}

        if "edge" in display.columns:
            display["edge"] = pd.to_numeric(display["edge"], errors="coerce")
            col_cfg["edge"] = st.column_config.ProgressColumn(
                "Edge", format="%.1f%%", min_value=0, max_value=0.25
            )
        if "model_prob" in display.columns:
            display["model_prob"] = pd.to_numeric(display["model_prob"], errors="coerce")
            col_cfg["model_prob"] = st.column_config.NumberColumn("Model%", format="%.1f%%")
        if "implied_prob" in display.columns:
            display["implied_prob"] = pd.to_numeric(display["implied_prob"], errors="coerce")
            col_cfg["implied_prob"] = st.column_config.NumberColumn("Impl%", format="%.1f%%")
        if "odds" in display.columns:
            col_cfg["odds"] = st.column_config.NumberColumn("Odds", format="%d")
        if "line" in display.columns:
            col_cfg["line"] = st.column_config.NumberColumn("Line", format="%.1f")
        if "predicted_mean" in display.columns:
            col_cfg["predicted_mean"] = st.column_config.NumberColumn("Pred K", format="%.2f")
        if "recommended_units" in display.columns:
            col_cfg["recommended_units"] = st.column_config.NumberColumn("Rec U", format="%.1f")
        if "kelly_units" in display.columns:
            col_cfg["kelly_units"] = st.column_config.NumberColumn("Kelly U", format="%.1f")
        if "bet_side" in display.columns:
            col_cfg["bet_side"] = st.column_config.TextColumn("Side")

        display = display.rename(columns=COL_LABELS)
        col_cfg_renamed = {COL_LABELS.get(k, k): v for k, v in col_cfg.items()}

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg_renamed,
            height=min(40 * len(display) + 52, 520),
        )
    else:
        st.markdown(
            '<div style="color:#7a9cc4;font-size:14px;padding:16px 0;font-style:italic;">No bets scheduled for today.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

    # ── Cumulative profit chart ──
    if not bet_log.empty and "profit_units" in bet_log.columns:
        st.markdown('<div class="section-label">Cumulative Profit (units)</div>', unsafe_allow_html=True)

        plot_df = bet_log.copy()
        if "date" in plot_df.columns:
            plot_df["date"] = pd.to_datetime(plot_df["date"], errors="coerce")
            plot_df = plot_df.sort_values("date")
        plot_df["profit_units"] = pd.to_numeric(plot_df["profit_units"], errors="coerce").fillna(0)
        plot_df["cum_profit"]   = plot_df["profit_units"].cumsum()

        x_vals       = plot_df["date"] if "date" in plot_df.columns else plot_df.index
        final_profit = plot_df["cum_profit"].iloc[-1] if len(plot_df) > 0 else 0
        line_color   = "#4d8fff" if final_profit >= 0 else "#f87171"
        fill_color   = "rgba(77,143,255,0.1)" if final_profit >= 0 else "rgba(248,113,113,0.1)"

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=plot_df["cum_profit"],
            mode="lines+markers",
            line=dict(color=line_color, width=2.5),
            marker=dict(size=5, color=line_color, line=dict(width=1.5, color="#0a1940")),
            fill="tozeroy",
            fillcolor=fill_color,
            hovertemplate="<b>%{x|%b %d}</b><br>%{y:+.2f}u<extra></extra>",
        ))
        layout = {**PLOT_LAYOUT, "height": 260}
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

    # ── Performance breakdown ──
    st.markdown('<div class="section-label">Performance Breakdown</div>', unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)

    def render_breakdown_table(df, label):
        if df.empty:
            st.markdown(f'<div style="color:#7a9cc4;font-size:13px;font-style:italic;">{label}: no data yet.</div>', unsafe_allow_html=True)
            return
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        col_cfg = {}
        for c in numeric_cols:
            lc = c.lower()
            if "profit" in lc or "unit" in lc or "roi" in lc:
                col_cfg[c] = st.column_config.NumberColumn(c.replace("_", " ").title(), format="%+.2f")
            elif "prob" in lc or "rate" in lc or "pct" in lc:
                col_cfg[c] = st.column_config.NumberColumn(c.replace("_", " ").title(), format="%.1f%%")
            else:
                col_cfg[c] = st.column_config.NumberColumn(c.replace("_", " ").title(), format="%.2f")
        st.dataframe(
            df, use_container_width=True, hide_index=True,
            column_config=col_cfg,
            height=min(40 * len(df) + 52, 300),
        )

    with col_a:
        st.markdown('<div style="font-size:11px;color:#8fafd4;font-weight:600;margin-bottom:8px;letter-spacing:0.05em;">BY LINE</div>', unsafe_allow_html=True)
        render_breakdown_table(by_line, "By Line")
    with col_b:
        st.markdown('<div style="font-size:11px;color:#8fafd4;font-weight:600;margin-bottom:8px;letter-spacing:0.05em;">BY EDGE BUCKET</div>', unsafe_allow_html=True)
        render_breakdown_table(by_edge, "By Edge")
    with col_c:
        st.markdown('<div style="font-size:11px;color:#8fafd4;font-weight:600;margin-bottom:8px;letter-spacing:0.05em;">OVER vs UNDER</div>', unsafe_allow_html=True)
        render_breakdown_table(by_side, "By Side")


# ===================================================
# TAB 2 — FULL BET LOG
# ===================================================
with tab2:

    if bet_log.empty:
        st.markdown('<div style="color:#7a9cc4;font-size:14px;font-style:italic;padding:16px 0;">No bet log data found.</div>', unsafe_allow_html=True)
    else:
        log = bet_log.copy()
        if "date" in log.columns:
            log["date"] = pd.to_datetime(log["date"], errors="coerce")
        if "profit_units" in log.columns:
            log["profit_units"] = pd.to_numeric(log["profit_units"], errors="coerce")
        if "edge" in log.columns:
            log["edge"] = pd.to_numeric(log["edge"], errors="coerce")

        # ── Filters ──
        st.markdown('<div class="section-label">Filters</div>', unsafe_allow_html=True)
        f1, f2, f3, f4 = st.columns([1, 1, 1, 1])

        with f1:
            sides = ["All"] + sorted(log["bet_side"].dropna().unique().tolist()) if "bet_side" in log.columns else ["All"]
            sel_side = st.selectbox("Side", sides)
        with f2:
            results = ["All"] + sorted(log["bet_result"].dropna().unique().tolist()) if "bet_result" in log.columns else ["All"]
            sel_result = st.selectbox("Result", results)
        with f3:
            pitchers = ["All"] + sorted(log["pitcher_name"].dropna().unique().tolist()) if "pitcher_name" in log.columns else ["All"]
            sel_pitcher = st.selectbox("Pitcher", pitchers)
        with f4:
            if "date" in log.columns:
                min_d = log["date"].min()
                max_d = log["date"].max()
                if pd.notna(min_d) and pd.notna(max_d):
                    date_range = st.date_input("Date Range", value=(min_d.date(), max_d.date()))
                else:
                    date_range = None
            else:
                date_range = None

        # Apply filters
        filtered_log = log.copy()
        if sel_side != "All" and "bet_side" in filtered_log.columns:
            filtered_log = filtered_log[filtered_log["bet_side"] == sel_side]
        if sel_result != "All" and "bet_result" in filtered_log.columns:
            filtered_log = filtered_log[filtered_log["bet_result"] == sel_result]
        if sel_pitcher != "All" and "pitcher_name" in filtered_log.columns:
            filtered_log = filtered_log[filtered_log["pitcher_name"] == sel_pitcher]
        if date_range and len(date_range) == 2 and "date" in filtered_log.columns:
            d0, d1 = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
            filtered_log = filtered_log[(filtered_log["date"] >= d0) & (filtered_log["date"] <= d1)]
        if "date" in filtered_log.columns:
            filtered_log = filtered_log.sort_values("date", ascending=False)

        st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

        # ── Summary strip ──
        n_bets   = len(filtered_log)
        n_wins   = (filtered_log["bet_result"] == "win").sum()  if "bet_result" in filtered_log.columns else 0
        n_losses = (filtered_log["bet_result"] == "loss").sum() if "bet_result" in filtered_log.columns else 0
        win_rate = n_wins / n_bets * 100 if n_bets > 0 else 0
        total_pl = filtered_log["profit_units"].sum() if "profit_units" in filtered_log.columns else 0
        avg_edge = filtered_log["edge"].mean() * 100  if "edge"  in filtered_log.columns else 0

        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Bets",      f"{n_bets}")
        s2.metric("Record",    f"{n_wins}–{n_losses}")
        s3.metric("Win Rate",  f"{win_rate:.1f}%",
                  delta=f"{win_rate-50:.1f}% vs 50%",
                  delta_color="normal")
        s4.metric("Total P/L", f"{total_pl:+.2f}u",
                  delta_color="normal")
        s5.metric("Avg Edge",  f"{avg_edge:.1f}%")

        st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

        # ── Bet history table ──
        st.markdown('<div class="section-label">Bet History</div>', unsafe_allow_html=True)

        display_log = filtered_log[safe_cols(filtered_log, DISPLAY_COLS_LOG)].copy()
        log_col_cfg = {}

        if "edge" in display_log.columns:
            log_col_cfg["edge"] = st.column_config.ProgressColumn(
                "Edge", format="%.1f%%", min_value=0, max_value=0.25
            )
        if "profit_units" in display_log.columns:
            log_col_cfg["profit_units"] = st.column_config.NumberColumn("P/L (u)", format="%+.2f")
        if "odds" in display_log.columns:
            log_col_cfg["odds"] = st.column_config.NumberColumn("Odds", format="%d")
        if "line" in display_log.columns:
            log_col_cfg["line"] = st.column_config.NumberColumn("Line", format="%.1f")
        if "predicted_mean" in display_log.columns:
            log_col_cfg["predicted_mean"] = st.column_config.NumberColumn("Pred K", format="%.2f")
        if "actual_strikeouts" in display_log.columns:
            log_col_cfg["actual_strikeouts"] = st.column_config.NumberColumn("Act K", format="%d")
        if "date" in display_log.columns:
            log_col_cfg["date"] = st.column_config.DateColumn("Date", format="MMM D, YYYY")

        display_log = display_log.rename(columns=COL_LABELS)
        log_col_cfg_renamed = {COL_LABELS.get(k, k): v for k, v in log_col_cfg.items()}

        st.dataframe(
            display_log,
            use_container_width=True,
            hide_index=True,
            column_config=log_col_cfg_renamed,
            height=min(40 * len(display_log) + 52, 680),
        )

        # ── P/L chart (filtered) ──
        if "profit_units" in filtered_log.columns and len(filtered_log) > 1:
            st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-label">P/L Over Time (filtered view)</div>', unsafe_allow_html=True)

            chart_df = filtered_log.sort_values("date") if "date" in filtered_log.columns else filtered_log
            chart_df = chart_df.copy()
            chart_df["cum"] = chart_df["profit_units"].cumsum()
            x_vals = chart_df["date"] if "date" in chart_df.columns else chart_df.index
            clr    = "#4d8fff" if chart_df["cum"].iloc[-1] >= 0 else "#f87171"
            fill   = "rgba(77,143,255,0.1)" if chart_df["cum"].iloc[-1] >= 0 else "rgba(248,113,113,0.1)"

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=x_vals, y=chart_df["cum"],
                mode="lines+markers",
                line=dict(color=clr, width=2.5),
                marker=dict(size=5, color=clr, line=dict(width=1.5, color="#0a1940")),
                fill="tozeroy", fillcolor=fill,
                hovertemplate="<b>%{x|%b %d}</b><br>%{y:+.2f}u<extra></extra>",
            ))
            layout2 = {**PLOT_LAYOUT, "height": 220}
            fig2.update_layout(**layout2)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
