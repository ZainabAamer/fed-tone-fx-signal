# STEP 1: download Fed statements + EUR/USD prices
import os
import pandas as pd
import yfinance as yf

os.makedirs("data", exist_ok=True)
os.makedirs("results", exist_ok=True)
URL = "https://raw.githubusercontent.com/vtasca/fed-statement-scraping/master/communications.csv"

print("Downloading Fed statements...")
df = pd.read_csv(URL)
st = df[df["Type"].str.lower() == "statement"][["Date", "Text"]].copy()
st["Date"] = pd.to_datetime(st["Date"])
st = st.sort_values("Date").reset_index(drop=True)
st.to_csv("data/statements.csv", index=False)
print(f"Saved {len(st)} statements ({st['Date'].min().date()} to {st['Date'].max().date()})")

print("Downloading EUR/USD prices...")
px = yf.download("EURUSD=X", start="2003-01-01", auto_adjust=True, progress=False)
if isinstance(px.columns, pd.MultiIndex):
    px.columns = px.columns.get_level_values(0)
px = px[["Close"]].dropna()
px.index = pd.to_datetime(px.index).tz_localize(None)
px.index.name = "Date"
px.to_csv("data/eurusd.csv")
print(f"Saved {len(px)} daily prices ({px.index.min().date()} to {px.index.max().date()})")
print("DONE. Step 1 complete.")
