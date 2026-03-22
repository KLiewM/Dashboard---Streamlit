"""
Crude Oil Price Dashboard
--------------------------
Bloomberg-style terminal interface for crude oil futures.
Reads from Excel (crude clean sheet) — Brent, WTI, Dubai M1-M12.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import datetime

# ─── Page config ───────────────────────────────────────────────────────────
st.set_page_config(page_title="Crude Oil Terminal", layout="wide", page_icon="")

# ─── Color constants ──────────────────────────────────────────────────────
BG       = "#0B0E14"
BG_CARD  = "#111520"
BG_SIDE  = "#0D1017"
BORDER   = "#1C2333"
AMBER    = "#FF8C00"
TEXT     = "#D1D5DB"
TEXT_DIM = "#6B7280"
GREEN    = "#00C853"
RED      = "#FF3D3D"
WHITE    = "#F0F0F0"

# ─── Bloomberg-style CSS ──────────────────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

    .stApp {{ background-color: {BG}; }}
    .block-container {{ padding-top: 0.8rem; padding-bottom: 0; max-width: 100%; }}
    h1, h2, h3 {{ color: {WHITE}; font-family: 'IBM Plex Sans', sans-serif; font-weight: 600; letter-spacing: -0.02em; }}
    h1 {{ font-size: 1.3rem !important; }}
    h2 {{ font-size: 1.1rem !important; margin-bottom: 0.3rem !important; }}
    h3 {{ font-size: 0.95rem !important; color: {TEXT_DIM}; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em; }}
    p, span, label, div {{ color: {TEXT}; font-family: 'IBM Plex Sans', sans-serif; }}
    hr {{ border-color: {BORDER} !important; margin: 0.5rem 0 !important; }}

    [data-testid="stSidebar"] {{ background-color: {BG_SIDE}; border-right: 1px solid {BORDER}; }}
    [data-testid="stSidebar"] * {{ color: {TEXT} !important; font-family: 'IBM Plex Sans', sans-serif; }}
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stCheckbox label,
    [data-testid="stSidebar"] .stRadio label {{
        font-size: 0.78rem !important; text-transform: uppercase;
        letter-spacing: 0.06em; color: {TEXT_DIM} !important;
    }}

    .stSelectbox > div > div, .stMultiSelect > div > div {{
        background-color: {BG_CARD} !important; border: 1px solid {BORDER} !important; color: {TEXT} !important;
    }}

    .stMetric {{ background: {BG_CARD}; padding: 8px 12px; border-radius: 4px; border: 1px solid {BORDER}; }}
    div[data-testid="stMetricValue"] {{
        color: {AMBER} !important; font-size: 1.05rem !important;
        font-family: 'JetBrains Mono', monospace !important; font-weight: 600 !important;
    }}
    div[data-testid="stMetricLabel"] {{
        color: {TEXT_DIM} !important; font-size: 0.72rem !important;
        text-transform: uppercase; letter-spacing: 0.08em;
    }}

    .stTabs [data-baseweb="tab-list"] {{ background-color: transparent; border-bottom: 1px solid {BORDER}; }}
    .stTabs [data-baseweb="tab"] {{
        color: {TEXT_DIM} !important; font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.82rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.06em;
    }}
    .stTabs [aria-selected="true"] {{ color: {AMBER} !important; border-bottom-color: {AMBER} !important; }}

    .stDataFrame {{ border: 1px solid {BORDER}; border-radius: 4px; }}
    .stCaption, [data-testid="stCaptionContainer"] {{ color: {TEXT_DIM} !important; font-size: 0.72rem !important; }}
    .stAlert {{ background-color: {BG_CARD} !important; border: 1px solid {BORDER} !important; color: {TEXT} !important; }}

    .tenor-strip {{
        display: flex; gap: 2px; padding: 0; margin: 4px 0 8px 0;
        font-family: 'JetBrains Mono', monospace;
    }}
    .tenor-cell {{
        flex: 1; background: {BG_CARD}; border: 1px solid {BORDER};
        padding: 6px 4px; text-align: center; min-width: 0;
    }}
    .tenor-cell:first-child {{ border-radius: 4px 0 0 4px; }}
    .tenor-cell:last-child  {{ border-radius: 0 4px 4px 0; }}
    .tenor-cell .t-label {{ font-size: 0.6rem; color: {TEXT_DIM}; font-weight: 600; letter-spacing: 0.1em; }}
    .tenor-cell .t-price {{ font-size: 0.82rem; color: {WHITE}; font-weight: 600; margin: 1px 0; }}
    .tenor-cell .t-chg   {{ font-size: 0.65rem; font-weight: 500; }}
    .t-up   {{ color: {GREEN}; }}
    .t-down {{ color: {RED}; }}
    .t-flat {{ color: {TEXT_DIM}; }}
    .tenor-cell .t-na {{ font-size: 0.75rem; color: {BORDER}; }}

    .header-bar {{
        display: flex; align-items: baseline; gap: 16px;
        padding: 0 0 4px 0; border-bottom: 2px solid {AMBER}; margin-bottom: 6px;
    }}
    .header-bar .h-product {{
        font-family: 'IBM Plex Sans', sans-serif; font-size: 1.15rem;
        font-weight: 700; color: {AMBER}; letter-spacing: -0.01em;
    }}
    .header-bar .h-date {{
        font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;
        color: {TEXT_DIM}; font-weight: 400;
    }}
    .section-div {{
        font-family: 'IBM Plex Sans', sans-serif; font-size: 0.75rem;
        color: {TEXT_DIM}; text-transform: uppercase; letter-spacing: 0.1em;
        font-weight: 600; padding: 12px 0 4px 0;
        border-bottom: 1px solid {BORDER}; margin-bottom: 8px;
    }}

    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    header {{ visibility: hidden; }}
</style>
""", unsafe_allow_html=True)

# ─── Load data ─────────────────────────────────────────────────────────────
DATA_FILE = Path(__file__).parent / "pricescrossbarrel_-_Crude_ONLY.xlsx"

PRODUCT_MAP = {
    "Brent":  "ICE BRENT CRUDE",
    "WTI":    "NYMEX WTI CRUDE",
    "Dubai":  "ICE DUBAI CRUDE",
}
PRODUCTS = list(PRODUCT_MAP.keys())
TENORS = [f"M{i}" for i in range(1, 13)]


@st.cache_data(ttl=3600)
def load_data(path: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="crude clean", header=None, skiprows=1)
    headers = raw.iloc[0].tolist()
    raw = raw.iloc[1:].reset_index(drop=True)
    raw.columns = headers
    raw["Date"] = pd.to_datetime(raw["Date"], errors="coerce")
    raw = raw.dropna(subset=["Date"]).reset_index(drop=True)

    df = pd.DataFrame({"Date": raw["Date"]})
    for short, prefix in PRODUCT_MAP.items():
        for t in TENORS:
            src = f"{prefix} {t}"
            dst = f"{short}|{t}"
            if src in raw.columns:
                vals = pd.to_numeric(raw[src], errors="coerce")
                vals = vals.replace(0, np.nan)
                df[dst] = vals

    price_cols = [c for c in df.columns if c != "Date"]
    df = df.dropna(subset=price_cols, how="all").reset_index(drop=True)
    return df


if not DATA_FILE.exists():
    st.error(f"Data file not found at `{DATA_FILE}`.")
    st.stop()

df = load_data(str(DATA_FILE))

columns = [c for c in df.columns if c != "Date"]
products = sorted(set(c.split("|")[0] for c in columns))
tenors_map = {}
for c in columns:
    prod, tenor = c.split("|")
    tenors_map.setdefault(prod, []).append(tenor)

# ─── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<div style="font-family:IBM Plex Sans,sans-serif; font-size:1.1rem; '
        f'font-weight:700; color:{AMBER}; letter-spacing:0.02em; padding:8px 0 4px 0;">'
        f'CRUDE OIL TERMINAL</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div style="font-size:0.68rem; color:{TEXT_DIM}; margin-bottom:12px;">'
                f'METS Analytics</div>', unsafe_allow_html=True)
    st.markdown("---")

    view_mode = st.radio("VIEW", [
        "Price History", "Seasonality", "Time Spreads", "Inter-Crude Spreads", "Calendar",
    ])
    st.markdown("---")

    if view_mode != "Calendar":
        selected_product = st.selectbox("PRODUCT", products)
        available_tenors = tenors_map.get(selected_product, TENORS)

        if view_mode == "Price History":
            selected_tenors = st.multiselect("TENORS", available_tenors, default=["M1", "M2"])
        elif view_mode == "Seasonality":
            selected_tenor_season = st.selectbox("TENOR", available_tenors, index=0)
            current_year = df["Date"].dt.year.max()
            all_years = sorted(df["Date"].dt.year.unique(), reverse=True)
            selected_years = st.multiselect("COMPARE YEARS", all_years, default=all_years[:5])
            show_range = st.checkbox("5-Year Min/Max Range", value=True)
            show_avg = st.checkbox("5-Year Average", value=True)
        elif view_mode == "Time Spreads":
            spread_tenors = [t for t in available_tenors if t.startswith("M")]
            c1, c2 = st.columns(2)
            with c1: front_tenor = st.selectbox("FRONT", spread_tenors, index=0)
            with c2: back_tenor = st.selectbox("BACK", spread_tenors, index=min(1, len(spread_tenors)-1))
        elif view_mode == "Inter-Crude Spreads":
            crude_a = st.selectbox("CRUDE A", products, index=0)
            crude_b = st.selectbox("CRUDE B", [p for p in products if p != crude_a], index=0)
            spread_tenor = st.selectbox("TENOR", TENORS, index=0)

    st.markdown("---")
    st.caption("Source: crude clean sheet")

# ─── Plotly styling ───────────────────────────────────────────────────────
CHART_COLORS = [AMBER, "#5B9CF6", GREEN, RED, "#A78BFA", "#F472B6",
                "#38BDF8", "#FBBF24", "#6EE7B7", "#94A3B8"]

MONTH_TICKS  = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


def style_fig(fig, title="", height=520):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=BG_CARD,
        title=dict(text=title.upper() if title else "",
                   font=dict(family="IBM Plex Sans", size=13, color=TEXT_DIM), x=0.01, y=0.97),
        legend=dict(bgcolor="rgba(0,0,0,0)",
                    font=dict(family="JetBrains Mono", size=10, color=TEXT),
                    orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        height=height,
        margin=dict(l=55, r=20, t=45, b=40),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=BG_CARD, font=dict(family="JetBrains Mono", size=11, color=WHITE),
                        bordercolor=BORDER),
        xaxis=dict(gridcolor="#1C2333", showgrid=True, gridwidth=1, zeroline=False,
                   linecolor=BORDER,
                   tickfont=dict(family="JetBrains Mono", size=10, color=TEXT_DIM)),
        yaxis=dict(gridcolor="#1C2333", showgrid=True, gridwidth=1, zeroline=False,
                   linecolor=BORDER, side="right",
                   title=dict(text="$/bbl", font=dict(family="IBM Plex Sans", size=10, color=TEXT_DIM)),
                   tickformat=",.1f",
                   tickfont=dict(family="JetBrains Mono", size=10, color=TEXT_DIM)),
    )
    return fig


def hex_to_rgba(hx, a):
    h = hx.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


# ─── Header + Tenor Strip ────────────────────────────────────────────────
if view_mode != "Calendar":
    latest = df.iloc[-1]
    prev   = df.iloc[-2]
    last_date = df["Date"].iloc[-1].strftime("%d %b %Y")

    st.markdown(
        f'<div class="header-bar">'
        f'<span class="h-product">{selected_product.upper()}</span>'
        f'<span class="h-date">Last: {last_date}</span>'
        f'</div>', unsafe_allow_html=True)

    cells = ""
    for t in TENORS:
        cn = f"{selected_product}|{t}"
        if cn in df.columns and pd.notna(latest[cn]):
            val = latest[cn]
            chg = val - prev[cn] if pd.notna(prev.get(cn)) else 0
            if abs(chg) < 0.005:
                cls, s = "t-flat", "UNCH"
            elif chg > 0:
                cls, s = "t-up", f"+{chg:.2f}"
            else:
                cls, s = "t-down", f"{chg:.2f}"
            cells += (f'<div class="tenor-cell"><div class="t-label">{t}</div>'
                      f'<div class="t-price">{val:,.2f}</div>'
                      f'<div class="t-chg {cls}">{s}</div></div>')
        else:
            cells += (f'<div class="tenor-cell"><div class="t-label">{t}</div>'
                      f'<div class="t-na">--</div></div>')
    st.markdown(f'<div class="tenor-strip">{cells}</div>', unsafe_allow_html=True)

# ═══ PRICE HISTORY ════════════════════════════════════════════════════════
if view_mode == "Price History":
    if not selected_tenors:
        st.warning("Select at least one tenor.")
        st.stop()

    fig = go.Figure()
    for i, tenor in enumerate(selected_tenors):
        col = f"{selected_product}|{tenor}"
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df["Date"], y=df[col], name=tenor,
                                     line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=1.5)))
    style_fig(fig, f"{selected_product} Price History")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-div">Forward Curve — Latest</div>', unsafe_allow_html=True)
    curve_vals = [latest[f"{selected_product}|{t}"]
                  if f"{selected_product}|{t}" in df.columns else np.nan for t in TENORS]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=TENORS, y=curve_vals, mode="lines+markers",
                              line=dict(color=AMBER, width=2),
                              marker=dict(size=6, color=AMBER, symbol="diamond"),
                              fill="tozeroy", fillcolor=hex_to_rgba(AMBER, 0.06)))
    style_fig(fig2, "", height=300)
    st.plotly_chart(fig2, use_container_width=True)

# ═══ SEASONALITY ══════════════════════════════════════════════════════════
elif view_mode == "Seasonality":
    col_name = f"{selected_product}|{selected_tenor_season}"
    if col_name not in df.columns:
        st.error(f"Column {col_name} not found.")
        st.stop()

    sub = df[["Date", col_name]].dropna(subset=[col_name]).copy()
    sub["Year"] = sub["Date"].dt.year
    sub["DayOfYear"] = sub["Date"].dt.dayofyear

    fig = go.Figure()
    range_years = sorted(sub["Year"].unique())[-5:]
    range_df = sub[sub["Year"].isin(range_years)]

    if show_range and len(range_years) >= 2:
        agg = range_df.groupby("DayOfYear")[col_name].agg(["min","max"]).reset_index()
        full_days = pd.DataFrame({"DayOfYear": range(1, 366)})
        agg = full_days.merge(agg, on="DayOfYear", how="left")
        agg["min"] = agg["min"].interpolate("linear").bfill().ffill()
        agg["max"] = agg["max"].interpolate("linear").bfill().ffill()
        x = agg["DayOfYear"].tolist()
        fig.add_trace(go.Scatter(
            x=x + x[::-1], y=agg["max"].tolist() + agg["min"].tolist()[::-1],
            fill="toself", fillcolor="rgba(255,140,0,0.06)",
            line=dict(color="rgba(0,0,0,0)"), connectgaps=True,
            name=f"{range_years[0]}-{range_years[-1]} Range", hoverinfo="skip"))

    if show_avg and len(range_years) >= 2:
        avg = range_df.groupby("DayOfYear")[col_name].mean().reset_index()
        full_days = pd.DataFrame({"DayOfYear": range(1, 366)})
        avg = full_days.merge(avg, on="DayOfYear", how="left")
        avg[col_name] = avg[col_name].interpolate("linear").bfill().ffill()
        fig.add_trace(go.Scatter(x=avg["DayOfYear"], y=avg[col_name], name="5Y Avg",
                                 line=dict(color=TEXT_DIM, width=1.5, dash="dot"), connectgaps=True))

    for i, year in enumerate(sorted(selected_years)):
        yr = sub[sub["Year"] == year].sort_values("DayOfYear")
        fig.add_trace(go.Scatter(
            x=yr["DayOfYear"], y=yr[col_name], name=str(year),
            line=dict(color=CHART_COLORS[i % len(CHART_COLORS)],
                      width=2.5 if year == current_year else 1.2),
            opacity=1.0 if year == current_year else 0.7))

    style_fig(fig, f"{selected_product} {selected_tenor_season} Seasonality")
    fig.update_layout(xaxis=dict(tickvals=MONTH_TICKS, ticktext=MONTH_LABELS, range=[1,365], title=""))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-div">Monthly Averages</div>', unsafe_allow_html=True)
    sub["Month"] = sub["Date"].dt.month
    pivot = sub.pivot_table(values=col_name, index="Year", columns="Month", aggfunc="mean")
    pivot.columns = [pd.Timestamp(2000, m, 1).strftime("%b") for m in pivot.columns]
    pivot = pivot.round(2)
    st.dataframe(pivot.loc[pivot.index.isin(selected_years)] if selected_years else pivot,
                 use_container_width=True)

# ═══ TIME SPREADS ═════════════════════════════════════════════════════════
elif view_mode == "Time Spreads":
    front_col = f"{selected_product}|{front_tenor}"
    back_col  = f"{selected_product}|{back_tenor}"
    if front_col not in df.columns or back_col not in df.columns:
        st.error("Selected tenors not available.")
        st.stop()

    spread = df[front_col] - df[back_col]
    spread_name = f"{selected_product} {front_tenor}-{back_tenor}"

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.6,0.4], vertical_spacing=0.04)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[front_col], name=front_tenor,
                             line=dict(color=AMBER, width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[back_col], name=back_tenor,
                             line=dict(color="#5B9CF6", width=1.5)), row=1, col=1)
    fig.add_trace(go.Bar(x=df["Date"], y=spread, name="Spread",
                         marker_color=[GREEN if v >= 0 else RED for v in spread], opacity=0.8),
                  row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color=TEXT_DIM, opacity=0.4, row=2, col=1)
    style_fig(fig, f"{spread_name} Spread", height=600)
    fig.update_yaxes(title_text="$/bbl", row=1, col=1)
    fig.update_yaxes(title_text="Spread", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-div">Spread Seasonality</div>', unsafe_allow_html=True)
    sp = pd.DataFrame({"Date": df["Date"], "Spread": spread}).dropna(subset=["Spread"])
    sp["Year"], sp["DayOfYear"] = sp["Date"].dt.year, sp["Date"].dt.dayofyear
    fig3 = go.Figure()
    for i, year in enumerate(sorted(sp["Year"].unique())[-5:]):
        yr = sp[sp["Year"] == year].sort_values("Date")
        fig3.add_trace(go.Scatter(x=yr["DayOfYear"], y=yr["Spread"], name=str(year),
                                  line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=1.3)))
    style_fig(fig3, f"{spread_name} Spread Seasonality", height=360)
    fig3.update_layout(xaxis=dict(tickvals=MONTH_TICKS, ticktext=MONTH_LABELS, range=[1,365]))
    st.plotly_chart(fig3, use_container_width=True)

# ═══ INTER-CRUDE SPREADS ═════════════════════════════════════════════════
elif view_mode == "Inter-Crude Spreads":
    col_a = f"{crude_a}|{spread_tenor}"
    col_b = f"{crude_b}|{spread_tenor}"
    if col_a not in df.columns or col_b not in df.columns:
        st.error(f"Columns not found: {col_a} or {col_b}")
        st.stop()

    crack = df[col_a] - df[col_b]
    crack_name = f"{crude_a} vs {crude_b} ({spread_tenor})"

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.55,0.45], vertical_spacing=0.04)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[col_a], name=crude_a,
                             line=dict(color=AMBER, width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[col_b], name=crude_b,
                             line=dict(color="#5B9CF6", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=crack, name="Spread",
                             line=dict(color=GREEN, width=1.5),
                             fill="tozeroy", fillcolor=hex_to_rgba(GREEN, 0.06)), row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color=TEXT_DIM, opacity=0.4, row=2, col=1)
    style_fig(fig, f"Inter-Crude: {crack_name}", height=600)
    fig.update_yaxes(title_text="$/bbl", row=1, col=1)
    fig.update_yaxes(title_text="Spread", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-div">Spread Seasonality</div>', unsafe_allow_html=True)
    ck = pd.DataFrame({"Date": df["Date"], "Spread": crack}).dropna(subset=["Spread"])
    ck["Year"], ck["DayOfYear"] = ck["Date"].dt.year, ck["Date"].dt.dayofyear

    fig4 = go.Figure()
    years = sorted(ck["Year"].unique())[-5:]
    for i, year in enumerate(years):
        yr = ck[ck["Year"] == year].sort_values("Date")
        fig4.add_trace(go.Scatter(x=yr["DayOfYear"], y=yr["Spread"], name=str(year),
                                  line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=1.3)))

    rng = ck[ck["Year"].isin(years)]
    rng["DayOfYear"] = rng["Date"].dt.dayofyear
    agg = rng.groupby("DayOfYear")["Spread"].agg(["min","max"]).reset_index()
    full_days = pd.DataFrame({"DayOfYear": range(1,366)})
    agg = full_days.merge(agg, on="DayOfYear", how="left")
    agg["min"] = agg["min"].interpolate("linear").bfill().ffill()
    agg["max"] = agg["max"].interpolate("linear").bfill().ffill()
    x = agg["DayOfYear"].tolist()
    fig4.add_trace(go.Scatter(
        x=x + x[::-1], y=agg["max"].tolist() + agg["min"].tolist()[::-1],
        fill="toself", fillcolor="rgba(255,140,0,0.06)",
        line=dict(color="rgba(0,0,0,0)"), connectgaps=True,
        name=f"{years[0]}-{years[-1]} Range", hoverinfo="skip"))
    style_fig(fig4, f"Spread Seasonality: {crack_name}", height=380)
    fig4.update_layout(xaxis=dict(tickvals=MONTH_TICKS, ticktext=MONTH_LABELS, range=[1,365]))
    st.plotly_chart(fig4, use_container_width=True)

# ═══ CALENDAR ═════════════════════════════════════════════════════════════
elif view_mode == "Calendar":
    st.markdown(
        f'<div class="header-bar"><span class="h-product">MARKET CALENDAR</span></div>',
        unsafe_allow_html=True)

    econ_tab, geo_tab = st.tabs(["ECONOMIC CALENDAR", "GEOPOLITICAL MONITOR"])

    with econ_tab:
        st.markdown('<div class="section-div">Upcoming Events</div>', unsafe_allow_html=True)
        st.caption("High-impact events: US, EU, China, Japan")

        if "te_api_key" not in st.session_state:
            st.session_state["te_api_key"] = ""
        with st.expander("API Key Configuration", expanded=not bool(st.session_state["te_api_key"])):
            key_input = st.text_input("Trading Economics API Key",
                                      value=st.session_state["te_api_key"], type="password",
                                      help="tradingeconomics.com/api — leave blank for guest demo.")
            if key_input != st.session_state["te_api_key"]:
                st.session_state["te_api_key"] = key_input
                st.rerun()

        api_key = st.session_state["te_api_key"] or "guest:guest"
        c1, c2, c3 = st.columns(3)
        with c1: horizon = st.selectbox("HORIZON", ["Today","Next 7 Days","Next 14 Days","Next Month"], index=1, key="cal_h")
        with c2: importance_filter = st.multiselect("IMPORTANCE", ["High (3)","Medium (2)","Low (1)"],
                                                     default=["High (3)","Medium (2)"], key="cal_i")
        with c3: country_filter = st.multiselect("TERRITORY", ["United States","Euro Area","China","Japan"],
                                                  default=["United States","Euro Area","China","Japan"], key="cal_c")

        COUNTRY_API_MAP = {"United States":["united states"],"Euro Area":["euro area","germany","france"],
                           "China":["china"],"Japan":["japan"]}
        API_TO_TERRITORY = {}
        for t, al in COUNTRY_API_MAP.items():
            for a in al: API_TO_TERRITORY[a.lower()] = t
        IMPORTANCE_INT   = {"High (3)":3,"Medium (2)":2,"Low (1)":1}
        IMPORTANCE_LABEL = {3:"HIGH",2:"MED",1:"LOW"}
        TERRITORY_SHORT  = {"United States":"US","Euro Area":"EU","China":"CN","Japan":"JP"}

        today = datetime.date.today()
        delta_map = {"Today":0,"Next 7 Days":7,"Next 14 Days":14,"Next Month":30}
        end_date = today + datetime.timedelta(days=delta_map[horizon])
        sel_imp = [IMPORTANCE_INT[i] for i in importance_filter]

        @st.cache_data(ttl=900, show_spinner=False)
        def fetch_te(ck, d1, d2, k):
            import requests, urllib.parse
            url = (f"https://api.tradingeconomics.com/calendar/country/"
                   f"{urllib.parse.quote(ck)}/{d1}/{d2}?c={k}")
            try:
                r = requests.get(url, timeout=10); r.raise_for_status(); return r.json()
            except Exception as e: return {"error": str(e)}

        ac = []
        for t in country_filter:
            for a in COUNTRY_API_MAP.get(t,[t.lower()]):
                if a not in ac: ac.append(a)

        if not country_filter:
            st.warning("Select at least one territory.")
        else:
            with st.spinner("Fetching..."):
                raw = fetch_te(",".join(ac), today.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), api_key)
            if isinstance(raw, dict) and "error" in raw:
                st.error(f"API error: {raw['error']}"); st.stop()
            if not raw:
                st.info("No events for selected period.")
            else:
                rows = []
                for ev in raw:
                    imp = int(ev.get("Importance") or 1)
                    if imp not in sel_imp: continue
                    ac2 = (ev.get("Country") or "").strip()
                    tl = API_TO_TERRITORY.get(ac2.lower())
                    if tl is None or tl not in country_filter: continue
                    rd = ev.get("Date","")
                    try:
                        dt = datetime.datetime.fromisoformat(rd)
                        ds, ts = dt.strftime("%d %b"), dt.strftime("%H:%M")
                    except: ds, ts = rd[:10], ""
                    rows.append({"Date":ds,"Time":ts,"Region":TERRITORY_SHORT.get(tl,tl),
                                 "Event":ev.get("Event",""),"Impact":IMPORTANCE_LABEL[imp],
                                 "Prev":ev.get("Previous") or "-",
                                 "Fcst":ev.get("Forecast") or ev.get("TEForecast") or "-",
                                 "Actual":ev.get("Actual") or "-"})
                if not rows: st.info("No events match filters.")
                else:
                    cdf = pd.DataFrame(rows)
                    def hl(v):
                        if v=="HIGH": return f"color:{RED};font-weight:600"
                        if v=="MED":  return f"color:{AMBER};font-weight:600"
                        return f"color:{GREEN}"
                    st.dataframe(cdf.style.map(hl, subset=["Impact"]),
                                 use_container_width=True, hide_index=True)
                    st.caption(f"{len(rows)} events | Trading Economics | UTC")

            st.markdown("---")
            st.markdown(
                f'<div style="font-size:0.75rem;color:{TEXT_DIM};line-height:1.6;">'
                '<b>Key drivers:</b> '
                'US: Fed decisions, NFP (USD inverse to oil). '
                'CN: PMI, industrial output (demand). '
                'EU: ECB rates (refinery margins). '
                'JP: BoJ policy (carry-trade unwinds).</div>', unsafe_allow_html=True)

    with geo_tab:
        st.markdown('<div class="section-div">Geopolitical Risk Monitor</div>', unsafe_allow_html=True)
        st.caption("Ongoing situations with direct oil supply or shipping implications.")
        st.info("Coming soon.")

# ─── Footer ────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="text-align:center;padding:16px 0 8px 0;font-size:0.65rem;'
    f'color:{BORDER};font-family:JetBrains Mono,monospace;letter-spacing:0.1em;">'
    f'CRUDE OIL TERMINAL  |  METS ANALYTICS</div>', unsafe_allow_html=True)
