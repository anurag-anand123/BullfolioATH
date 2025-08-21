import pandas as pd
import yfinance as yf
import mplfinance as mpf
import os
import shutil
from datetime import datetime, timedelta
import sys
import subprocess
import math

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

# ==== STYLE (omitted for brevity, no changes here) ====
binance_dark = {
    "base_mpl_style": "dark_background", "marketcolors": {"candle": {"up": "#3dc985", "down": "#ef4f60"},"edge": {"up": "#3dc985", "down": "#ef4f60"},"wick": {"up": "#3dc985", "down": "#ef4f60"},"ohlc": {"up": "green", "down": "red"},"volume": {"up": "#247252", "down": "#82333f"},"vcedge": {"up": "green", "down": "red"},"vcdopcod": False,"alpha": 1,},"mavcolors": ("#ad7739", "#a63ab2", "#62b8ba"),"facecolor": "#1b1f24","gridcolor": "#2c2e31","gridstyle": "--","y_on_right": True,"rc": {"axes.grid": True,"axes.grid.axis": "y","axes.edgecolor": "#474d56","axes.titlecolor": "red","figure.facecolor": "#161a1e","figure.titlesize": 10,"figure.titleweight": "semibold","axes.labelsize": 5,"axes.titlesize": 8,"xtick.labelsize": 5,"ytick.labelsize": 5,},"base_mpf_style": "binance-dark",
}


# ==== BATCH DOWNLOAD FUNCTION (MODIFIED) ====
def download_in_batches(tickers_list, batch_size=200, **kwargs):
    """Downloads yfinance data in batches and combines into a single DataFrame."""
    all_data_frames = []
    total_batches = math.ceil(len(tickers_list) / batch_size)
    
    for i in range(0, len(tickers_list), batch_size):
        batch = tickers_list[i:i + batch_size]
        print(f"Downloading batch {i//batch_size + 1}/{total_batches}...")
        batch_data = yf.download(batch, **kwargs)
        all_data_frames.append(batch_data)
        
    # Combine all batch DataFrames horizontally
    if not all_data_frames:
        return pd.DataFrame()
    return pd.concat(all_data_frames, axis=1)


# ==== READ TICKERS ====
df_symbols = pd.read_csv(csv_file)
tickers = [str(sym).strip() + suffix for sym in df_symbols["Symbol"].dropna().unique()]
limit_from_top = int(input("Enter the number of top stocks to process: Top ").strip())
tickers = tickers[:limit_from_top]

# ==== DOWNLOAD ALL DATA (FULL HISTORY) - MODIFIED ====
print(f"Downloading full history for {len(tickers)} stocks...")
# We remove group_by='ticker' to get a single DataFrame with MultiIndex columns
full_data = download_in_batches(
    tickers,
    period="max",
    interval="1d",
    threads=True,
    progress=False
)

# ==== Calculate ATH and filter (MODIFIED) ====
results = []
# Get a list of unique tickers that were successfully downloaded
downloaded_tickers = full_data.columns.get_level_values(1).unique()

for ticker in downloaded_tickers:
    try:
        # Extract data for a single ticker from the main DataFrame
        # The columns will be ('Close', 'TICKER'), ('Open', 'TICKER'), etc.
        hist_full = full_data.loc[:, (slice(None), ticker)]
        # Remove the top-level index ('TICKER') to simplify column names
        hist_full.columns = hist_full.columns.droplevel(1)
        hist_full = hist_full.dropna()
        
        if hist_full.empty:
            continue

        all_time_high = hist_full["Close"].max()
        current_price = hist_full["Close"].iloc[-1]
        pct_from_ath = (all_time_high - current_price) / all_time_high * 100

        results.append({
            "Ticker": ticker,
            "Pct_from_ATH": pct_from_ath
        })
    except Exception as e:
        # print(f"Could not process ATH for {ticker}: {e}") # You can uncomment this for debugging
        continue

# Sort by % from ATH
results_sorted = sorted(results, key=lambda x: x["Pct_from_ATH"])
if not results_sorted:
    print("No valid data found for any tickers. Exiting.")
    exit()

# ==== DOWNLOAD CHART DATA - MODIFIED ====
needed_tickers = [r["Ticker"] for r in results_sorted]
print(f"Downloading chart data for {len(needed_tickers)} stocks...")
chart_data = download_in_batches(
    needed_tickers,
    period=period_input,
    interval=interval_input,
    threads=True,
    progress=False
)

# ==== PLOT (MODIFIED) ====
plot_count = 0
for i, stock_data in enumerate(results_sorted, start=1):
    ticker = stock_data["Ticker"]

    try:
        # Extract and clean data for plotting, same as before
        hist = chart_data.loc[:, (slice(None), ticker)]
        hist.columns = hist.columns.droplevel(1)
        hist = hist.dropna()
        hist = hist.astype(float, errors="ignore")
        
        if hist.empty:
            continue

        save_path = os.path.join(output_folder, f"graph{i}_{ticker}.png")
        title = f"{ticker} (Pct from ATH: {stock_data['Pct_from_ATH']:.2f}%)"

        mpf.plot(
            hist, type='candle', style=binance_dark, title=title,
            ylabel='Price', savefig=dict(fname=save_path, dpi=300, bbox_inches='tight'),
            figratio=(20, 9), figscale=0.8
        )
        print(f"Saved chart: {save_path}")
        plot_count += 1
    except Exception as e:
        print(f"Error plotting {ticker}: {e}")

print(f"✅ Saved {plot_count} candlestick charts to '{output_folder}'")

# ==== Open folder automatically (omitted for brevity, no changes here) ====
try:
    if os.name == 'nt': os.startfile(output_folder)
    elif os.name == 'posix':
        if sys.platform == "darwin": subprocess.run(["open", output_folder])
        else: subprocess.run(["xdg-open", output_folder])
except Exception as e:
    print(f"Could not open folder automatically: {e}")