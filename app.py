"""
Crude Oil Price Dashboard
--------------------------
Reads historical crude oil prices from Excel (crude clean sheet) and presents
interactive price history, seasonality, spread, inter-crude spread, and calendar
charts via Streamlit + Plotly.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import datetime

# ─── Page config ───────────────────────────────────────────────────────────
st.set_page_config(page_title="Crude Oil Dashboard", layout="wide", page_icon="🛢️")

# ─── Custom CSS — white / light theme ─────────────────────────────────────
st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #F5F7FA; }
    [data-testid="stSidebar"] * { color: #1E293B !important; }

    /* Main area */
    .stApp { background-color: #FFFFFF; }
    .block-container { padding-top: 1.2rem; }
    h1, h2, h3 { color: #1E293B; }
    p, span, label, div { color: #334155; }

    /* KPI metrics */
    .stMetric {
        background: linear-gradient(135deg, #F8FAFC, #EEF2F7);
        padding: 10px 14px; border-radius: 10px;
        border: 1px solid #E2E8F0;
    }
    div[data-testid="stMetricValue"] { color: #0F172A !important; font-size: 1.15rem !important; }
    div[data-testid="stMetricLabel"] { color: #64748B !important; font-size: 0.85rem !important; }
    div[data-testid="stMetricDelta"] > div { font-size: 0.8rem !important; }

    /* M1–M12 banner */
    .tenor-banner {
        display: flex; flex-wrap: wrap; gap: 8px;
        padding: 12px 0; margin-bottom: 8px;
    }
    .tenor-card {
        flex: 1 1 0; min-width: 80px; max-width: 120px;
        background: #F1F5F9; border: 1px solid #E2E8F0;
        border-radius: 8px; padding: 8px 10px; text-align: center;
    }
    .tenor-card .label { font-size: 0.7rem; color: #94A3B8; font-weight: 600; }
    .tenor-card .price { font-size: 0.95rem; color: #0F172A; font-weight: 700; }
    .tenor-card .chg-up   { font-size: 0.72rem; color: #16A34A; }
    .tenor-card .chg-down { font-size: 0.72rem; color: #DC2626; }
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

    # Normalise column names to "Product|Tenor" format
    df = pd.DataFrame({"Date": raw["Date"]})
    for short, prefix in PRODUCT_MAP.items():
        for t in TENORS:
            src = f"{prefix} {t}"
            dst = f"{short}|{t}"
            if src in raw.columns:
                vals = pd.to_numeric(raw[src], errors="coerce")
                vals = vals.replace(0, np.nan)
                df[dst] = vals

    # Drop rows where all price columns are NaN
    price_cols = [c for c in df.columns if c != "Date"]
    df = df.dropna(subset=price_cols, how="all").reset_index(drop=True)
    return df


if not DATA_FILE.exists():
    st.error(f"Data file not found at `{DATA_FILE}`.")
    st.stop()

df = load_data(str(DATA_FILE))

# ─── Parse column structure ────────────────────────────────────────────────
columns = [c for c in df.columns if c != "Date"]
products = sorted(set(c.split("|")[0] for c in columns))
tenors_map = {}
for c in columns:
    prod, tenor = c.split("|")
    tenors_map.setdefault(prod, []).append(tenor)

# ─── Sidebar controls ─────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/oil-industry.png", width=60)
    st.title("Crude Oil Dashboard")
    st.markdown("---")

    view_mode = st.radio("📊 View Mode", [
        "Price History",
        "Seasonality",
        "Spreads (M1–M2, etc.)",
        "Inter-Crude Spreads",
        "📅 Calendar",
    ])

    st.markdown("---")

    if view_mode != "📅 Calendar":
        st.subheader("Product Selection")
        selected_product = st.selectbox("Product", products)
        available_tenors = tenors_map.get(selected_product, TENORS)

        if view_mode == "Price History":
            selected_tenors = st.multiselect("Tenors", available_tenors, default=["M1", "M2"])
        elif view_mode == "Seasonality":
            selected_tenor_season = st.selectbox("Tenor", available_tenors, index=0)
            current_year = df["Date"].dt.year.max()
            all_years = sorted(df["Date"].dt.year.unique(), reverse=True)
            default_years = [y for y in all_years[:5]]
            selected_years = st.multiselect("Compare Years", all_years, default=default_years)
            show_range = st.checkbox("Show 5-Year Min/Max Range", value=True)
            show_avg = st.checkbox("Show 5-Year Average", value=True)
        elif view_mode == "Spreads (M1–M2, etc.)":
            spread_tenors = [t for t in available_tenors if t.startswith("M")]
            col1, col2 = st.columns(2)
            with col1:
                front_tenor = st.selectbox("Front", spread_tenors, index=0)
            with col2:
                back_idx = min(1, len(spread_tenors) - 1)
                back_tenor = st.selectbox("Back", spread_tenors, index=back_idx)
        elif view_mode == "Inter-Crude Spreads":
            crude_a = st.selectbox("Crude A", products, index=0)
            crude_b = st.selectbox("Crude B", [p for p in products if p != crude_a], index=0)
            spread_tenor = st.selectbox("Tenor", TENORS, index=0)

    st.markdown("---")
    st.caption("Data: crude clean sheet · Brent / WTI / Dubai")

# ─── Plotting helpers ──────────────────────────────────────────────────────
COLORS = ["#2563EB", "#DC2626", "#16A34A", "#D97706", "#7C3AED", "#DB2777",
          "#0891B2", "#4F46E5", "#B45309", "#64748B"]


def style_fig(fig, title="", height=560):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(248,250,252,1)",
        title=dict(text=title, font=dict(size=17, color="#1E293B"), x=0.02),
        legend=dict(bgcolor="rgba(255,255,255,0.8)", font=dict(size=11, color="#334155")),
        height=height,
        margin=dict(l=50, r=30, t=50, b=50),
        hovermode="x unified",
        xaxis=dict(gridcolor="rgba(0,0,0,0.06)", showgrid=True),
        yaxis=dict(gridcolor="rgba(0,0,0,0.06)", showgrid=True,
                   title="$/bbl", tickformat=",.1f"),
    )
    return fig


def hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ─── M1–M12 Banner at the top ─────────────────────────────────────────────
if view_mode != "📅 Calendar":
    st.markdown(f"## {selected_product}")

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    cards_html = '<div class="tenor-banner">'
    for t in TENORS:
        col_name = f"{selected_product}|{t}"
        if col_name in df.columns and pd.notna(latest[col_name]):
            val = latest[col_name]
            chg = val - prev[col_name] if pd.notna(prev[col_name]) else 0
            chg_cls = "chg-up" if chg >= 0 else "chg-down"
            chg_sign = "+" if chg >= 0 else ""
            cards_html += (
                f'<div class="tenor-card">'
                f'<div class="label">{t}</div>'
                f'<div class="price">${val:,.2f}</div>'
                f'<div class="{chg_cls}">{chg_sign}{chg:.2f}</div>'
                f'</div>'
            )
        else:
            cards_html += (
                f'<div class="tenor-card">'
                f'<div class="label">{t}</div>'
                f'<div class="price" style="color:#94A3B8;">—</div>'
                f'</div>'
            )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)
    st.markdown("---")

# ═══ VIEW: Price History ═══════════════════════════════════════════════════
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
                line=dict(color=COLORS[i % len(COLORS)], width=2),
            ))
    style_fig(fig, f"{selected_product} — Price History")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Forward Curve (Latest)")
    curve_vals = []
    for t in TENORS:
        c = f"{selected_product}|{t}"
        if c in df.columns:
            curve_vals.append(latest[c])
        else:
            curve_vals.append(np.nan)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=TENORS, y=curve_vals, mode="lines+markers",
        line=dict(color="#2563EB", width=3),
        marker=dict(size=8, color="#2563EB"),
        fill="tozeroy", fillcolor="rgba(37,99,235,0.07)"
    ))
    style_fig(fig2, f"{selected_product} — Forward Curve", height=350)
    fig2.update_layout(xaxis_title="Contract Month")
    st.plotly_chart(fig2, use_container_width=True)

# ═══ VIEW: Seasonality ════════════════════════════════════════════════════
elif view_mode == "Seasonality":
    col_name = f"{selected_product}|{selected_tenor_season}"
    if col_name not in df.columns:
        st.error(f"Column {col_name} not found.")
        st.stop()

    sub = df[["Date", col_name]].dropna(subset=[col_name]).copy()
    sub["Year"] = sub["Date"].dt.year
    sub["DayOfYear"] = sub["Date"].dt.dayofyear
    sub["MonthDay"] = sub["Date"].apply(lambda d: d.replace(year=2000))

    fig = go.Figure()
    range_years = sorted(sub["Year"].unique())[-5:]
    range_df = sub[sub["Year"].isin(range_years)]

    if show_range and len(range_years) >= 2:
        agg = range_df.groupby("DayOfYear")[col_name].agg(["min", "max"]).reset_index()
        # Reindex to continuous 1–365 and interpolate to remove weekend gaps
        full_days = pd.DataFrame({"DayOfYear": range(1, 366)})
        agg = full_days.merge(agg, on="DayOfYear", how="left")
        agg["min"] = agg["min"].interpolate(method="linear").bfill().ffill()
        agg["max"] = agg["max"].interpolate(method="linear").bfill().ffill()
        agg["MonthDay"] = pd.to_datetime("2000-01-01") + pd.to_timedelta(agg["DayOfYear"] - 1, unit="D")
        # Draw as a single closed polygon: upper edge forward, lower edge reversed
        fig.add_trace(go.Scatter(
            x=pd.concat([agg["MonthDay"], agg["MonthDay"][::-1]]),
            y=pd.concat([agg["max"], agg["min"][::-1]]),
            fill="toself",
            fillcolor="rgba(37,99,235,0.10)",
            line=dict(color="rgba(0,0,0,0)"),
            name=f"{range_years[0]}–{range_years[-1]} Range",
            hoverinfo="skip",
        ))

    if show_avg and len(range_years) >= 2:
        avg = range_df.groupby("DayOfYear")[col_name].mean().reset_index()
        full_days = pd.DataFrame({"DayOfYear": range(1, 366)})
        avg = full_days.merge(avg, on="DayOfYear", how="left")
        avg[col_name] = avg[col_name].interpolate(method="linear")
        avg["MonthDay"] = pd.to_datetime("2000-01-01") + pd.to_timedelta(avg["DayOfYear"] - 1, unit="D")
        fig.add_trace(go.Scatter(
            x=avg["MonthDay"], y=avg[col_name], name="5Y Average",
            line=dict(color="#94A3B8", width=2, dash="dash"),
        ))

    for i, year in enumerate(sorted(selected_years)):
        yr_data = sub[sub["Year"] == year].sort_values("DayOfYear")
        is_current = (year == current_year)
        fig.add_trace(go.Scatter(
            x=yr_data["MonthDay"], y=yr_data[col_name],
            name=str(year),
            line=dict(color=COLORS[i % len(COLORS)],
                      width=3 if is_current else 1.8),
            opacity=1.0 if is_current else 0.75,
        ))

    style_fig(fig, f"{selected_product} {selected_tenor_season} — Seasonality")
    fig.update_layout(xaxis=dict(tickformat="%b", dtick="M1",
                                  range=["2000-01-01", "2000-12-31"], title=""))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Monthly Averages by Year")
    sub["Month"] = sub["Date"].dt.month
    pivot = sub.pivot_table(values=col_name, index="Year", columns="Month", aggfunc="mean")
    pivot.columns = [pd.Timestamp(2000, m, 1).strftime("%b") for m in pivot.columns]
    pivot = pivot.round(2)
    if not selected_years:
        st.dataframe(pivot, use_container_width=True)
    else:
        st.dataframe(pivot.loc[pivot.index.isin(selected_years)], use_container_width=True)

# ═══ VIEW: Spreads ═════════════════════════════════════════════════════════
elif view_mode == "Spreads (M1–M2, etc.)":
    front_col = f"{selected_product}|{front_tenor}"
    back_col = f"{selected_product}|{back_tenor}"
    if front_col not in df.columns or back_col not in df.columns:
        st.error("Selected tenors not available.")
        st.stop()

    spread = df[front_col] - df[back_col]
    spread_name = f"{selected_product} {front_tenor}–{back_tenor}"

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35],
                        vertical_spacing=0.06)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[front_col], name=front_tenor,
                             line=dict(color="#2563EB", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[back_col], name=back_tenor,
                             line=dict(color="#DC2626", width=2)), row=1, col=1)
    colors = ["#16A34A" if v >= 0 else "#DC2626" for v in spread]
    fig.add_trace(go.Bar(x=df["Date"], y=spread, name="Spread",
                         marker_color=colors, opacity=0.7), row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="#94A3B8", opacity=0.6, row=2, col=1)

    style_fig(fig, f"{spread_name} Spread", height=620)
    fig.update_yaxes(title_text="$/bbl", row=1, col=1)
    fig.update_yaxes(title_text="Spread $/bbl", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Spread Seasonality")
    sp_df = pd.DataFrame({"Date": df["Date"], "Spread": spread})
    sp_df = sp_df.dropna(subset=["Spread"])
    sp_df["Year"] = sp_df["Date"].dt.year
    sp_df["MonthDay"] = sp_df["Date"].apply(lambda d: d.replace(year=2000))

    fig3 = go.Figure()
    for i, year in enumerate(sorted(sp_df["Year"].unique())[-5:]):
        yr = sp_df[sp_df["Year"] == year].sort_values("Date")
        fig3.add_trace(go.Scatter(
            x=yr["MonthDay"], y=yr["Spread"], name=str(year),
            line=dict(color=COLORS[i % len(COLORS)], width=2)
        ))
    style_fig(fig3, f"{spread_name} Spread — Seasonality", height=380)
    fig3.update_layout(xaxis=dict(tickformat="%b", dtick="M1",
                                   range=["2000-01-01", "2000-12-31"]))
    st.plotly_chart(fig3, use_container_width=True)

# ═══ VIEW: Inter-Crude Spreads ═════════════════════════════════════════════
elif view_mode == "Inter-Crude Spreads":
    col_a = f"{crude_a}|{spread_tenor}"
    col_b = f"{crude_b}|{spread_tenor}"
    if col_a not in df.columns or col_b not in df.columns:
        st.error(f"Columns not found: {col_a} or {col_b}")
        st.stop()

    crack = df[col_a] - df[col_b]
    crack_name = f"{crude_a} vs {crude_b} ({spread_tenor})"

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.55, 0.45],
                        vertical_spacing=0.06)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[col_a], name=crude_a,
                             line=dict(color="#2563EB", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[col_b], name=crude_b,
                             line=dict(color="#DC2626", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=crack, name="Spread",
                             line=dict(color="#16A34A", width=2),
                             fill="tozeroy", fillcolor="rgba(22,163,74,0.10)"), row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="#94A3B8", opacity=0.6, row=2, col=1)

    style_fig(fig, f"Inter-Crude Spread: {crack_name}", height=620)
    fig.update_yaxes(title_text="$/bbl", row=1, col=1)
    fig.update_yaxes(title_text="Spread $/bbl", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Spread Seasonality")
    ck_df = pd.DataFrame({"Date": df["Date"], "Spread": crack})
    ck_df = ck_df.dropna(subset=["Spread"])
    ck_df["Year"] = ck_df["Date"].dt.year
    ck_df["MonthDay"] = ck_df["Date"].apply(lambda d: d.replace(year=2000))

    fig4 = go.Figure()
    years = sorted(ck_df["Year"].unique())[-5:]
    for i, year in enumerate(years):
        yr = ck_df[ck_df["Year"] == year].sort_values("Date")
        fig4.add_trace(go.Scatter(
            x=yr["MonthDay"], y=yr["Spread"], name=str(year),
            line=dict(color=COLORS[i % len(COLORS)], width=2)
        ))
    range_df = ck_df[ck_df["Year"].isin(years)]
    range_df["DayOfYear"] = range_df["Date"].dt.dayofyear
    agg = range_df.groupby("DayOfYear")["Spread"].agg(["min", "max"]).reset_index()
    full_days = pd.DataFrame({"DayOfYear": range(1, 366)})
    agg = full_days.merge(agg, on="DayOfYear", how="left")
    agg["min"] = agg["min"].interpolate(method="linear").bfill().ffill()
    agg["max"] = agg["max"].interpolate(method="linear").bfill().ffill()
    agg["MonthDay"] = pd.to_datetime("2000-01-01") + pd.to_timedelta(agg["DayOfYear"] - 1, unit="D")
    fig4.add_trace(go.Scatter(
        x=pd.concat([agg["MonthDay"], agg["MonthDay"][::-1]]),
        y=pd.concat([agg["max"], agg["min"][::-1]]),
        fill="toself",
        fillcolor="rgba(37,99,235,0.10)",
        line=dict(color="rgba(0,0,0,0)"),
        name=f"{years[0]}–{years[-1]} Range",
        hoverinfo="skip",
    ))

    style_fig(fig4, f"Spread Seasonality: {crack_name}", height=400)
    fig4.update_layout(xaxis=dict(tickformat="%b", dtick="M1",
                                   range=["2000-01-01", "2000-12-31"]))
    st.plotly_chart(fig4, use_container_width=True)

# ═══ VIEW: Calendar ════════════════════════════════════════════════════════
elif view_mode == "📅 Calendar":

    st.markdown("## Market Calendar")

    econ_tab, geo_tab = st.tabs(["📊 Economic Calendar", "🌍 Geopolitical Calendar"])

    with econ_tab:
        st.markdown("### Economic Calendar")
        st.caption(
            "High-impact events for the US, EU, China, and Japan — "
            "the four macro territories that drive oil demand and dollar pricing."
        )

        if "te_api_key" not in st.session_state:
            st.session_state["te_api_key"] = ""

        with st.expander(
            "🔑 Trading Economics API Key",
            expanded=not bool(st.session_state["te_api_key"])
        ):
            key_input = st.text_input(
                "Paste your API key here",
                value=st.session_state["te_api_key"],
                type="password",
                help=(
                    "Get a key at tradingeconomics.com/api. "
                    "Leave blank to use the free guest:guest demo key "
                    "(returns limited sample data only)."
                ),
            )
            if key_input != st.session_state["te_api_key"]:
                st.session_state["te_api_key"] = key_input
                st.rerun()

        api_key = st.session_state["te_api_key"] or "guest:guest"

        col_f1, col_f2, col_f3 = st.columns([1, 1, 1])

        with col_f1:
            horizon = st.selectbox(
                "Horizon",
                ["Today", "Next 7 Days", "Next 14 Days", "Next Month"],
                index=1,
                key="cal_horizon",
            )

        with col_f2:
            importance_filter = st.multiselect(
                "Importance",
                ["🔴 High (3)", "🟡 Medium (2)", "🟢 Low (1)"],
                default=["🔴 High (3)", "🟡 Medium (2)"],
                key="cal_importance",
            )

        with col_f3:
            country_filter = st.multiselect(
                "Territory",
                ["United States", "Euro Area", "China", "Japan"],
                default=["United States", "Euro Area", "China", "Japan"],
                key="cal_countries",
            )

        COUNTRY_API_MAP = {
            "United States": ["united states"],
            "Euro Area":     ["euro area", "germany", "france"],
            "China":         ["china"],
            "Japan":         ["japan"],
        }

        API_TO_TERRITORY = {}
        for territory, api_list in COUNTRY_API_MAP.items():
            for api_name in api_list:
                API_TO_TERRITORY[api_name.lower()] = territory

        IMPORTANCE_INT   = {"🔴 High (3)": 3, "🟡 Medium (2)": 2, "🟢 Low (1)": 1}
        IMPORTANCE_LABEL = {3: "🔴 High", 2: "🟡 Medium", 1: "🟢 Low"}

        FLAG = {
            "United States": "🇺🇸",
            "Euro Area":     "🇪🇺",
            "China":         "🇨🇳",
            "Japan":         "🇯🇵",
        }

        today     = datetime.date.today()
        delta_map = {"Today": 0, "Next 7 Days": 7, "Next 14 Days": 14, "Next Month": 30}
        end_date  = today + datetime.timedelta(days=delta_map[horizon])
        init_str  = today.strftime("%Y-%m-%d")
        end_str   = end_date.strftime("%Y-%m-%d")

        selected_importance_ints = [IMPORTANCE_INT[i] for i in importance_filter]

        @st.cache_data(ttl=900, show_spinner=False)
        def fetch_te_calendar(countries_key, init_date, end_date, key):
            import requests
            import urllib.parse
            encoded_countries = urllib.parse.quote(countries_key)
            url = (
                f"https://api.tradingeconomics.com/calendar/country/"
                f"{encoded_countries}/{init_date}/{end_date}"
                f"?c={key}"
            )
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.HTTPError as e:
                return {"error": f"HTTP {resp.status_code}: {e}"}
            except Exception as e:
                return {"error": str(e)}

        api_countries = []
        for territory in country_filter:
            for api_name in COUNTRY_API_MAP.get(territory, [territory.lower()]):
                if api_name not in api_countries:
                    api_countries.append(api_name)

        countries_key = ",".join(api_countries)

        if not country_filter:
            st.warning("Select at least one territory.")
        else:
            with st.spinner("Fetching calendar from Trading Economics…"):
                raw = fetch_te_calendar(countries_key, init_str, end_str, api_key)

            if isinstance(raw, dict) and "error" in raw:
                st.error(
                    f"**API error:** {raw['error']}\n\n"
                    "Check that your API key is correct, or leave it blank to "
                    "use the guest demo key."
                )
                st.stop()

            if not raw:
                st.info("No events returned for the selected period and territories.")
            else:
                rows = []
                for ev in raw:
                    imp = int(ev.get("Importance") or 1)
                    if imp not in selected_importance_ints:
                        continue

                    api_country    = (ev.get("Country") or "").strip()
                    territory_label = API_TO_TERRITORY.get(api_country.lower())
                    if territory_label is None or territory_label not in country_filter:
                        continue

                    raw_date = ev.get("Date", "")
                    try:
                        dt        = datetime.datetime.fromisoformat(raw_date)
                        date_str  = dt.strftime("%a %d %b")
                        time_str  = dt.strftime("%H:%M")
                    except Exception:
                        date_str  = raw_date[:10]
                        time_str  = ""

                    flag = FLAG.get(territory_label, "")

                    rows.append({
                        "Date":        date_str,
                        "Time (UTC)":  time_str,
                        "Territory":   f"{flag} {territory_label}",
                        "Event":       ev.get("Event", ""),
                        "Category":    ev.get("Category", ""),
                        "Importance":  IMPORTANCE_LABEL[imp],
                        "Previous":    ev.get("Previous")   or "—",
                        "Forecast":    ev.get("Forecast") or ev.get("TEForecast") or "—",
                        "Actual":      ev.get("Actual")     or "—",
                    })

                if not rows:
                    st.info("No events match the selected importance / territory filters.")
                else:
                    cal_df = pd.DataFrame(rows)

                    def highlight_importance(val):
                        if "High"   in val: return "color: #DC2626; font-weight: 600"
                        if "Medium" in val: return "color: #D97706; font-weight: 600"
                        return "color: #16A34A"

                    styled_df = cal_df.style.map(highlight_importance, subset=["Importance"])

                    st.dataframe(
                        styled_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Date":       st.column_config.TextColumn(width="small"),
                            "Time (UTC)": st.column_config.TextColumn(width="small"),
                            "Territory":  st.column_config.TextColumn(width="medium"),
                            "Event":      st.column_config.TextColumn(width="large"),
                            "Category":   st.column_config.TextColumn(width="medium"),
                            "Importance": st.column_config.TextColumn(width="small"),
                            "Previous":   st.column_config.TextColumn(width="small"),
                            "Forecast":   st.column_config.TextColumn(width="small"),
                            "Actual":     st.column_config.TextColumn(width="small"),
                        },
                    )

                    st.caption(
                        f"**{len(rows)}** events shown · "
                        f"Source: Trading Economics · "
                        f"Refreshes every 15 min · Times in UTC"
                    )

            st.markdown("---")
            st.info(
                "💡 **What to watch for oil:**  "
                "🇺🇸 **Fed decisions & NFP** — dollar moves directly inverse to oil.  "
                "🇨🇳 **China PMI & industrial output** — biggest demand signal.  "
                "🇪🇺 **ECB rate decisions** — affect Euro and European refinery margins.  "
                "🇯🇵 **BoJ policy surprises** — JPY carry-trade unwinds ripple into commodities."
            )

    with geo_tab:
        st.markdown("### Geopolitical Risk Monitor")
        st.caption("Ongoing situations with direct oil supply or shipping implications.")
        st.info("🚧 Geopolitical calendar coming soon.")

# ─── Footer ────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Crude Oil Dashboard · Data: crude clean sheet · Built with Streamlit + Plotly")
