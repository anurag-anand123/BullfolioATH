import pandas as pd
import yfinance as yf
import mplfinance as mpf
import os
import shutil

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

# Create subfolder based on period & interval
subfolder_name = f"graph_period{period_input}_interval{interval_input}"
output_folder = os.path.join(base_folder, subfolder_name)
if os.path.exists(output_folder):
    shutil.rmtree(output_folder)
os.makedirs(output_folder, exist_ok=True)

# Binance Dark Theme
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

# ==== Read tickers ====
df_symbols = pd.read_csv(csv_file)
tickers = [str(sym).strip() + suffix for sym in df_symbols["Symbol"].dropna().unique()]
limit_from_top = int(input("Enter the number of top stocks to process: Top ").strip())
tickers = tickers[:limit_from_top]

results = []

for ticker in tickers:
    try:
        stock = yf.Ticker(ticker)

        # Full history for ATH
        hist_full = stock.history(period="max", interval="1d")
        if hist_full.empty:
            print(f"No historical data for {ticker}")
            continue

        all_time_high = hist_full["Close"].max()
        current_price = hist_full["Close"].dropna().iloc[-1]
        pct_from_ath = (all_time_high - current_price) / all_time_high * 100

        # User-specified period & interval for plotting
        hist_custom = stock.history(period=period_input, interval=interval_input)
        if hist_custom.empty:
            print(f"No chart data for {ticker} ({period_input}, {interval_input})")
            continue

        results.append({
            "Ticker": ticker,
            "Pct_from_ATH": pct_from_ath,
            "Hist": hist_custom
        })

    except Exception as e:
        print(f"Error processing {ticker}: {e}")

# Sort by % from ATH
results_sorted = sorted(results, key=lambda x: x["Pct_from_ATH"])

# Plot & save charts
for i, stock_data in enumerate(results_sorted, start=1):
    ticker = stock_data["Ticker"]
    hist = stock_data["Hist"]

    save_path = os.path.join(output_folder, f"graph{i}_{ticker}.png")
    title = f"{ticker} (Pct from ATH: {stock_data['Pct_from_ATH']:.2f}%)"

    try:
        mpf.plot(
            hist,
            type='candle',
            style=binance_dark,
            title=title,
            ylabel='Price',
            savefig=dict(fname=save_path, dpi=300, bbox_inches='tight'),
            figratio=(20, 9),
            figscale=0.8,
        )
        print(f"Saved chart: {save_path}")
    except Exception as e:
        print(f"Error plotting {ticker}: {e}")

print(f"✅ Saved {len(results_sorted)} candlestick charts to '{output_folder}'")
