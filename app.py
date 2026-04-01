import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="MLB Strikeout Dashboard",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg:        #f0f2f5;
    --surface:   #ffffff;
    --surface2:  #f7f8fa;
    --border:    #e2e5eb;
    --border2:   #d0d5de;
    --text-1:    #0f1923;
    --text-2:    #3d4a5c;
    --text-3:    #7a8799;
    --text-4:    #b0bac8;
    --accent:    #1a56db;
    --accent-2:  #3b82f6;
    --accent-bg: rgba(26,86,219,0.07);
    --green:     #059669;
    --red:       #dc2626;
    --shadow-sm: 0 1px 3px rgba(15,25,35,0.07), 0 1px 2px rgba(15,25,35,0.04);
    --shadow-md: 0 4px 12px rgba(15,25,35,0.08), 0 2px 4px rgba(15,25,35,0.04);
    --shadow-lg: 0 8px 24px rgba(15,25,35,0.10), 0 4px 8px rgba(15,25,35,0.05);
    --radius:    12px;
    --radius-sm: 8px;
}

html, body, [class*="css"] { font-family: 'Sora', sans-serif !important; color: var(--text-1); }
#MainMenu, footer, header { visibility: hidden; }

.stApp {
    background: var(--bg);
    background-image:
        radial-gradient(ellipse 100% 50% at 60% -20%, rgba(59,130,246,0.06) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 0% 80%, rgba(5,150,105,0.04) 0%, transparent 50%);
}
.block-container { padding: 2rem 1.5rem 4rem 1.5rem !important; max-width: 1280px !important; }

/* HEADER */
.dash-header { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; margin-bottom:28px; }
.dash-brand  { display:flex; align-items:center; gap:14px; }
.dash-icon   { width:44px; height:44px; background:linear-gradient(135deg,#1a56db 0%,#3b82f6 100%); border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:22px; box-shadow:0 4px 12px rgba(26,86,219,0.3); }
.dash-title  { font-size:clamp(18px,3vw,26px); font-weight:800; color:var(--text-1); letter-spacing:-0.04em; line-height:1; }
.dash-title em { font-style:normal; background:linear-gradient(135deg,#1a56db,#3b82f6); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }
.dash-subtitle { font-size:12px; color:var(--text-3); font-weight:400; margin-top:3px; }
.dash-pills { display:flex; gap:8px; flex-wrap:wrap; }
.pill { font-family:'JetBrains Mono',monospace; font-size:11px; font-weight:500; padding:6px 14px; border-radius:20px; border:1px solid var(--border); background:var(--surface); color:var(--text-2); box-shadow:var(--shadow-sm); white-space:nowrap; }
.pill-accent { background:var(--accent-bg); border-color:rgba(26,86,219,0.2); color:var(--accent); }

/* TABS */
.stTabs [data-baseweb="tab-list"] { gap:0; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:4px; margin-bottom:24px; box-shadow:var(--shadow-sm); width:fit-content; }
.stTabs [data-baseweb="tab"] { height:34px; padding:0 20px; font-size:13px; font-weight:600; color:var(--text-3); background:transparent; border:none; border-radius:var(--radius-sm); letter-spacing:-0.01em; font-family:'Sora',sans-serif !important; }
.stTabs [aria-selected="true"] { color:var(--text-1) !important; background:var(--bg) !important; box-shadow:var(--shadow-sm) !important; }
.stTabs [data-baseweb="tab-highlight"] { display:none; }
.stTabs [data-baseweb="tab-panel"] { padding:0; }

/* METRIC CARDS */
[data-testid="metric-container"] { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:18px 20px 16px; box-shadow:var(--shadow-sm); transition:box-shadow 0.2s,border-color 0.2s; position:relative; overflow:hidden; }
[data-testid="metric-container"]:hover { box-shadow:var(--shadow-md); border-color:var(--border2); }
[data-testid="metric-container"]::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; background:linear-gradient(90deg,#1a56db,#3b82f6,transparent); }
[data-testid="metric-container"] label { color:var(--text-3) !important; font-size:10px !important; font-weight:700 !important; letter-spacing:0.12em !important; text-transform:uppercase !important; font-family:'Sora',sans-serif !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { font-size:clamp(20px,2.5vw,28px) !important; font-weight:700 !important; color:var(--text-1) !important; font-family:'JetBrains Mono',monospace !important; letter-spacing:-0.02em !important; line-height:1.15 !important; }
[data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size:11px !important; font-family:'JetBrains Mono',monospace !important; }

/* SECTION HEADERS */
.sec-head { display:flex; align-items:center; gap:10px; margin:0 0 12px 0; }
.sec-head-label { font-size:10px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:var(--text-3); white-space:nowrap; }
.sec-head-line  { flex:1; height:1px; background:var(--border); }

/* DATAFRAME */
.stDataFrame { border:1px solid var(--border) !important; border-radius:var(--radius) !important; overflow:hidden !important; box-shadow:var(--shadow-sm) !important; }
[data-testid="stDataFrameResizable"] { border-radius:var(--radius); }
[data-testid="stDataFrameResizable"] thead th { background:var(--surface2) !important; color:var(--text-3) !important; font-size:10px !important; font-weight:700 !important; letter-spacing:0.1em !important; text-transform:uppercase !important; border-bottom:1px solid var(--border) !important; font-family:'Sora',sans-serif !important; }
[data-testid="stDataFrameResizable"] tbody tr { border-bottom:1px solid var(--border) !important; }
[data-testid="stDataFrameResizable"] tbody tr:hover td { background:var(--accent-bg) !important; }
[data-testid="stDataFrameResizable"] tbody td { color:var(--text-1) !important; font-size:13px !important; font-family:'JetBrains Mono',monospace !important; background:var(--surface) !important; }
/* Force Edge progress bars blue */
[data-testid="stDataFrameResizable"] [role="progressbar"] > div { background: var(--accent) !important; }
[data-testid="stDataFrameResizable"] [role="progressbar"] { background: rgba(26,86,219,0.12) !important; border-radius: 4px !important; }


/* SELECTBOX */
.stSelectbox label, .stMultiSelect label, .stDateInput label { font-size:10px !important; font-weight:700 !important; color:var(--text-3) !important; text-transform:uppercase !important; letter-spacing:0.12em !important; font-family:'Sora',sans-serif !important; }
[data-baseweb="select"] > div { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:var(--radius-sm) !important; color:var(--text-1) !important; font-size:13px !important; font-family:'Sora',sans-serif !important; box-shadow:var(--shadow-sm) !important; }
[data-baseweb="select"] > div:hover { border-color:var(--border2) !important; }
[data-baseweb="popover"] { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:var(--radius) !important; box-shadow:var(--shadow-lg) !important; }
[data-baseweb="menu"] { background:var(--surface) !important; }
[data-baseweb="option"] { color:var(--text-1) !important; background:var(--surface) !important; font-size:13px !important; font-family:'Sora',sans-serif !important; }
[data-baseweb="option"]:hover { background:var(--accent-bg) !important; color:var(--accent) !important; }

/* DATE INPUT */
[data-baseweb="input"] { background:var(--surface) !important; border:1px solid var(--border) !important; border-radius:var(--radius-sm) !important; box-shadow:var(--shadow-sm) !important; }
[data-baseweb="input"] input { color:var(--text-1) !important; font-size:13px !important; font-family:'JetBrains Mono',monospace !important; }

/* MOBILE */
@media (max-width: 768px) {
    .block-container { padding:1rem 0.75rem 3rem !important; }
    .dash-title { font-size:18px; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] { font-size:20px !important; }
    .stTabs [data-baseweb="tab"] { padding:0 12px; font-size:12px; }
    [data-testid="stDataFrameResizable"] tbody td { font-size:11px !important; }
}

.gap-sm { margin-top:12px; }
.gap    { margin-top:20px; }
.gap-lg { margin-top:28px; }
.empty-state { color:var(--text-4); font-size:13px; padding:20px 0; font-style:italic; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════
# DATA
# ═══════════════════════════════════════
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

DISPLAY_COLS_TODAY = ["pitcher_name","team","opponent","frame_away","bet_side","line","odds","model_prob","implied_prob","edge","predicted_mean","recommended_units","kelly_units"]
DISPLAY_COLS_LOG   = ["date","pitcher_name","team","opponent","bet_side","line","odds","edge","predicted_mean","actual_strikeouts","bet_result","profit_units"]
COL_LABELS = {
    "pitcher_name":"Pitcher","team":"Team","opponent":"Opp","frame_away":"H/A",
    "bet_side":"Side","line":"Line","odds":"Odds","model_prob":"Model%",
    "implied_prob":"Impl%","edge":"Edge","predicted_mean":"Pred K",
    "simulated_mean":"Sim K","recommended_units":"Rec U","kelly_units":"Kelly U",
    "date":"Date","actual_strikeouts":"Act K","bet_result":"Result","profit_units":"P/L (u)",
}

def safe_cols(df, cols):
    return [c for c in cols if c in df.columns]

def smart_round(val, metric_name=""):
    """Round raw metric values to clean display strings."""
    s = str(val).strip()
    try:
        f = float(s.replace("%","").replace("+",""))
        lc = metric_name.lower()
        # Already formatted with %
        if "%" in s:
            return f"{f:.1f}%"
        # Win rate / probability fields stored as 0-1 raw
        is_rate = any(x in lc for x in ["rate","prob","pct"])
        if is_rate and 0 <= abs(f) <= 1:
            return f"{f:.1%}"
        # Large counts
        if abs(f) >= 1000:
            return f"{f:,.0f}"
        # Clean integers (total_bets=29.0)
        if f == int(f) and abs(f) < 10000:
            return f"{int(f)}"
        # Profit fields — 2dp with sign and 'u'
        if any(x in lc for x in ["profit","unit"]):
            return f"{f:+.2f}u"
        # Everything else — 2dp
        return f"{f:.2f}"
    except Exception:
        return s

# ═══════════════════════════════════════
# PLOTLY THEME
# ═══════════════════════════════════════
PLOT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#f7f8fa",
    font=dict(family="JetBrains Mono", color="#7a8799", size=11),
    margin=dict(l=4, r=4, t=12, b=4),
    xaxis=dict(showgrid=False, tickfont=dict(size=10,color="#7a8799"), linecolor="#e2e5eb", tickformat="%b %d", zeroline=False),
    yaxis=dict(showgrid=True, gridcolor="#e8eaee", tickfont=dict(size=10,color="#7a8799"), tickformat="+.1f", ticksuffix="u", zeroline=True, zerolinecolor="#d0d5de", zerolinewidth=1.5),
    hoverlabel=dict(bgcolor="#0f1923", bordercolor="#1a56db", font=dict(color="#ffffff",size=12,family="JetBrains Mono")),
)

def profit_chart(df, height=260):
    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")
    df["profit_units"] = pd.to_numeric(df["profit_units"], errors="coerce").fillna(0)
    df["cum"] = df["profit_units"].cumsum()
    x = list(df["date"] if "date" in df.columns else df.index)
    y = list(df["cum"])

    if not y:
        fig = go.Figure()
        fig.update_layout(**{**PLOT_BASE, "height": height})
        return fig

    # Build a dense list of (x, y) including interpolated zero-crossing points
    pts_x, pts_y = [x[0]], [y[0]]
    for i in range(1, len(y)):
        if (y[i-1] >= 0) != (y[i] >= 0):
            # Interpolate zero crossing
            frac = y[i-1] / (y[i-1] - y[i])
            xc = x[i-1] + (x[i] - x[i-1]) * frac
            pts_x.append(xc)
            pts_y.append(0.0)
        pts_x.append(x[i])
        pts_y.append(y[i])

    # Split into contiguous same-sign segments
    fig = go.Figure()
    seg_x, seg_y = [pts_x[0]], [pts_y[0]]
    for i in range(1, len(pts_y)):
        seg_x.append(pts_x[i])
        seg_y.append(pts_y[i])
        # End segment at a zero-crossing point (pts_y[i] == 0 and next changes sign)
        at_cross = (pts_y[i] == 0.0 and i < len(pts_y) - 1 and
                    ((pts_y[i-1] >= 0) != (pts_y[i+1] >= 0)))
        if at_cross or i == len(pts_y) - 1:
            is_pos = pts_y[i-1] >= 0 if len(seg_y) > 1 else pts_y[i] >= 0
            clr  = "#16a34a" if is_pos else "#dc2626"
            fill = "rgba(22,163,74,0.09)" if is_pos else "rgba(220,38,38,0.09)"
            fig.add_trace(go.Scatter(
                x=seg_x, y=seg_y,
                mode="lines+markers",
                line=dict(color=clr, width=2.5, shape="linear"),
                marker=dict(size=4, color=clr, line=dict(width=1.5, color="#ffffff")),
                fill="tozeroy", fillcolor=fill,
                showlegend=False,
                hovertemplate="<b>%{x|%b %d}</b><br>%{y:+.2f}u<extra></extra>",
            ))
            seg_x, seg_y = [pts_x[i]], [pts_y[i]]

    fig.update_layout(**{**PLOT_BASE, "height": height})
    return fig

# ═══════════════════════════════════════
# HEADER
# ═══════════════════════════════════════
today_str = pd.Timestamp.now().strftime("%b %d, %Y")
n_today   = len(filtered_bets) if not filtered_bets.empty else 0

st.markdown(f"""
<div class="dash-header">
  <div class="dash-brand">
    <div class="dash-icon">⚾</div>
    <div>
      <div class="dash-title">MLB <em>Strikeout</em> Dashboard</div>
      <div class="dash-subtitle">Pitcher strikeout model · updated daily</div>
    </div>
  </div>
  <div class="dash-pills">
    <div class="pill">📅 {today_str}</div>
    <div class="pill pill-accent">🎯 {n_today} bets today</div>
  </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊  Dashboard", "📋  Bet Log"])

def sec(label):
    st.markdown(f'<div class="sec-head"><span class="sec-head-label">{label}</span><span class="sec-head-line"></span></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# TAB 1
# ═══════════════════════════════════════════════════════
with tab1:

    # Season metrics
    if not summary.empty:
        sec("Season Performance")
        n_m = min(len(summary), 6)
        mc  = st.columns(n_m)
        for i, row in summary.iterrows():
            if i < len(mc):
                mname = str(row.get("metric",""))
                mc[i].metric(
                    label=mname.replace("_"," ").title(),
                    value=smart_round(row.get("value",""), mname),
                )
        st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

    # Today's bets
    sec("Today's Bets")
    if not filtered_bets.empty:
        d = filtered_bets[safe_cols(filtered_bets, DISPLAY_COLS_TODAY)].copy()
        cfg = {}
        for c in ["edge","model_prob","implied_prob","odds","line","predicted_mean","recommended_units","kelly_units"]:
            if c in d.columns: d[c] = pd.to_numeric(d[c], errors="coerce")
        if "edge"             in d.columns: cfg["edge"]             = st.column_config.ProgressColumn("Edge", format="%.1f%%", min_value=0, max_value=0.25)
        if "model_prob"       in d.columns: cfg["model_prob"]       = st.column_config.NumberColumn("Model%", format="%.1f%%")
        if "implied_prob"     in d.columns: cfg["implied_prob"]     = st.column_config.NumberColumn("Impl%", format="%.1f%%")
        if "odds"             in d.columns: cfg["odds"]             = st.column_config.NumberColumn("Odds", format="%d")
        if "line"             in d.columns: cfg["line"]             = st.column_config.NumberColumn("Line", format="%.1f")
        if "predicted_mean"   in d.columns: cfg["predicted_mean"]   = st.column_config.NumberColumn("Pred K", format="%.2f")
        if "recommended_units"in d.columns: cfg["recommended_units"]= st.column_config.NumberColumn("Rec U", format="%.1f")
        if "kelly_units"      in d.columns: cfg["kelly_units"]      = st.column_config.NumberColumn("Kelly U", format="%.1f")
        d   = d.rename(columns=COL_LABELS)
        cfg = {COL_LABELS.get(k,k):v for k,v in cfg.items()}
        st.dataframe(d, use_container_width=True, hide_index=True, column_config=cfg, height=min(42*len(d)+54,540))
    else:
        st.markdown('<div class="empty-state">No bets scheduled for today.</div>', unsafe_allow_html=True)

    st.markdown('<div class="gap-lg"></div>', unsafe_allow_html=True)

    # Profit chart
    if not bet_log.empty and "profit_units" in bet_log.columns:
        sec("Cumulative Profit (units)")
        st.plotly_chart(profit_chart(bet_log.copy()), use_container_width=True, config={"displayModeBar":False})
        st.markdown('<div class="gap-lg"></div>', unsafe_allow_html=True)

    # Performance breakdown
    sec("Performance Breakdown")

    def render_breakdown(df, label):
        if df.empty:
            st.markdown(f'<div class="empty-state">{label}: no data yet.</div>', unsafe_allow_html=True)
            return
        cfg = {}
        for c in df.select_dtypes(include="number").columns:
            lc = c.lower()
            fmt = "%+.2f" if any(x in lc for x in ["profit","unit","roi"]) else "%.2f"
            cfg[c] = st.column_config.NumberColumn(c.replace("_"," ").title(), format=fmt)
        st.dataframe(df, use_container_width=True, hide_index=True, column_config=cfg, height=min(42*len(df)+54,300))

    ca, cb, cc = st.columns(3)
    with ca:
        st.markdown('<p style="font-size:10px;font-weight:700;color:var(--text-3);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">By Line</p>', unsafe_allow_html=True)
        render_breakdown(by_line, "By Line")
    with cb:
        st.markdown('<p style="font-size:10px;font-weight:700;color:var(--text-3);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">By Edge Bucket</p>', unsafe_allow_html=True)
        render_breakdown(by_edge, "By Edge")
    with cc:
        st.markdown('<p style="font-size:10px;font-weight:700;color:var(--text-3);text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">Over vs Under</p>', unsafe_allow_html=True)
        render_breakdown(by_side, "By Side")


# ═══════════════════════════════════════════════════════
# TAB 2
# ═══════════════════════════════════════════════════════
with tab2:

    if bet_log.empty:
        st.markdown('<div class="empty-state">No bet log data found.</div>', unsafe_allow_html=True)
    else:
        log = bet_log.copy()
        if "date"         in log.columns: log["date"]         = pd.to_datetime(log["date"], errors="coerce")
        if "profit_units" in log.columns: log["profit_units"] = pd.to_numeric(log["profit_units"], errors="coerce")
        if "edge"         in log.columns: log["edge"]         = pd.to_numeric(log["edge"], errors="coerce")

        sec("Filters")
        f1,f2,f3,f4 = st.columns(4)
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
            date_range = None
            if "date" in log.columns:
                mn, mx = log["date"].min(), log["date"].max()
                if pd.notna(mn) and pd.notna(mx):
                    date_range = st.date_input("Date Range", value=(mn.date(), mx.date()))

        fl = log.copy()
        if sel_side    != "All" and "bet_side"     in fl.columns: fl = fl[fl["bet_side"]     == sel_side]
        if sel_result  != "All" and "bet_result"   in fl.columns: fl = fl[fl["bet_result"]   == sel_result]
        if sel_pitcher != "All" and "pitcher_name" in fl.columns: fl = fl[fl["pitcher_name"] == sel_pitcher]
        if date_range and len(date_range) == 2 and "date" in fl.columns:
            fl = fl[(fl["date"] >= pd.Timestamp(date_range[0])) & (fl["date"] <= pd.Timestamp(date_range[1]))]
        if "date" in fl.columns:
            fl = fl.sort_values("date", ascending=False)

        st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
        sec("Summary")

        n_bets   = len(fl)
        n_wins   = int((fl["bet_result"]=="win").sum())  if "bet_result" in fl.columns else 0
        n_losses = int((fl["bet_result"]=="loss").sum()) if "bet_result" in fl.columns else 0
        n_settled = n_wins + n_losses
        win_rate = n_wins/n_settled*100 if n_settled > 0 else 0
        total_pl = fl["profit_units"].sum() if "profit_units" in fl.columns else 0
        avg_edge = fl["edge"].mean()*100    if "edge"         in fl.columns else 0

        s1,s2,s3,s4,s5 = st.columns(5)
        s1.metric("Bets",      f"{n_bets}")
        s2.metric("Record",    f"{n_wins}–{n_losses}")
        s3.metric("Win Rate",  f"{win_rate:.1f}%")
        s4.metric("Total P/L", f"{total_pl:+.2f}u")
        s5.metric("Avg Edge",  f"{avg_edge:.1f}%")

        st.markdown('<div class="gap-lg"></div>', unsafe_allow_html=True)
        sec("Bet History")

        dl = fl[safe_cols(fl, DISPLAY_COLS_LOG)].copy()
        # Replace "None" strings with dashes for cleaner display
        for col in ["actual_strikeouts","bet_result","profit_units"]:
            if col in dl.columns:
                dl[col] = dl[col].replace("None", "—").replace(float("nan"), "—")
                dl[col] = dl[col].where(dl[col].notna(), "—")
        # Numeric conversions
        for nc in ["edge","profit_units","odds","line","predicted_mean"]:
            if nc in dl.columns:
                dl[nc] = pd.to_numeric(dl[nc], errors="coerce")
        lcfg = {}
        if "edge"             in dl.columns: lcfg["edge"]             = st.column_config.ProgressColumn("Edge", format="%.1f%%", min_value=0, max_value=0.25)
        if "profit_units"     in dl.columns: lcfg["profit_units"]     = st.column_config.NumberColumn("P/L (u)", format="%+.2f")
        if "odds"             in dl.columns: lcfg["odds"]             = st.column_config.NumberColumn("Odds", format="%d")
        if "line"             in dl.columns: lcfg["line"]             = st.column_config.NumberColumn("Line", format="%.1f")
        if "predicted_mean"   in dl.columns: lcfg["predicted_mean"]   = st.column_config.NumberColumn("Pred K", format="%.2f")
        if "actual_strikeouts"in dl.columns: lcfg["actual_strikeouts"]= st.column_config.NumberColumn("Act K", format="%d")
        if "date"             in dl.columns: lcfg["date"]             = st.column_config.DateColumn("Date", format="MMM D, YYYY")
        dl   = dl.rename(columns=COL_LABELS)
        lcfg = {COL_LABELS.get(k,k):v for k,v in lcfg.items()}
        st.dataframe(dl, use_container_width=True, hide_index=True, column_config=lcfg, height=min(42*len(dl)+54,680))

        if "profit_units" in fl.columns and len(fl) > 1:
            st.markdown('<div class="gap-lg"></div>', unsafe_allow_html=True)
            sec("P/L Over Time (filtered)")
            st.plotly_chart(profit_chart(fl.copy(), height=220), use_container_width=True, config={"displayModeBar":False})
