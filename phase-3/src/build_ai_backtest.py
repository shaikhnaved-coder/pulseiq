import duckdb
import numpy as np
import pandas as pd

con = duckdb.connect("05_Starter/pulseiq.duckdb")

# Company totals per month (sum over all departments, D00 included)
df = con.execute("""
    SELECT month_start_date,
           SUM(headcount_end)   AS hc,
           SUM(exits)           AS ex,
           SUM(headcount_start) AS hs
    FROM wh.fact_headcount_monthly
    GROUP BY 1 ORDER BY 1
""").df()
df["month_start_date"] = pd.to_datetime(df["month_start_date"])
df["attr"] = 100.0 * df["ex"] / df["hs"]
df["mon"] = df["month_start_date"].dt.month

CUTOFF = pd.Timestamp("2026-03-01")   # we pretend we are standing here
LAST = pd.Timestamp("2026-09-01")     # last month with actuals
Z80 = 1.2816                          # multiplier for an 80% range

# --- Headcount: 36-month linear trend + half-strength seasonality ---
train = df[df["month_start_date"] <= CUTOFF].tail(36).reset_index(drop=True)
x = np.arange(len(train))
slope, intercept = np.polyfit(x, train["hc"], 1)
trend = intercept + slope * x
resid = train["hc"] - trend
seas = resid.groupby(train["mon"]).mean()          # usual swing per calendar month
fitted = trend + 0.5 * train["mon"].map(seas)
sd = float(np.std(train["hc"] - fitted, ddof=2))   # typical miss in training

test = df[(df["month_start_date"] > CUTOFF) & (df["month_start_date"] <= LAST)]
rows = []
for i, (_, r) in enumerate(test.iterrows()):
    f = intercept + slope * (len(train) + i) + 0.5 * seas[r["mon"]]
    lo, hi = f - Z80 * sd, f + Z80 * sd
    act = float(r["hc"])
    rows.append(dict(
        metric="headcount_end", month_start_date=r["month_start_date"].date(),
        forecast=round(f, 1), lower_80=round(lo, 1), upper_80=round(hi, 1),
        actual=act, error=round(f - act, 2), abs_error=round(abs(f - act), 2),
        abs_pct_error=round(100 * abs(f - act) / act, 2),
        inside_80=bool(lo <= act <= hi)))

# --- Attrition %: same-month average of the last 3 years (no range) ---
for _, r in test.iterrows():
    past = df[(df["mon"] == r["mon"]) & (df["month_start_date"] < r["month_start_date"])].tail(3)
    f = float(past["attr"].mean())
    act = float(r["attr"])
    rows.append(dict(
        metric="attrition_rate_monthly_pct", month_start_date=r["month_start_date"].date(),
        forecast=round(f, 2), lower_80=None, upper_80=None,
        actual=round(act, 2), error=round(f - act, 2), abs_error=round(abs(f - act), 2),
        abs_pct_error=round(100 * abs(f - act) / act, 2) if act else None,
        inside_80=None))

bt = pd.DataFrame(rows)
bt["method_note"] = "Own backtest trained through 2026-03, not the AI's published forecast"

con.register("bt_df", bt)
con.execute("CREATE OR REPLACE TABLE metrics.ai_backtest AS SELECT * FROM bt_df")
bt.to_csv("docs/forecast_error_backtest.csv", index=False)

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
print(bt.drop(columns=["method_note"]).to_string(index=False))

h = bt[bt["metric"] == "headcount_end"]
a = bt[bt["metric"] == "attrition_rate_monthly_pct"]
print("\nHEADCOUNT: MAPE %.2f%%, mean abs error %.1f people, %d of %d inside 80%% range"
      % (h["abs_pct_error"].mean(), h["abs_error"].mean(),
         int(h["inside_80"].sum()), len(h)))
print("ATTRITION: mean abs error %.2f percentage points over %d months"
      % (a["abs_error"].mean(), len(a)))
print("Training months: %s to %s" % (train["month_start_date"].min().date(),
                                     train["month_start_date"].max().date()))
print("Saved: metrics.ai_backtest and docs/forecast_error_backtest.csv")