# 🛢️ Oil Barrel Price Dashboard

Interactive Streamlit dashboard for analyzing crude oil and petroleum product prices across the oil barrel.

## Features

| View | What it shows |
|------|--------------|
| **Price History** | Time-series of any product + tenor, plus live forward curve |
| **Seasonality** | Jan–Dec overlay comparing up to 5 years, with min/max range band and 5-year average |
| **Spreads** | Calendar spreads like M1–M2, M1–M3, etc. with spread seasonality |
| **Cracks** | Product vs crude differentials (e.g. Jet Fuel – Brent) with crack seasonality |

## Products Covered

- Brent Crude, WTI Crude
- Jet Fuel (Singapore), Gasoil 0.5% (Singapore)
- Naphtha (Singapore), Fuel Oil 380 (Singapore)
- VLSFO (Singapore), HSFO (Singapore)

Each product includes: **Spot, M1–M12, Q1–Q4** pricing.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate dummy data (or replace with your own Excel)
python generate_data.py

# 3. Launch dashboard
streamlit run app.py
```

## Data Format

The Excel file (`oil_barrel_prices.xlsx`) uses pipe-delimited column headers:

```
Date | Brent|Spot | Brent|M1 | Brent|M2 | ... | Jet Fuel (Sing)|Q4
```

To use your own data, match this column naming convention in the `Prices` sheet.

## Replacing with Real Data

1. Keep the same column format: `ProductName|Tenor`
2. Ensure a `Date` column with daily business dates
3. Save as `oil_barrel_prices.xlsx` in the same directory as `app.py`

## to run paste this: python -m streamlit run app.py