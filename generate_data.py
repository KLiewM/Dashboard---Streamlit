"""
Generate dummy historical oil barrel price data (2020-2025) and save to Excel.
Products: Brent, WTI, Jet Fuel (Sing), Gasoil 0.5% (Sing), Naphtha (Sing), 
          Fuel Oil 380 (Sing), VLSFO (Sing), HSFO (Sing)
Each product gets: Spot, M1-M12, Q1-Q4
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)

PRODUCTS = {
    "Brent": {"base": 65, "vol": 0.25, "season_amp": 5},
    "WTI": {"base": 62, "vol": 0.25, "season_amp": 5},
    "Jet Fuel (Sing)": {"base": 80, "vol": 0.28, "season_amp": 8},
    "Gasoil 0.5% (Sing)": {"base": 78, "vol": 0.26, "season_amp": 7},
    "Naphtha (Sing)": {"base": 55, "vol": 0.30, "season_amp": 6},
    "Fuel Oil 380 (Sing)": {"base": 45, "vol": 0.28, "season_amp": 4},
    "VLSFO (Sing)": {"base": 60, "vol": 0.27, "season_amp": 5},
    "HSFO (Sing)": {"base": 40, "vol": 0.30, "season_amp": 4},
}

start = datetime(2020, 1, 2)
end = datetime(2025, 12, 31)
dates = pd.bdate_range(start, end)

def generate_price_series(base, vol, season_amp, n):
    prices = np.zeros(n)
    prices[0] = base
    daily_vol = vol / np.sqrt(252)
    trend_shift = {
        0: 0, 300: 0.0003, 500: -0.0001, 750: 0.0004,
        1000: -0.0002, 1200: 0.0001, 1400: -0.0003
    }
    current_drift = 0
    for i in range(1, n):
        for t, d in trend_shift.items():
            if i == t:
                current_drift = d
        day_of_year = (i % 252) / 252 * 2 * np.pi
        seasonal = season_amp * np.sin(day_of_year) / prices[i-1]
        shock = np.random.normal(current_drift + seasonal * 0.01, daily_vol)
        prices[i] = prices[i-1] * (1 + shock)
        prices[i] = max(prices[i], base * 0.3)
    return prices

n = len(dates)
all_data = {"Date": dates}

for product, params in PRODUCTS.items():
    spot = generate_price_series(params["base"], params["vol"], params["season_amp"], n)
    all_data[f"{product}|Spot"] = np.round(spot, 2)
    for m in range(1, 13):
        contango = np.random.uniform(0.2, 0.8) * m
        noise = np.random.normal(0, 0.3, n)
        all_data[f"{product}|M{m}"] = np.round(spot + contango + noise, 2)
    for q in range(1, 5):
        avg_m = int(q * 3)
        contango = np.random.uniform(0.5, 1.5) * q
        noise = np.random.normal(0, 0.5, n)
        all_data[f"{product}|Q{q}"] = np.round(spot + contango + noise, 2)

df = pd.DataFrame(all_data)
output_path = "oil_barrel_prices.xlsx"

with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
    df.to_excel(writer, sheet_name="Prices", index=False)
    wb = writer.book
    ws = writer.sheets["Prices"]
    header_fmt = wb.add_format({
        "bold": True, "bg_color": "#1B3A5C", "font_color": "#FFFFFF",
        "border": 1, "text_wrap": True, "align": "center", "font_size": 9
    })
    for col_num, col_name in enumerate(df.columns):
        ws.write(0, col_num, col_name, header_fmt)
        ws.set_column(col_num, col_num, 14 if col_num == 0 else 12)
    ws.freeze_panes(1, 1)
    ws.autofilter(0, 0, len(df), len(df.columns) - 1)

    meta = pd.DataFrame({
        "Product": list(PRODUCTS.keys()),
        "Base Price ($/bbl)": [p["base"] for p in PRODUCTS.values()],
        "Annualized Vol": [p["vol"] for p in PRODUCTS.values()],
        "Seasonal Amplitude": [p["season_amp"] for p in PRODUCTS.values()],
    })
    meta.to_excel(writer, sheet_name="Metadata", index=False)

print(f"Generated {output_path}: {df.shape[0]} rows x {df.shape[1]} columns")
print(f"Products: {list(PRODUCTS.keys())}")
print(f"Date range: {dates[0].date()} to {dates[-1].date()}")
