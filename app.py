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

# ─── CSS + JS ─────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

    /* ── Base ── */
    .stApp {{ background-color: {BG}; }}
    .block-container {{ padding-top: 0.8rem; padding-bottom: 0; max-width: 100%; }}
    h1, h2, h3 {{ color: {WHITE}; font-family: 'IBM Plex Sans', sans-serif; font-weight: 600; letter-spacing: -0.02em; }}
    h1 {{ font-size: 1.3rem !important; }}
    h2 {{ font-size: 1.1rem !important; margin-bottom: 0.3rem !important; }}
    h3 {{ font-size: 0.95rem !important; color: {TEXT_DIM}; font-weight: 500; text-transform: uppercase; letter-spacing: 0.08em; }}
    p, span, label, div {{ color: {TEXT}; font-family: 'IBM Plex Sans', sans-serif; }}
    hr {{ border-color: {BORDER} !important; margin: 0.5rem 0 !important; }}

    /* ── HIDE the entire Streamlit header bar (contains keyboard_double_ text) ── */
    /* We keep [data-testid="collapsedControl"] accessible via JS by moving it off-screen */
    header[data-testid="stHeader"] {{
        display: none !important;
    }}
    /* The collapsedControl renders outside the header in some Streamlit versions — hide it visually */
    /* but keep it off-screen (NOT display:none) so JS .click() still works */
    [data-testid="collapsedControl"] {{
        position: fixed !important;
        top: -9999px !important;
        left: -9999px !important;
        opacity: 0 !important;
        pointer-events: none !important;
        z-index: -1 !important;
    }}
    /* Hide the in-sidebar close button — our custom button handles everything */
    [data-testid="stSidebarCollapseButton"] {{
        display: none !important;
    }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{ background-color: {BG_SIDE}; border-right: 1px solid {BORDER}; }}
    [data-testid="stSidebar"] * {{ color: {TEXT} !important; font-family: 'IBM Plex Sans', sans-serif; }}
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiSelect label,
    [data-testid="stSidebar"] .stCheckbox label,
    [data-testid="stSidebar"] .stRadio label {{
        font-size: 0.78rem !important; text-transform: uppercase;
        letter-spacing: 0.06em; color: {TEXT_DIM} !important;
    }}

    /* ── Inputs ── */
    .stSelectbox > div > div, .stMultiSelect > div > div {{
        background-color: {BG_CARD} !important; border: 1px solid {BORDER} !important; color: {TEXT} !important;
    }}

    /* ── Metrics ── */
    .stMetric {{ background: {BG_CARD}; padding: 8px 12px; border-radius: 4px; border: 1px solid {BORDER}; }}
    div[data-testid="stMetricValue"] {{
        color: {AMBER} !important; font-size: 1.05rem !important;
        font-family: 'JetBrains Mono', monospace !important; font-weight: 600 !important;
    }}
    div[data-testid="stMetricLabel"] {{
        color: {TEXT_DIM} !important; font-size: 0.72rem !important;
        text-transform: uppercase; letter-spacing: 0.08em;
    }}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {{ background-color: transparent; border-bottom: 1px solid {BORDER}; }}
    .stTabs [data-baseweb="tab"] {{
        color: {TEXT_DIM} !important; font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.82rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.06em;
    }}
    .stTabs [aria-selected="true"] {{ color: {AMBER} !important; border-bottom-color: {AMBER} !important; }}

    /* ── Misc ── */
    .stDataFrame {{ border: 1px solid {BORDER}; border-radius: 4px; }}
    .stCaption, [data-testid="stCaptionContainer"] {{ color: {TEXT_DIM} !important; font-size: 0.72rem !important; }}
    .stAlert {{ background-color: {BG_CARD} !important; border: 1px solid {BORDER} !important; color: {TEXT} !important; }}
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}

    /* ── Custom floating ▶ button (shown when sidebar is collapsed) ── */
    #cot-open-btn {{
        position: fixed;
        top: 50%;
        left: 0;
        transform: translateY(-50%);
        z-index: 999999;
        background: {BG_CARD};
        border: 1px solid {AMBER};
        border-left: none;
        border-radius: 0 6px 6px 0;
        padding: 14px 7px;
        cursor: pointer;
        display: none;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        box-shadow: 3px 0 16px rgba(255,140,0,0.18);
        transition: background 0.15s;
    }}
    #cot-open-btn:hover {{ background: {BORDER}; }}
    #cot-open-btn .cot-arrow {{
        color: {AMBER};
        font-size: 15px;
        line-height: 1;
        font-style: normal;
    }}
    #cot-open-btn .cot-label {{
        color: {AMBER};
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.58rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        writing-mode: vertical-rl;
        text-orientation: mixed;
    }}

    /* ── Tenor strip ── */
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

    /* ── Header bar ── */
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
</style>

<!-- Custom sidebar toggle button -->
<button id="cot-open-btn" onclick="cotOpen()" title="Open sidebar">
    <i class="cot-arrow">&#9654;</i>
    <span class="cot-label">Menu</span>
</button>

<script>
(function() {{
    /* Try clicking Streamlit's native (off-screen) collapsedControl button.
       Because it is NOT display:none — just opacity:0 + off-screen — JS .click() works. */
    function cotOpen() {{
        var btn = document.querySelector('[data-testid="collapsedControl"] button');
        if (btn) {{ btn.click(); return; }}
        /* Fallback: force sidebar open by removing the collapsed CSS class */
        var sb = document.querySelector('[data-testid="stSidebar"]');
        if (sb) sb.style.marginLeft = '0';
    }}

    function cotSync() {{
        var sb  = document.querySelector('[data-testid="stSidebar"]');
        var fab = document.getElementById('cot-open-btn');
        if (!fab) return;
        if (!sb) {{ fab.style.display = 'flex'; return; }}
        var w = sb.getBoundingClientRect().width;
        /* collapsed when sidebar width shrinks below ~50px */
        fab.style.display = (w < 50) ? 'flex' : 'none';
    }}

    /* Expose so onclick="" works */
    window.cotOpen = cotOpen;

    /* Poll until sidebar exists, then observe */
    var timer = setInterval(function() {{
        var sb = document.querySelector('[data-testid="stSidebar"]');
        if (!sb) return;
        clearInterval(timer);
        cotSync();
        /* Watch for width changes (Streamlit animates the sidebar) */
        var ro = new ResizeObserver(cotSync);
        ro.observe(sb);
        window.addEventListener('resize', cotSync);
    }}, 100);
}})();
</script>
""", unsafe_allow_html=True)

# ─── Load data ─────────────────────────────────────────────────────────────
DATA_FILE = Path(__file__).parent / "pricescrossbarrel_-_Crude_ONLY.xlsx"

PRODUCT_MAP = {
    "Brent":  "ICE BRENT CRUDE",
    "WTI":    "NYMEX WTI CRUDE",
    "Dubai":  "ICE DUBAI CRUDE",
}
PRODUCTS = list(PRODUCT_MAP.keys())
TENORS   = [f"M{i}" for i in range(1, 13)]


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
                vals = pd.to_numeric(raw[src], errors="coerce").replace(0, np.nan)
                df[dst] = vals

    price_cols = [c for c in df.columns if c != "Date"]
    df = df.dropna(subset=price_cols, how="all").reset_index(drop=True)
    return df


if not DATA_FILE.exists():
    st.error(f"Data file not found at `{DATA_FILE}`.")
    st.stop()

df = load_data(str(DATA_FILE))

columns   = [c for c in df.columns if c != "Date"]
products  = sorted(set(c.split("|")[0] for c in columns))
tenors_map = {}
for c in columns:
    prod, tenor = c.split("|")
    tenors_map.setdefault(prod, []).append(tenor)

# ─── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<div style="font-family:IBM Plex Sans,sans-serif;font-size:1.1rem;'
        f'font-weight:700;color:{AMBER};letter-spacing:0.02em;padding:8px 0 4px 0;">'
        f'CRUDE OIL TERMINAL</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:0.68rem;color:{TEXT_DIM};margin-bottom:12px;">'
        f'METS Analytics</div>', unsafe_allow_html=True)
    st.markdown("---")

    view_mode = st.radio("VIEW", [
        "Price History", "Seasonality", "Time Spreads", "Inter-Crude Spreads",
    ])
    st.markdown("---")

    selected_product  = st.selectbox("PRODUCT", products) if view_mode != "Inter-Crude Spreads" else None
    available_tenors  = tenors_map.get(selected_product, TENORS) if selected_product else TENORS

    if view_mode == "Price History":
        selected_tenors = st.multiselect("TENORS", available_tenors, default=["M1", "M2"])

    elif view_mode == "Seasonality":
        selected_tenor_season = st.selectbox("TENOR", available_tenors, index=0)
        current_year  = df["Date"].dt.year.max()
        all_years     = sorted(df["Date"].dt.year.unique(), reverse=True)
        selected_years = st.multiselect("COMPARE YEARS", all_years, default=all_years[:5])
        show_range    = st.checkbox("Min/Max Range", value=True)
        show_avg      = st.checkbox("Average of Selection", value=True)

    elif view_mode == "Time Spreads":
        spread_tenors = [t for t in available_tenors if t.startswith("M")]
        c1, c2 = st.columns(2)
        with c1: front_tenor = st.selectbox("FRONT", spread_tenors, index=0)
        with c2: back_tenor  = st.selectbox("BACK",  spread_tenors,
                                              index=min(1, len(spread_tenors)-1))

    elif view_mode == "Inter-Crude Spreads":
        crude_a      = st.selectbox("CRUDE A", products, index=0)
        crude_b      = st.selectbox("CRUDE B", [p for p in products if p != crude_a], index=0)
        spread_tenor = st.selectbox("TENOR", TENORS, index=0)

    st.markdown("---")
    st.caption("Source: crude clean sheet")

# ─── Plotly helpers ───────────────────────────────────────────────────────
CHART_COLORS = [AMBER, "#5B9CF6", GREEN, RED, "#A78BFA", "#F472B6",
                "#38BDF8", "#FBBF24", "#6EE7B7", "#94A3B8"]
MONTH_TICKS  = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


def style_fig(fig, title="", height=520):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=BG_CARD,
        title=dict(
            text=title.upper() if title else "",
            font=dict(family="IBM Plex Sans", size=13, color=TEXT_DIM),
            x=0.01, y=0.99,
        ),
        # Legend anchored BELOW the x-axis — never overlaps the chart
        legend=dict(
            bgcolor="rgba(17,21,32,0.9)",
            bordercolor=BORDER,
            borderwidth=1,
            font=dict(family="JetBrains Mono", size=10, color=TEXT),
            orientation="h",
            yanchor="top",
            y=-0.10,
            xanchor="left",
            x=0,
            itemwidth=40,
            itemsizing="constant",
        ),
        height=height,
        margin=dict(l=55, r=20, t=36, b=90),   # large bottom margin for legend
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=BG_CARD,
            font=dict(family="JetBrains Mono", size=11, color=WHITE),
            bordercolor=BORDER,
        ),
        xaxis=dict(
            gridcolor="#1C2333", showgrid=True, gridwidth=1, zeroline=False,
            linecolor=BORDER,
            tickfont=dict(family="JetBrains Mono", size=10, color=TEXT_DIM),
            hoverformat=" ",   # suppress raw day-of-year number in hover header
        ),
        yaxis=dict(
            gridcolor="#1C2333", showgrid=True, gridwidth=1, zeroline=False,
            linecolor=BORDER, side="right",
            title=dict(text="$/bbl",
                       font=dict(family="IBM Plex Sans", size=10, color=TEXT_DIM)),
            tickformat=",.1f",
            tickfont=dict(family="JetBrains Mono", size=10, color=TEXT_DIM),
        ),
    )
    return fig


def hex_to_rgba(hx, a):
    h = hx.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


# ─── Header + Tenor Strip ────────────────────────────────────────────────
latest    = df.iloc[-1]
prev      = df.iloc[-2]
last_date = df["Date"].iloc[-1].strftime("%d %b %Y")

header_label = f"{crude_a} / {crude_b}" if view_mode == "Inter-Crude Spreads" else selected_product.upper()
st.markdown(
    f'<div class="header-bar">'
    f'<span class="h-product">{header_label}</span>'
    f'<span class="h-date">Last: {last_date}</span>'
    f'</div>', unsafe_allow_html=True)




# ═══ PRICE HISTORY ════════════════════════════════════════════════════════
if view_mode == "Price History":
    if not selected_tenors:
        st.warning("Select at least one tenor.")
        st.stop()

    fig = go.Figure()
    for i, tenor in enumerate(selected_tenors):
        col = f"{selected_product}|{tenor}"
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["Date"], y=df[col], name=tenor,
                line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=1.5),
            ))
    style_fig(fig, f"{selected_product} Price History")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-div">Forward Curve — Latest</div>', unsafe_allow_html=True)
    curve_vals = [
        latest[f"{selected_product}|{t}"]
        if f"{selected_product}|{t}" in df.columns else np.nan
        for t in TENORS
    ]
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=TENORS, y=curve_vals, mode="lines+markers",
        line=dict(color=AMBER, width=2),
        marker=dict(size=6, color=AMBER, symbol="diamond"),
        fill="tozeroy", fillcolor=hex_to_rgba(AMBER, 0.06),
        showlegend=False,
    ))
    style_fig(fig2, "", height=300)
    st.plotly_chart(fig2, use_container_width=True)

# ═══ SEASONALITY ══════════════════════════════════════════════════════════
elif view_mode == "Seasonality":
    col_name = f"{selected_product}|{selected_tenor_season}"
    if col_name not in df.columns:
        st.error(f"Column {col_name} not found.")
        st.stop()

    sub = df[["Date", col_name]].dropna(subset=[col_name]).copy()
    sub["Year"]      = sub["Date"].dt.year
    sub["DayOfYear"] = sub["Date"].dt.dayofyear

    fig = go.Figure()
    range_years = sorted(sub["Year"].unique())[-5:]
    range_df    = sub[sub["Year"].isin(range_years)]
    # Band uses selected years excluding the current year
    band_years = sorted([y for y in selected_years if y != current_year])

    if show_range and len(band_years) >= 2:
        band_df = sub[sub["Year"].isin(band_years)]
        year_frames = []
        for yr in band_years:
            yr_df = band_df[band_df["Year"] == yr][["DayOfYear", col_name]].copy()
            yr_df = yr_df.drop_duplicates("DayOfYear").set_index("DayOfYear")
            yr_df = yr_df.reindex(range(1, 366))
            yr_df[col_name] = yr_df[col_name].interpolate("linear").bfill().ffill()
            year_frames.append(yr_df[col_name].rename(yr))
        grid = pd.concat(year_frames, axis=1)
        band_min = grid.min(axis=1)
        band_max = grid.max(axis=1)
        x = list(range(1, 366))
        fig.add_trace(go.Scatter(
            x=x, y=band_min.tolist(),
            line=dict(color="rgba(0,0,0,0)"), showlegend=False,
            hoverinfo="skip", connectgaps=True,
        ))
        fig.add_trace(go.Scatter(
            x=x, y=band_max.tolist(),
            fill="tonexty", fillcolor="rgba(255,140,0,0.10)",
            line=dict(color="rgba(0,0,0,0)"), connectgaps=True,
            name=f"{band_years[0]}–{band_years[-1]} Range",
            hoverinfo="skip",
        ))

    if show_avg and len(band_years) >= 2:
        band_df_avg = sub[sub["Year"].isin(band_years)]
        year_frames_avg = []
        for yr in band_years:
            yr_df = band_df_avg[band_df_avg["Year"] == yr][["DayOfYear", col_name]].copy()
            yr_df = yr_df.drop_duplicates("DayOfYear").set_index("DayOfYear")
            yr_df = yr_df.reindex(range(1, 366))
            yr_df[col_name] = yr_df[col_name].interpolate("linear").bfill().ffill()
            year_frames_avg.append(yr_df[col_name].rename(yr))
        grid_avg = pd.concat(year_frames_avg, axis=1)
        avg_vals = grid_avg.mean(axis=1)
        fig.add_trace(go.Scatter(
            x=list(range(1, 366)), y=avg_vals.tolist(),
            name=f"{len(band_years)}Y Avg",
            line=dict(color=TEXT_DIM, width=1.5, dash="dot"), connectgaps=True,
            hovertemplate="%{y:.1f}<extra>" + f"{len(band_years)}Y Avg" + "</extra>",
        ))

    for i, year in enumerate(sorted(selected_years)):
        yr = sub[sub["Year"] == year].drop_duplicates("DayOfYear").sort_values("DayOfYear")
        fig.add_trace(go.Scatter(
            x=yr["DayOfYear"], y=yr[col_name], name=str(year),
            line=dict(
                color=CHART_COLORS[i % len(CHART_COLORS)],
                width=2.5 if year == current_year else 1.2,
            ),
            opacity=1.0 if year == current_year else 0.7,
            hovertemplate="%{y:.1f}<extra>" + str(year) + "</extra>",
        ))

    style_fig(fig, f"{selected_product} {selected_tenor_season} Seasonality")
    fig.update_layout(xaxis=dict(tickvals=MONTH_TICKS, ticktext=MONTH_LABELS,
                                  range=[1, 365], title="", hoverformat=" "))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-div">Monthly Averages</div>', unsafe_allow_html=True)
    sub["Month"] = sub["Date"].dt.month
    pivot = sub.pivot_table(values=col_name, index="Year", columns="Month", aggfunc="mean")
    pivot.columns = [pd.Timestamp(2000, m, 1).strftime("%b") for m in pivot.columns]
    pivot = pivot.round(2)
    st.dataframe(
        pivot.loc[pivot.index.isin(selected_years)] if selected_years else pivot,
        use_container_width=True,
    )

# ═══ TIME SPREADS ═════════════════════════════════════════════════════════
elif view_mode == "Time Spreads":
    front_col = f"{selected_product}|{front_tenor}"
    back_col  = f"{selected_product}|{back_tenor}"
    if front_col not in df.columns or back_col not in df.columns:
        st.error("Selected tenors not available.")
        st.stop()

    spread      = df[front_col] - df[back_col]
    spread_name = f"{selected_product} {front_tenor}-{back_tenor}"

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.4], vertical_spacing=0.06)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[front_col], name=front_tenor,
                             line=dict(color=AMBER, width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[back_col], name=back_tenor,
                             line=dict(color="#5B9CF6", width=1.5)), row=1, col=1)

    # Use a filled area line for the spread so it's clearly visible at any scale
    spread_clean = spread.dropna()
    fig.add_trace(go.Scatter(
        x=df["Date"], y=spread,
        name="Spread",
        line=dict(color=AMBER, width=1.5),
        fill="tozeroy",
        fillcolor=hex_to_rgba(GREEN, 0.15),
    ), row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color=TEXT_DIM, opacity=0.6, row=2, col=1)

    style_fig(fig, f"{spread_name} Spread", height=620)
    fig.update_yaxes(title_text="$/bbl", row=1, col=1)

    # Auto-range the spread panel with a small padding so it fills the panel
    pad = max(spread_clean.abs().quantile(0.99) * 0.15, 0.05)
    fig.update_yaxes(
        title_text="Spread ($/bbl)", row=2, col=1,
        range=[spread_clean.min() - pad, spread_clean.max() + pad],
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-div">Spread Seasonality</div>', unsafe_allow_html=True)
    sp = pd.DataFrame({"Date": df["Date"], "Spread": spread}).dropna(subset=["Spread"])
    sp["Year"]      = sp["Date"].dt.year
    sp["DayOfYear"] = sp["Date"].dt.dayofyear

    fig3 = go.Figure()
    for i, year in enumerate(sorted(sp["Year"].unique())[-5:]):
        yr = sp[sp["Year"] == year].drop_duplicates("DayOfYear").sort_values("Date")
        fig3.add_trace(go.Scatter(
            x=yr["DayOfYear"], y=yr["Spread"], name=str(year),
            line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=1.3),
            hovertemplate="%{y:.2f}<extra>" + str(year) + "</extra>",
        ))
    style_fig(fig3, f"{spread_name} Spread Seasonality", height=380)
    fig3.update_layout(xaxis=dict(tickvals=MONTH_TICKS, ticktext=MONTH_LABELS, range=[1, 365], hoverformat=" "))
    st.plotly_chart(fig3, use_container_width=True)

# ═══ INTER-CRUDE SPREADS ═════════════════════════════════════════════════
elif view_mode == "Inter-Crude Spreads":
    col_a = f"{crude_a}|{spread_tenor}"
    col_b = f"{crude_b}|{spread_tenor}"
    if col_a not in df.columns or col_b not in df.columns:
        st.error(f"Columns not found: {col_a} or {col_b}")
        st.stop()

    crack      = df[col_a] - df[col_b]
    crack_name = f"{crude_a} vs {crude_b} ({spread_tenor})"
    crack_clean = crack.dropna()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.4], vertical_spacing=0.06)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[col_a], name=crude_a,
                             line=dict(color=AMBER, width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[col_b], name=crude_b,
                             line=dict(color="#5B9CF6", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df["Date"], y=crack, name="Spread",
        line=dict(color=AMBER, width=1.5),
        fill="tozeroy", fillcolor=hex_to_rgba(GREEN, 0.15),
    ), row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color=TEXT_DIM, opacity=0.6, row=2, col=1)
    style_fig(fig, f"Inter-Crude: {crack_name}", height=620)
    fig.update_yaxes(title_text="$/bbl", row=1, col=1)
    pad = max(crack_clean.abs().quantile(0.99) * 0.15, 0.05)
    fig.update_yaxes(
        title_text="Spread ($/bbl)", row=2, col=1,
        range=[crack_clean.min() - pad, crack_clean.max() + pad],
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-div">Spread Seasonality</div>', unsafe_allow_html=True)
    ck = pd.DataFrame({"Date": df["Date"], "Spread": crack}).dropna(subset=["Spread"])
    ck["Year"]      = ck["Date"].dt.year
    ck["DayOfYear"] = ck["Date"].dt.dayofyear

    fig4 = go.Figure()
    years = sorted(ck["Year"].unique())[-5:]
    current_year_ck = ck["Year"].max()
    band_years_ck = sorted([y for y in years if y != current_year_ck])
    for i, year in enumerate(years):
        yr = ck[ck["Year"] == year].drop_duplicates("DayOfYear").sort_values("Date")
        fig4.add_trace(go.Scatter(
            x=yr["DayOfYear"], y=yr["Spread"], name=str(year),
            line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=1.3),
            hovertemplate="%{y:.2f}<extra>" + str(year) + "</extra>",
        ))

    rng = ck[ck["Year"].isin(band_years_ck)].copy()
    year_frames_ck = []
    for yr in band_years_ck:
        yr_df = rng[rng["Year"] == yr][["DayOfYear", "Spread"]].copy()
        yr_df = yr_df.drop_duplicates("DayOfYear").set_index("DayOfYear")
        yr_df = yr_df.reindex(range(1, 366))
        yr_df["Spread"] = yr_df["Spread"].interpolate("linear").bfill().ffill()
        year_frames_ck.append(yr_df["Spread"].rename(yr))
    grid_ck  = pd.concat(year_frames_ck, axis=1)
    ck_min   = grid_ck.min(axis=1)
    ck_max   = grid_ck.max(axis=1)
    x = list(range(1, 366))
    fig4.add_trace(go.Scatter(
        x=x, y=ck_min.tolist(),
        line=dict(color="rgba(0,0,0,0)"), showlegend=False,
        hoverinfo="skip", connectgaps=True,
    ))
    fig4.add_trace(go.Scatter(
        x=x, y=ck_max.tolist(),
        fill="tonexty", fillcolor="rgba(255,140,0,0.10)",
        line=dict(color="rgba(0,0,0,0)"), connectgaps=True,
        name=f"{band_years_ck[0]}–{band_years_ck[-1]} Range", hoverinfo="skip",
    ))
    style_fig(fig4, f"Spread Seasonality: {crack_name}", height=400)
    fig4.update_layout(xaxis=dict(tickvals=MONTH_TICKS, ticktext=MONTH_LABELS, range=[1, 365], hoverformat=" "))
    st.plotly_chart(fig4, use_container_width=True)

# ─── Footer ────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="text-align:center;padding:16px 0 8px 0;font-size:0.65rem;'
    f'color:{BORDER};font-family:JetBrains Mono,monospace;letter-spacing:0.1em;">'
    f'CRUDE OIL TERMINAL  |  METS ANALYTICS</div>', unsafe_allow_html=True)
