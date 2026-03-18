"""
Oil Barrel Price Dashboard
--------------------------
Reads historical oil product prices from Excel and presents interactive
seasonality, spread, crack, and seasonal forecast charts via Streamlit + Plotly.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# ─── Page config ───────────────────────────────────────────────────────────
st.set_page_config(page_title="Oil Barrel Dashboard", layout="wide", page_icon="🛢️")

# ─── Custom CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0E1B2A; }
    [data-testid="stSidebar"] * { color: #E0E0E0 !important; }
    .stMetric { background: linear-gradient(135deg, #1B3A5C, #0E1B2A);
                padding: 12px 16px; border-radius: 10px; border: 1px solid #2A5580; }
    div[data-testid="stMetricValue"] { color: #4FC3F7 !important; font-size: 1.3rem !important; }
    div[data-testid="stMetricLabel"] { color: #90CAF9 !important; }
    .block-container { padding-top: 1.5rem; }
    h1, h2, h3 { color: #E0E0E0; }
</style>
""", unsafe_allow_html=True)

# ─── Load data ─────────────────────────────────────────────────────────────
DATA_FILE = Path(__file__).parent / "oil_barrel_prices.xlsx"

@st.cache_data(ttl=3600)
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Prices")
    df["Date"] = pd.to_datetime(df["Date"])
    return df

if not DATA_FILE.exists():
    st.error(f"Data file not found at `{DATA_FILE}`. Run `python generate_data.py` first.")
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
    st.title("🛢️ Oil Barrel")
    st.markdown("---")

    view_mode = st.radio("📊 View Mode", [
        "Price History",
        "Seasonality",
        "Spreads (M1–M2, etc.)",
        "Cracks (Product – Crude)",
        "Seasonal Forecast"
    ])

    st.markdown("---")
    st.subheader("Product Selection")
    selected_product = st.selectbox("Product", products)
    available_tenors = tenors_map.get(selected_product, ["Spot"])

    if view_mode == "Price History":
        selected_tenors = st.multiselect("Tenors", available_tenors, default=["Spot", "M1"])
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
    elif view_mode == "Cracks (Product – Crude)":
        crack_product = st.selectbox("Product (numerator)", [p for p in products if "Brent" not in p and "WTI" not in p])
        crack_crude = st.selectbox("Crude (denominator)", ["Brent", "WTI"])
        crack_tenor = st.selectbox("Tenor", ["Spot", "M1", "M2", "M3", "Q1", "Q2"])
    elif view_mode == "Seasonal Forecast":
        forecast_products = st.multiselect(
            "Products to forecast",
            products,
            default=["Brent"],
            help="Pick one or more products to compare."
        )
        forecast_tenor = st.selectbox("Tenor", ["Spot", "M1", "M2", "M3"], index=0)
        forecast_horizon = st.select_slider(
            "Forecast horizon",
            options=["3M", "6M", "12M"],
            value="6M",
        )

    st.markdown("---")
    st.caption("Data: Dummy generated · Updated daily")

# ─── Plotting helpers ──────────────────────────────────────────────────────
COLORS = ["#4FC3F7", "#FF8A65", "#81C784", "#BA68C8", "#FFD54F", "#E57373",
          "#4DB6AC", "#7986CB", "#A1887F", "#90A4AE"]

def style_fig(fig, title="", height=560):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(14,27,42,0.6)",
        title=dict(text=title, font=dict(size=18, color="#E0E0E0"), x=0.02),
        legend=dict(bgcolor="rgba(0,0,0,0.3)", font=dict(size=11)),
        height=height,
        margin=dict(l=50, r=30, t=50, b=50),
        hovermode="x unified",
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)", showgrid=True),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)", showgrid=True,
                   title="$/bbl", tickformat=",.1f"),
    )
    return fig

def hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

# ─── Main content area ────────────────────────────────────────────────────
if view_mode != "Seasonal Forecast":
    st.markdown(f"## {selected_product}")

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    kpi_cols = st.columns(5)
    show_tenors = ["Spot", "M1", "M3", "M6", "M12"]
    for i, t in enumerate(show_tenors):
        col_name = f"{selected_product}|{t}"
        if col_name in df.columns:
            val = latest[col_name]
            chg = val - prev[col_name]
            kpi_cols[i].metric(t, f"${val:,.2f}", f"{chg:+.2f}")

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
    m_tenors = [f"M{i}" for i in range(1, 13)]
    curve_vals = []
    for t in m_tenors:
        c = f"{selected_product}|{t}"
        if c in df.columns:
            curve_vals.append(latest[c])
        else:
            curve_vals.append(np.nan)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=m_tenors, y=curve_vals, mode="lines+markers",
        line=dict(color="#4FC3F7", width=3),
        marker=dict(size=8, color="#4FC3F7"),
        fill="tozeroy", fillcolor="rgba(79,195,247,0.1)"
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

    sub = df[["Date", col_name]].copy()
    sub["Year"] = sub["Date"].dt.year
    sub["DayOfYear"] = sub["Date"].dt.dayofyear
    sub["MonthDay"] = sub["Date"].apply(lambda d: d.replace(year=2000))

    fig = go.Figure()
    range_years = sorted(sub["Year"].unique())[-5:]
    range_df = sub[sub["Year"].isin(range_years)]

    if show_range and len(range_years) >= 2:
        agg = range_df.groupby("DayOfYear")[col_name].agg(["min", "max"]).reset_index()
        agg["MonthDay"] = pd.to_datetime("2000-01-01") + pd.to_timedelta(agg["DayOfYear"] - 1, unit="D")
        fig.add_trace(go.Scatter(
            x=agg["MonthDay"], y=agg["max"], mode="lines",
            line=dict(width=0), showlegend=False, hoverinfo="skip"
        ))
        fig.add_trace(go.Scatter(
            x=agg["MonthDay"], y=agg["min"], mode="lines",
            line=dict(width=0), fill="tonexty",
            fillcolor="rgba(79,195,247,0.12)",
            name=f"{range_years[0]}–{range_years[-1]} Range",
        ))

    if show_avg and len(range_years) >= 2:
        avg = range_df.groupby("DayOfYear")[col_name].mean().reset_index()
        avg["MonthDay"] = pd.to_datetime("2000-01-01") + pd.to_timedelta(avg["DayOfYear"] - 1, unit="D")
        fig.add_trace(go.Scatter(
            x=avg["MonthDay"], y=avg[col_name], name="5Y Average",
            line=dict(color="#FFFFFF", width=2, dash="dash"),
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
                             line=dict(color="#4FC3F7", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[back_col], name=back_tenor,
                             line=dict(color="#FF8A65", width=2)), row=1, col=1)
    colors = ["#81C784" if v >= 0 else "#E57373" for v in spread]
    fig.add_trace(go.Bar(x=df["Date"], y=spread, name="Spread",
                         marker_color=colors, opacity=0.7), row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="white", opacity=0.4, row=2, col=1)

    style_fig(fig, f"{spread_name} Spread", height=620)
    fig.update_yaxes(title_text="$/bbl", row=1, col=1)
    fig.update_yaxes(title_text="Spread $/bbl", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Spread Seasonality")
    sp_df = pd.DataFrame({"Date": df["Date"], "Spread": spread})
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

# ═══ VIEW: Cracks ══════════════════════════════════════════════════════════
elif view_mode == "Cracks (Product – Crude)":
    prod_col = f"{crack_product}|{crack_tenor}"
    crude_col = f"{crack_crude}|{crack_tenor}"
    if prod_col not in df.columns or crude_col not in df.columns:
        st.error(f"Columns not found: {prod_col} or {crude_col}")
        st.stop()

    crack = df[prod_col] - df[crude_col]
    crack_name = f"{crack_product} vs {crack_crude} ({crack_tenor})"

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.55, 0.45],
                        vertical_spacing=0.06)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[prod_col], name=crack_product,
                             line=dict(color="#4FC3F7", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df[crude_col], name=crack_crude,
                             line=dict(color="#FF8A65", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=crack, name="Crack",
                             line=dict(color="#81C784", width=2),
                             fill="tozeroy", fillcolor="rgba(129,199,132,0.15)"), row=2, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="white", opacity=0.4, row=2, col=1)

    style_fig(fig, f"Crack Spread: {crack_name}", height=620)
    fig.update_yaxes(title_text="$/bbl", row=1, col=1)
    fig.update_yaxes(title_text="Crack $/bbl", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Crack Seasonality")
    ck_df = pd.DataFrame({"Date": df["Date"], "Crack": crack})
    ck_df["Year"] = ck_df["Date"].dt.year
    ck_df["MonthDay"] = ck_df["Date"].apply(lambda d: d.replace(year=2000))

    fig4 = go.Figure()
    years = sorted(ck_df["Year"].unique())[-5:]
    for i, year in enumerate(years):
        yr = ck_df[ck_df["Year"] == year].sort_values("Date")
        fig4.add_trace(go.Scatter(
            x=yr["MonthDay"], y=yr["Crack"], name=str(year),
            line=dict(color=COLORS[i % len(COLORS)], width=2)
        ))
    range_df = ck_df[ck_df["Year"].isin(years)]
    range_df["DayOfYear"] = range_df["Date"].dt.dayofyear
    agg = range_df.groupby("DayOfYear")["Crack"].agg(["min", "max"]).reset_index()
    agg["MonthDay"] = pd.to_datetime("2000-01-01") + pd.to_timedelta(agg["DayOfYear"] - 1, unit="D")
    fig4.add_trace(go.Scatter(x=agg["MonthDay"], y=agg["max"], mode="lines",
                              line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig4.add_trace(go.Scatter(x=agg["MonthDay"], y=agg["min"], mode="lines",
                              line=dict(width=0), fill="tonexty",
                              fillcolor="rgba(79,195,247,0.10)",
                              name=f"{years[0]}–{years[-1]} Range"))

    style_fig(fig4, f"Crack Seasonality: {crack_name}", height=400)
    fig4.update_layout(xaxis=dict(tickformat="%b", dtick="M1",
                                   range=["2000-01-01", "2000-12-31"]))
    st.plotly_chart(fig4, use_container_width=True)

# ═══ VIEW: Seasonal Forecast ══════════════════════════════════════════════
elif view_mode == "Seasonal Forecast":

    st.markdown("## Seasonal Price Forecast")

    # ── Plain-English model explanation ──
    st.markdown(
        "**How this works:** Oil prices follow seasonal patterns — heating fuel "
        "demand peaks in winter, driving fuel demand rises in summer, and refineries "
        "go through maintenance cycles. This model takes the **5-year average** of "
        "what each product does month-by-month, anchors it to today's actual price, "
        "and projects that path forward. The shaded range shows the **historical "
        "min–max** over those 5 years — so you can see how wide the actual outcomes "
        "have been around the seasonal average."
    )

    if not forecast_products:
        st.warning("Select at least one product from the sidebar.")
        st.stop()

    # ── Horizon & date setup ──
    hz_map = {"3M": 63, "6M": 126, "12M": 252}
    hz_days = hz_map[forecast_horizon]

    current_date = df["Date"].iloc[-1]
    current_doy = current_date.dayofyear
    fwd_dates = pd.bdate_range(current_date, periods=hz_days + 1)
    all_years = sorted(df["Date"].dt.year.unique())
    range_years = all_years[-5:]

    # ── Compute forecasts ──
    forecast_results = {}

    for product in forecast_products:
        col_name = f"{product}|{forecast_tenor}"
        if col_name not in df.columns:
            continue

        sub = df[["Date", col_name]].dropna().copy()
        sub["Year"] = sub["Date"].dt.year
        sub["DayOfYear"] = sub["Date"].dt.dayofyear
        current_price = sub[col_name].iloc[-1]

        range_df = sub[sub["Year"].isin(range_years)]
        seasonal_avg = range_df.groupby("DayOfYear")[col_name].mean()
        seasonal_min = range_df.groupby("DayOfYear")[col_name].min()
        seasonal_max = range_df.groupby("DayOfYear")[col_name].max()

        # Smooth out day-to-day noise using circular (wrap-around) rolling average.
        # Without this, each point is the average of only 5 values (one per year)
        # which creates a jagged sawtooth pattern. We wrap the series so Dec–Jan
        # transitions are smooth too.
        smooth_window = 30
        def circular_smooth(series, window=smooth_window):
            padded = pd.concat([series.iloc[-window:], series, series.iloc[:window]])
            smoothed = padded.rolling(window, center=True, min_periods=5).mean()
            return smoothed.iloc[window:-window]

        seasonal_avg = circular_smooth(seasonal_avg)
        seasonal_min = circular_smooth(seasonal_min)
        seasonal_max = circular_smooth(seasonal_max)

        anchor_avg = seasonal_avg.get(current_doy, current_price)
        anchor_min = seasonal_min.get(current_doy, current_price)
        anchor_max = seasonal_max.get(current_doy, current_price)

        fwd_avg, fwd_lo, fwd_hi = [], [], []
        for d in range(hz_days + 1):
            future_doy = ((current_doy + d - 1) % 365) + 1

            avg_val = seasonal_avg.get(future_doy, np.nan)
            min_val = seasonal_min.get(future_doy, np.nan)
            max_val = seasonal_max.get(future_doy, np.nan)

            if not np.isnan(avg_val) and anchor_avg != 0:
                fwd_avg.append(current_price * (avg_val / anchor_avg))
            else:
                fwd_avg.append(current_price)

            if not np.isnan(min_val) and anchor_min != 0:
                fwd_lo.append(current_price * (min_val / anchor_min))
            else:
                fwd_lo.append(current_price)

            if not np.isnan(max_val) and anchor_max != 0:
                fwd_hi.append(current_price * (max_val / anchor_max))
            else:
                fwd_hi.append(current_price)

        # Final light smooth on output to remove any remaining bumps
        def smooth_array(arr, w=10):
            s = pd.Series(arr).rolling(w, center=True, min_periods=3).mean()
            s.iloc[0] = arr[0]  # keep exact starting price
            return s.bfill().ffill().values

        forecast_results[product] = {
            "current": current_price,
            "fwd_avg": smooth_array(np.array(fwd_avg)),
            "fwd_lo": smooth_array(np.array(fwd_lo)),
            "fwd_hi": smooth_array(np.array(fwd_hi)),
        }

    # ── Summary cards ──
    summary_cols = st.columns(max(len(forecast_products), 1))
    for idx, product in enumerate(forecast_products):
        if product not in forecast_results:
            continue
        r = forecast_results[product]
        end_fc = r["fwd_avg"][-1]
        chg = end_fc - r["current"]
        chg_pct = chg / r["current"] * 100
        direction = "↑" if chg > 0 else "↓"

        with summary_cols[idx]:
            st.metric(
                product,
                f"${r['current']:,.2f} → ${end_fc:,.2f}",
                f"{direction} {abs(chg_pct):.1f}% ({forecast_horizon})"
            )
            st.caption(f"Range: ${r['fwd_lo'][-1]:,.1f} – ${r['fwd_hi'][-1]:,.1f}")

    st.markdown("---")

    # ── Main forecast chart ──
    st.markdown("### Forecast Chart")
    st.caption(
        f"**Solid line** = where prices typically go at this time of year (5-year "
        f"seasonal average, anchored to today's price). **Shaded area** = the "
        f"full range of what actually happened in the last 5 years. If the range "
        f"is wide, the seasonal pattern is less reliable for that product."
    )

    fig = go.Figure()

    for i, product in enumerate(forecast_products):
        if product not in forecast_results:
            continue
        r = forecast_results[product]
        color = COLORS[i % len(COLORS)]

        # Range band
        fig.add_trace(go.Scatter(
            x=fwd_dates, y=r["fwd_hi"], mode="lines",
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=fwd_dates, y=r["fwd_lo"], mode="lines",
            line=dict(width=0), fill="tonexty",
            fillcolor=hex_to_rgba(color, 0.12),
            name=f"{product} range",
        ))

        # Forecast line
        fig.add_trace(go.Scatter(
            x=fwd_dates, y=r["fwd_avg"],
            name=f"{product} forecast",
            line=dict(color=color, width=3),
        ))

        # Starting dot
        fig.add_trace(go.Scatter(
            x=[fwd_dates[0]], y=[r["current"]],
            mode="markers", showlegend=False,
            marker=dict(size=9, color=color, symbol="diamond"),
        ))

        # End label
        fig.add_annotation(
            x=fwd_dates[-1], y=r["fwd_avg"][-1],
            text=f"${r['fwd_avg'][-1]:,.1f}",
            showarrow=False, font=dict(size=11, color=color),
            xanchor="left", xshift=8
        )

    style_fig(fig, "", height=500)
    fig.update_layout(
        xaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── Forward Curve Shape ──
    st.markdown("### Forward Curve Shape")
    st.markdown(
        "**What this shows:** The forward curve plots today's price for each future "
        "delivery month (M1 = next month, M12 = 12 months out). The **shape** tells "
        "you what the market expects:\n\n"
        "- **Upward slope (contango):** Later months cost more than near months. "
        "This usually means the market is well-supplied — there's no urgency to buy now, "
        "so storage and financing costs get priced into future months.\n"
        "- **Downward slope (backwardation):** Near months cost more than later months. "
        "This usually means supply is tight right now — buyers are paying a premium for "
        "immediate delivery.\n"
        "- **Flat:** No strong supply/demand imbalance. The market is balanced."
    )

    fig_curve = go.Figure()
    m_labels = [f"M{i}" for i in range(1, 13)]

    for i, product in enumerate(forecast_products):
        if product not in forecast_results:
            continue
        color = COLORS[i % len(COLORS)]
        curve_vals = []
        for t in m_labels:
            c = f"{product}|{t}"
            if c in df.columns:
                curve_vals.append(df[c].iloc[-1])
            else:
                curve_vals.append(np.nan)

        fig_curve.add_trace(go.Scatter(
            x=m_labels, y=curve_vals, mode="lines+markers",
            name=product,
            line=dict(color=color, width=3),
            marker=dict(size=7, color=color),
        ))

    style_fig(fig_curve, "", height=380)
    fig_curve.update_layout(
        xaxis_title="Contract Month",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    st.plotly_chart(fig_curve, use_container_width=True)

    st.markdown("---")

    # ── Momentum Chart ──
    st.markdown("### Price Momentum")
    st.markdown(
        "**What this shows:** The blue line is the actual daily price. The two dashed "
        "lines are **moving averages** — they smooth out the noise to reveal the trend:\n\n"
        "- **50-day average (green):** The short-term trend — where prices have been heading "
        "over roughly the last 2 months.\n"
        "- **200-day average (orange):** The long-term trend — the general direction over "
        "roughly the last 10 months.\n\n"
        "**How to read it:** When the 50-day is **above** the 200-day, the short-term "
        "trend is stronger than the long-term trend — prices have been rising and "
        "momentum is upward. When it's **below**, prices have been weakening. This "
        "doesn't predict the future, but it tells you whether the current price "
        "movement is with or against the broader trend."
    )

    n_products = len([p for p in forecast_products if p in forecast_results])
    if n_products > 0:
        mom_cols = st.columns(min(n_products, 3))

        for idx, product in enumerate(forecast_products):
            if product not in forecast_results:
                continue
            col_name = f"{product}|{forecast_tenor}"
            if col_name not in df.columns:
                continue

            sub = df[["Date", col_name]].dropna().copy()
            sub["MA50"] = sub[col_name].rolling(50).mean()
            sub["MA200"] = sub[col_name].rolling(200).mean()
            tail = sub.tail(252)

            ma50_now = tail["MA50"].iloc[-1]
            ma200_now = tail["MA200"].iloc[-1]

            if ma50_now > ma200_now:
                signal = "📈 Upward"
                signal_color = "#81C784"
            else:
                signal = "📉 Downward"
                signal_color = "#E57373"

            with mom_cols[idx % 3]:
                st.markdown(f"**{product}** — Momentum: "
                            f"<span style='color:{signal_color}'>{signal}</span>",
                            unsafe_allow_html=True)
                st.caption(f"50d: ${ma50_now:,.2f}  |  200d: ${ma200_now:,.2f}")

                fig_mom = go.Figure()
                fig_mom.add_trace(go.Scatter(
                    x=tail["Date"], y=tail[col_name],
                    name="Price", line=dict(color="#4FC3F7", width=2),
                ))
                fig_mom.add_trace(go.Scatter(
                    x=tail["Date"], y=tail["MA50"],
                    name="50d MA", line=dict(color="#81C784", width=1.5, dash="dash"),
                ))
                fig_mom.add_trace(go.Scatter(
                    x=tail["Date"], y=tail["MA200"],
                    name="200d MA", line=dict(color="#FF8A65", width=1.5, dash="dash"),
                ))
                style_fig(fig_mom, "", height=280)
                fig_mom.update_layout(
                    margin=dict(t=10, b=30),
                    showlegend=(idx == 0),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                xanchor="left", x=0),
                )
                st.plotly_chart(fig_mom, use_container_width=True)

    st.markdown("---")

    # ── Market context panel ──
    st.markdown("### Market Context")
    st.caption(
        "Quick check for each product: is the forward curve in **contango** "
        "(front < back, typically bearish / oversupplied) or **backwardation** "
        "(front > back, typically bullish / tight supply)? And is the current "
        "price above or below where it usually sits at this time of year?"
    )

    ctx_cols = st.columns(max(len(forecast_products), 1))
    for idx, product in enumerate(forecast_products):
        if product not in forecast_results:
            continue
        m1_col = f"{product}|M1"
        m6_col = f"{product}|M6"
        spot_col = f"{product}|{forecast_tenor}"

        with ctx_cols[idx]:
            st.markdown(f"**{product}**")

            # Curve shape
            if m1_col in df.columns and m6_col in df.columns:
                m1_p = df[m1_col].iloc[-1]
                m6_p = df[m6_col].iloc[-1]
                spread = m1_p - m6_p
                if spread > 1:
                    st.markdown(f"📈 **Backwardation** (M1–M6: +${spread:.2f})")
                    st.caption("Front > back — usually means tight supply.")
                elif spread < -1:
                    st.markdown(f"📉 **Contango** (M1–M6: ${spread:.2f})")
                    st.caption("Front < back — usually means oversupply.")
                else:
                    st.markdown(f"➡️ **Flat** (M1–M6: ${spread:+.2f})")
                    st.caption("No strong curve signal.")

            # vs seasonal norm
            if spot_col in df.columns:
                sub = df[["Date", spot_col]].dropna().copy()
                sub["DayOfYear"] = sub["Date"].dt.dayofyear
                sub["Year"] = sub["Date"].dt.year
                seasonal_now = sub[sub["Year"].isin(range_years)].groupby("DayOfYear")[spot_col].mean()
                norm_price = seasonal_now.get(current_doy, np.nan)
                actual = forecast_results[product]["current"]
                if not np.isnan(norm_price) and norm_price != 0:
                    diff_pct = (actual - norm_price) / norm_price * 100
                    if diff_pct > 2:
                        st.markdown(f"🔺 **{diff_pct:+.1f}%** above seasonal norm")
                        st.caption("Price is higher than usual for this time of year.")
                    elif diff_pct < -2:
                        st.markdown(f"🔻 **{diff_pct:+.1f}%** below seasonal norm")
                        st.caption("Price is lower than usual for this time of year.")
                    else:
                        st.markdown(f"✅ **In line** with seasonal norm ({diff_pct:+.1f}%)")
                        st.caption("Price is tracking the typical seasonal pattern.")

    st.markdown("---")

    # ── Monthly forecast table ──
    st.markdown("### Monthly Forecast Table")
    st.caption("Estimated month-end prices based on the seasonal model, with the historical low–high range.")

    table_rows = []
    horizon_months = int(forecast_horizon.replace("M", ""))
    for m in range(1, horizon_months + 1):
        trade_day = min(m * 21, hz_days)
        row = {"Month": (current_date + pd.DateOffset(months=m)).strftime("%b %Y")}
        for product in forecast_products:
            if product in forecast_results:
                r = forecast_results[product]
                row[f"{product}"] = f"${r['fwd_avg'][trade_day]:,.2f}"
                row[f"{product} Low"] = f"${r['fwd_lo'][trade_day]:,.2f}"
                row[f"{product} High"] = f"${r['fwd_hi'][trade_day]:,.2f}"
        table_rows.append(row)

    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.info(
        "💡 **Note:** This forecast follows historical seasonal patterns only. It does "
        "not account for OPEC decisions, geopolitical events, demand shocks, or other "
        "market-moving fundamentals. Use it as a baseline to compare your own view against."
    )

# ─── Footer ────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Oil Barrel Dashboard · Data sourced from generated dummy prices · Built with Streamlit + Plotly")
