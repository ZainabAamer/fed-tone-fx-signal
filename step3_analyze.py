# STEP 3: does the hawkish/dovish score predict what EUR/USD does?
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

import os
os.makedirs("results", exist_ok=True)
sc = pd.read_csv("data/scores.csv", parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)
px = pd.read_csv("data/eurusd.csv", parse_dates=["Date"]).set_index("Date")["Close"]
sc["change"] = sc["score"].diff()  # markets react to CHANGES in tone

idx = px.index
rows = []
for _, r in sc.iterrows():
    d = r["Date"]
    pos = idx.searchsorted(d)              # first trading day on/after meeting date
    if pos < 1 or pos + 5 >= len(idx) or idx[pos] != d:
        continue
    usd_reaction = -(px.iloc[pos] / px.iloc[pos - 1] - 1)   # meeting day: USD move (USD up = EURUSD down)
    usd_drift = -(px.iloc[pos + 5] / px.iloc[pos] - 1)      # next 5 trading days after meeting day
    rows.append({"Date": d, "score": r["score"], "change": r["change"],
                 "usd_reaction": usd_reaction, "usd_drift": usd_drift})
df = pd.DataFrame(rows).dropna()
df.to_csv("results/event_table.csv", index=False)

out = []
def say(s):
    print(s); out.append(s)

say(f"Meetings analysed: {len(df)}  ({df['Date'].min().date()} to {df['Date'].max().date()})")
say("")
for label, col in [("SAME-DAY reaction (does the market agree with the AI score?)", "usd_reaction"),
                   ("NEXT-5-DAY drift (could you have traded on it?)", "usd_drift")]:
    p, pp = stats.pearsonr(df["change"], df[col])
    s, sp = stats.spearmanr(df["change"], df[col])
    hit = (np.sign(df["change"]) == np.sign(df[col]))[df["change"] != 0].mean()
    say(f"{label}")
    say(f"  Pearson correlation (score change vs USD move): {p:+.3f}  (p-value {pp:.3f})")
    say(f"  Spearman rank correlation:                      {s:+.3f}  (p-value {sp:.3f})")
    say(f"  Direction hit-rate (50% = coin flip):           {hit:.1%}")
    say("")

# Simple trading rule: after each statement, go long USD if tone got more hawkish, short USD if more dovish, hold 5 days
d2 = df[df["change"] != 0].copy()
d2["strat"] = np.sign(d2["change"]) * d2["usd_drift"]
mean, sd = d2["strat"].mean(), d2["strat"].std()
n = len(d2)
years = (d2["Date"].max() - d2["Date"].min()).days / 365.25
trades_per_year = n / years
sharpe = mean / sd * np.sqrt(trades_per_year) if sd > 0 else float("nan")
tstat = mean / sd * np.sqrt(n) if sd > 0 else float("nan")
tp = 2 * stats.t.sf(abs(tstat), n - 1)
say("SIMPLE RULE: long USD if tone more hawkish, short USD if more dovish, hold 5 trading days")
say(f"  Trades: {n} (~{trades_per_year:.1f} per year) | avg return per trade: {mean:.3%} | win rate: {(d2['strat'] > 0).mean():.1%}")
say(f"  Annualised Sharpe (approx): {sharpe:.2f} | t-stat of avg return: {tstat:.2f} (p-value {tp:.3f}; below 0.05 = statistically significant)")
say(f"  Cumulative return: {(1 + d2['strat']).prod() - 1:.1%} over {years:.1f} years")
open("results/summary.txt", "w").write("\n".join(out) + "\n")

fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
ax[0].scatter(df["change"], df["usd_reaction"] * 100, alpha=0.6)
m, b = np.polyfit(df["change"], df["usd_reaction"] * 100, 1)
xs = np.linspace(df["change"].min(), df["change"].max(), 50)
ax[0].plot(xs, m * xs + b, color="red")
ax[0].axhline(0, color="grey", lw=0.5); ax[0].axvline(0, color="grey", lw=0.5)
ax[0].set_xlabel("Change in AI hawkish score vs previous statement")
ax[0].set_ylabel("USD move on meeting day (%)")
ax[0].set_title("Does a more hawkish Fed tone lift the dollar?")
ax[1].plot(d2["Date"], (1 + d2["strat"]).cumprod())
ax[1].set_title("Rule: trade USD on tone change, 5-day hold")
ax[1].set_ylabel("Growth of 1")
plt.tight_layout()
plt.savefig("results/chart.png", dpi=150)
print("Saved results/chart.png, results/summary.txt, results/event_table.csv")
