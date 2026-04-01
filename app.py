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
# CUSTOM CSS
# =========================
st.markdown("""
<style>
    /* Global font and background */
    html, body, [class*="css"] {
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Import DM Sans */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

    /* Hide default streamlit chrome */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Page background */
    .stApp {
        background-color: #0d0f12;
    }

    /* Main block container padding */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1px solid #1e2229;
        background: transparent;
        margin-bottom: 1.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        padding: 0 20px;
        font-size: 13px;
        font-weight: 500;
        color: #6b7280;
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        border-radius: 0;
        letter-spacing: 0.02em;
    }
    .stTabs [aria-selected="true"] {
        color: #e5e7eb !important;
        background: transparent !important;
        border-bottom: 2px solid #22c55e !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding: 0;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #131519;
        border: 1px solid #1e2229;
        border-radius: 10px;
        padding: 16px 20px;
    }
    [data-testid="metric-container"] label {
        color: #6b7280 !important;
        font-size: 11px !important;
        font-weight: 500 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 26px !important;
        font-weight: 600 !important;
        color: #e5e7eb !important;
        font-family: 'DM Mono', monospace !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-size: 12px !important;
    }

    /* Dataframe styling */
    .stDataFrame {
        border: 1px solid #1e2229 !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    [data-testid="stDataFrameResizable"] {
        border-radius: 10px;
    }

    /* Section headers */
    .section-header {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #4b5563;
        margin: 0 0 14px 2px;
    }

    /* Page title */
    .page-title {
        font-size: 24px;
        font-weight: 600;
        color: #f9fafb;
        letter-spacing: -0.02em;
        margin-bottom: 4px;
    }
    .page-subtitle {
        font-size: 13px;
        color: #4b5563;
        margin-bottom: 2rem;
    }

    /* Filter row */
    .stSelectbox label, .stMultiSelect label {
        font-size: 11px !important;
        font-weight: 500 !important;
        color: #6b7280 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.07em !important;
    }
    [data-baseweb="select"] {
        background: #131519 !important;
        border-color: #1e2229 !important;
    }
    [data-baseweb="select"] * {
        background: #131519 !important;
        color: #d1d5db !important;
    }

    /* Divider */
    hr {
        border: none;
        border-top: 1px solid #1e2229;
        margin: 1.5rem 0;
    }

    /* Pill badges rendered via markdown */
    .badge-over {
        background: #052e16; color: #4ade80;
        padding: 2px 8px; border-radius: 20px;
        font-size: 11px; font-weight: 600;
        font-family: 'DM Mono', monospace;
    }
    .badge-under {
        background: #1c1917; color: #f59e0b;
        padding: 2px 8px; border-radius: 20px;
        font-size: 11px; font-weight: 600;
        font-family: 'DM Mono', monospace;
    }
    .badge-win {
        background: #052e16; color: #4ade80;
        padding: 2px 8px; border-radius: 20px;
        font-size: 11px; font-weight: 600;
    }
    .badge-loss {
        background: #2d0a0a; color: #f87171;
        padding: 2px 8px; border-radius: 20px;
        font-size: 11px; font-weight: 600;
    }
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

bet_log      = load_csv("bet_log.csv")
filtered_bets = load_csv("filtered_bets.csv")
summary      = load_csv("dashboard_summary.csv")
by_line      = load_csv("dashboard_by_line.csv")
by_edge      = load_csv("dashboard_by_edge.csv")
by_side      = load_csv("dashboard_by_side.csv")

# =========================
# HELPER: DISPLAY COLS
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

def fmt_pct(val):
    try:
        return f"{float(val)*100:.1f}%"
    except Exception:
        return val

def fmt_edge(val):
    try:
        return f"{float(val)*100:.1f}%"
    except Exception:
        return val

# =========================
# PAGE HEADER
# =========================
st.markdown('<div class="page-title">⚾ MLB Strikeout Dashboard</div>', unsafe_allow_html=True)

today_str = pd.Timestamp.now().strftime("%B %d, %Y")
n_today = len(filtered_bets) if not filtered_bets.empty else 0
st.markdown(f'<div class="page-subtitle">{today_str} &nbsp;·&nbsp; {n_today} bets today</div>', unsafe_allow_html=True)

# =========================
# TABS
# =========================
tab1, tab2 = st.tabs(["📊  Dashboard", "📋  Full Bet Log"])

# ===================================================
# TAB 1 — DASHBOARD
# ===================================================
with tab1:

    # ---- SUMMARY METRICS ----
    if not summary.empty:
        st.markdown('<div class="section-header">Season Performance</div>', unsafe_allow_html=True)
        metric_cols = st.columns(min(len(summary), 6))
        for i, row in summary.iterrows():
            if i < len(metric_cols):
                metric_cols[i].metric(label=str(row.get("metric", "")), value=str(row.get("value", "")))
        st.markdown("<br>", unsafe_allow_html=True)

    # ---- TODAY'S BETS ----
    st.markdown('<div class="section-header">Today\'s Bets</div>', unsafe_allow_html=True)
    if not filtered_bets.empty:
        display = filtered_bets[safe_cols(filtered_bets, DISPLAY_COLS_TODAY)].copy()

        col_cfg = {}

        if "edge" in display.columns:
            display["edge"] = pd.to_numeric(display["edge"], errors="coerce")
            col_cfg["edge"] = st.column_config.ProgressColumn(
                "Edge",
                format="%.1f%%",
                min_value=0,
                max_value=0.25,
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
            height=min(38 * len(display) + 48, 500),
        )
    else:
        st.markdown(
            '<div style="color:#4b5563;font-size:14px;padding:16px 0;">No bets scheduled for today.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- PROFIT CHART ----
    if not bet_log.empty and "profit_units" in bet_log.columns:
        st.markdown('<div class="section-header">Cumulative Profit (units)</div>', unsafe_allow_html=True)

        plot_df = bet_log.copy()
        if "date" in plot_df.columns:
            plot_df["date"] = pd.to_datetime(plot_df["date"], errors="coerce")
            plot_df = plot_df.sort_values("date")
        plot_df["profit_units"] = pd.to_numeric(plot_df["profit_units"], errors="coerce").fillna(0)
        plot_df["cum_profit"] = plot_df["profit_units"].cumsum()

        x_vals = plot_df["date"] if "date" in plot_df.columns else plot_df.index
        final_profit = plot_df["cum_profit"].iloc[-1] if len(plot_df) > 0 else 0
        line_color = "#22c55e" if final_profit >= 0 else "#f87171"
        fill_color = "rgba(34,197,94,0.08)" if final_profit >= 0 else "rgba(248,113,113,0.08)"

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=plot_df["cum_profit"],
            mode="lines+markers",
            line=dict(color=line_color, width=2),
            marker=dict(size=4, color=line_color),
            fill="tozeroy",
            fillcolor=fill_color,
            hovertemplate="<b>%{x|%b %d}</b><br>%{y:+.2f}u<extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#131519",
            height=260,
            margin=dict(l=0, r=0, t=8, b=0),
            xaxis=dict(
                showgrid=False,
                tickfont=dict(size=11, color="#4b5563"),
                linecolor="#1e2229",
                tickformat="%b %d",
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor="#1e2229",
                tickfont=dict(size=11, color="#4b5563"),
                tickformat="+.1f",
                ticksuffix="u",
                zeroline=True,
                zerolinecolor="#374151",
                zerolinewidth=1,
            ),
            hoverlabel=dict(
                bgcolor="#1e2229",
                bordercolor="#374151",
                font=dict(color="#e5e7eb", size=12),
            ),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown("<br>", unsafe_allow_html=True)

    # ---- PERFORMANCE BREAKDOWN ----
    st.markdown('<div class="section-header">Performance Breakdown</div>', unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns(3)

    def render_breakdown_table(df, title):
        if df.empty:
            st.markdown(f'<div style="color:#4b5563;font-size:13px;">{title}: no data yet.</div>', unsafe_allow_html=True)
            return
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        col_cfg = {}
        for c in numeric_cols:
            if "profit" in c.lower() or "unit" in c.lower() or "roi" in c.lower():
                col_cfg[c] = st.column_config.NumberColumn(c.replace("_", " ").title(), format="%+.2f")
            elif "prob" in c.lower() or "rate" in c.lower() or "pct" in c.lower():
                col_cfg[c] = st.column_config.NumberColumn(c.replace("_", " ").title(), format="%.1f%%")
            else:
                col_cfg[c] = st.column_config.NumberColumn(c.replace("_", " ").title(), format="%.2f")
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config=col_cfg,
            height=min(38 * len(df) + 48, 300),
        )

    with col_a:
        st.markdown('<div style="font-size:12px;color:#6b7280;font-weight:500;margin-bottom:8px;">By Line</div>', unsafe_allow_html=True)
        render_breakdown_table(by_line, "By Line")

    with col_b:
        st.markdown('<div style="font-size:12px;color:#6b7280;font-weight:500;margin-bottom:8px;">By Edge Bucket</div>', unsafe_allow_html=True)
        render_breakdown_table(by_edge, "By Edge")

    with col_c:
        st.markdown('<div style="font-size:12px;color:#6b7280;font-weight:500;margin-bottom:8px;">Over vs Under</div>', unsafe_allow_html=True)
        render_breakdown_table(by_side, "By Side")


# ===================================================
# TAB 2 — FULL BET LOG
# ===================================================
with tab2:

    if bet_log.empty:
        st.markdown('<div style="color:#4b5563;font-size:14px;padding:16px 0;">No bet log data found.</div>', unsafe_allow_html=True)
    else:
        log = bet_log.copy()

        # Parse date
        if "date" in log.columns:
            log["date"] = pd.to_datetime(log["date"], errors="coerce")

        if "profit_units" in log.columns:
            log["profit_units"] = pd.to_numeric(log["profit_units"], errors="coerce")

        if "edge" in log.columns:
            log["edge"] = pd.to_numeric(log["edge"], errors="coerce")

        # ---- FILTER ROW ----
        f1, f2, f3, f4 = st.columns([2, 2, 2, 2])

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
                    date_range = st.date_input("Date range", value=(min_d.date(), max_d.date()))
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

        filtered_log = filtered_log.sort_values("date", ascending=False) if "date" in filtered_log.columns else filtered_log

        st.markdown("<br>", unsafe_allow_html=True)

        # ---- LOG SUMMARY STRIP ----
        n_bets   = len(filtered_log)
        n_wins   = (filtered_log["bet_result"] == "win").sum() if "bet_result" in filtered_log.columns else 0
        n_losses = (filtered_log["bet_result"] == "loss").sum() if "bet_result" in filtered_log.columns else 0
        win_rate = n_wins / n_bets * 100 if n_bets > 0 else 0
        total_pl = filtered_log["profit_units"].sum() if "profit_units" in filtered_log.columns else 0
        avg_edge = filtered_log["edge"].mean() * 100 if "edge" in filtered_log.columns else 0

        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Bets", f"{n_bets}")
        s2.metric("Record", f"{n_wins}–{n_losses}")
        s3.metric("Win Rate", f"{win_rate:.1f}%")
        s4.metric("Total P/L", f"{total_pl:+.2f}u")
        s5.metric("Avg Edge", f"{avg_edge:.1f}%")

        st.markdown("<br>", unsafe_allow_html=True)

        # ---- LOG TABLE ----
        st.markdown('<div class="section-header">Bet history</div>', unsafe_allow_html=True)

        display_log = filtered_log[safe_cols(filtered_log, DISPLAY_COLS_LOG)].copy()

        log_col_cfg = {}

        if "edge" in display_log.columns:
            log_col_cfg["edge"] = st.column_config.ProgressColumn(
                "Edge", format="%.1f%%", min_value=0, max_value=0.25
            )

        if "profit_units" in display_log.columns:
            log_col_cfg["profit_units"] = st.column_config.NumberColumn(
                "P/L (u)", format="%+.2f"
            )

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
            height=min(38 * len(display_log) + 48, 650),
        )

        # ---- P/L CHART FOR FILTERED SELECTION ----
        if "profit_units" in filtered_log.columns and len(filtered_log) > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-header">P/L over time (filtered)</div>', unsafe_allow_html=True)

            chart_df = filtered_log.sort_values("date") if "date" in filtered_log.columns else filtered_log
            chart_df["cum"] = chart_df["profit_units"].cumsum()
            x_vals = chart_df["date"] if "date" in chart_df.columns else chart_df.index
            clr = "#22c55e" if chart_df["cum"].iloc[-1] >= 0 else "#f87171"
            fill = "rgba(34,197,94,0.08)" if chart_df["cum"].iloc[-1] >= 0 else "rgba(248,113,113,0.08)"

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=x_vals, y=chart_df["cum"],
                mode="lines+markers",
                line=dict(color=clr, width=2),
                marker=dict(size=4, color=clr),
                fill="tozeroy", fillcolor=fill,
                hovertemplate="<b>%{x|%b %d}</b><br>%{y:+.2f}u<extra></extra>",
            ))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#131519",
                height=220,
                margin=dict(l=0, r=0, t=8, b=0),
                xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#4b5563"), linecolor="#1e2229", tickformat="%b %d"),
                yaxis=dict(showgrid=True, gridcolor="#1e2229", tickfont=dict(size=11, color="#4b5563"), tickformat="+.1f", ticksuffix="u", zeroline=True, zerolinecolor="#374151"),
                hoverlabel=dict(bgcolor="#1e2229", bordercolor="#374151", font=dict(color="#e5e7eb", size=12)),
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
