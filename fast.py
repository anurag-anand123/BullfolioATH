import pandas as pd
import yfinance as yf
import mplfinance as mpf
import os
import shutil
from datetime import datetime, timedelta

# ==== COUNTRY SELECTION ====
country_choice = input("Select country (US / India): ").strip().lower()

if country_choice == "us":
    csv_file = "csv/us.csv"
    suffix = ""
elif country_choice == "india":
    csv_file = "csv/india.csv"
    suffix = ".NS"
else:
    print("Invalid choice! Please enter 'US' or 'India'.")
    exit()

# ==== Ask user for period & interval ====
print("Example periods: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'")
period_input = input("Enter chart period (e.g., 3d, 1mo, 6mo, 1y): ").strip()

print("\nExample intervals: '1m', '2m', '5m', '15m', '30m', '1h', '1d', '1wk', '1mo'")
interval_input = input("Enter chart interval (e.g., 1m, 5m, 1d): ").strip()

# ==== CONFIG ====
base_folder = "candlestick_charts"
os.makedirs(base_folder, exist_ok=True)

subfolder_name = f"graph_period{period_input}_interval{interval_input}"
output_folder = os.path.join(base_folder, subfolder_name)
if os.path.exists(output_folder):
    shutil.rmtree(output_folder)
os.makedirs(output_folder, exist_ok=True)

# ==== STYLE ====
binance_dark = {
    "base_mpl_style": "dark_background",
    "marketcolors": {
        "candle": {"up": "#3dc985", "down": "#ef4f60"},
        "edge": {"up": "#3dc985", "down": "#ef4f60"},
        "wick": {"up": "#3dc985", "down": "#ef4f60"},
        "ohlc": {"up": "green", "down": "red"},
        "volume": {"up": "#247252", "down": "#82333f"},
        "vcedge": {"up": "green", "down": "red"},
        "vcdopcod": False,
        "alpha": 1,
    },
    "mavcolors": ("#ad7739", "#a63ab2", "#62b8ba"),
    "facecolor": "#1b1f24",
    "gridcolor": "#2c2e31",
    "gridstyle": "--",
    "y_on_right": True,
    "rc": {
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.edgecolor": "#474d56",
        "axes.titlecolor": "red",
        "figure.facecolor": "#161a1e",
        "figure.titlesize": 10,
        "figure.titleweight": "semibold",
        "axes.labelsize": 5,
        "axes.titlesize": 8,
        "xtick.labelsize": 5,
        "ytick.labelsize": 5,
    },
    "base_mpf_style": "binance-dark",
}

# ==== READ TICKERS ====
df_symbols = pd.read_csv(csv_file)
tickers = [str(sym).strip() + suffix for sym in df_symbols["Symbol"].dropna().unique()]
limit_from_top = int(input("Enter the number of top stocks to process: Top ").strip())
tickers = tickers[:limit_from_top]

# ==== DOWNLOAD ALL DATA AT ONCE (FULL HISTORY) ====
print(f"Downloading full history for {len(tickers)} stocks...")
full_data = yf.download(tickers, period="max", interval="1d", group_by='ticker', threads=True, progress=False)

# ==== Calculate ATH and filter ====
results = []
for ticker in tickers:
    try:
        hist_full = full_data[ticker].dropna()
        if hist_full.empty:
            continue

        all_time_high = hist_full["Close"].max()
        current_price = hist_full["Close"].iloc[-1]
        pct_from_ath = (all_time_high - current_price) / all_time_high * 100

        results.append({
            "Ticker": ticker,
            "Pct_from_ATH": pct_from_ath
        })
    except Exception:
        continue

# Sort by % from ATH
results_sorted = sorted(results, key=lambda x: x["Pct_from_ATH"])

# ==== DOWNLOAD ONLY NEEDED PERIOD & INTERVAL DATA ====
needed_tickers = [r["Ticker"] for r in results_sorted]
print(f"Downloading chart data for {len(needed_tickers)} stocks...")
chart_data = yf.download(needed_tickers, period=period_input, interval=interval_input, group_by='ticker', threads=True, progress=False)

# ==== PLOT ====
for i, stock_data in enumerate(results_sorted, start=1):
    ticker = stock_data["Ticker"]

    try:
        hist = chart_data[ticker].dropna()
        hist = hist.astype(float, errors="ignore")  # Ensure numeric
        if hist.empty:
            continue

        save_path = os.path.join(output_folder, f"graph{i}_{ticker}.png")
        title = f"{ticker} (Pct from ATH: {stock_data['Pct_from_ATH']:.2f}%)"

        mpf.plot(
            hist,
            type='candle',
            style=binance_dark,
            title=title,
            ylabel='Price',
            savefig=dict(fname=save_path, dpi=300, bbox_inches='tight'),
            figratio=(20, 9),
            figscale=0.8
        )
        print(f"Saved chart: {save_path}")
    except Exception as e:
        print(f"Error plotting {ticker}: {e}")

print(f"✅ Saved {len(results_sorted)} candlestick charts to '{output_folder}'")

# ==== Open folder automatically ====
import sys
import subprocess
try:
    if os.name == 'nt':
        os.startfile(output_folder)
    elif os.name == 'posix':
        if sys.platform == "darwin":
            subprocess.run(["open", output_folder])
        else:
            subprocess.run(["xdg-open", output_folder])
except Exception as e:
    print(f"Could not open folder automatically: {e}")
