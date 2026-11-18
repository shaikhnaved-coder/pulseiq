from db import get_connection
from pathlib import Path

import altair as alt
import duckdb
import pandas as pd
import streamlit as st

# Database sits at <project>/05_Starter/pulseiq.duckdb; this file is app/pages/AI_Signals.py
AI_LABEL = "AI-generated, for human review"


@st.cache_data
def q(sql: str) -> pd.DataFrame:
    con = get_connection()
    df = con.execute(sql).df()
    con.close()
    return df


def ai_label():
    st.warning(f"🤖 {AI_LABEL}", icon=None)


def inr_m(x: float) -> str:
    return f"₹{x / 1e6:,.2f} million"


st.title("AI signals")
st.caption(
    "Anomaly flags and forecasts produced by AI models. They are leads for people "
    "to check, not proof and not decisions."
)

# ------------------------------------------------------------------
# 1. Anomalies by type, biggest money first
# ------------------------------------------------------------------
an = q("SELECT * FROM metrics.v_ai_anomaly_by_type")
paid = an[an["records_with_money"] > 0].copy()          # already sorted, money biggest first
nomoney = an[an["records_with_money"] == 0].copy()

total_flagged = int(an["flagged_records"].sum())
total_money = float(an["money_at_risk"].sum())          # NULLs are skipped, not counted as 0
no_money_n = int(an["records_without_money"].sum())

c1, c2, c3 = st.columns(3)
c1.metric("Flagged records", f"{total_flagged:,}")
c2.metric("Money at risk (payroll flags)", inr_m(total_money))
c3.metric("Flags with no rupee value", f"{no_money_n:,}")

st.subheader("Anomalies by type: money at risk")
ai_label()

left, right = st.columns([2, 1])
with left:
    bars = (
        alt.Chart(paid)
        .mark_bar()
        .encode(
            y=alt.Y("reason_code:N", sort="-x", title=None, axis=alt.Axis(labelLimit=300)),
            x=alt.X("money_at_risk:Q", title="Money at risk (₹)"),
            tooltip=[
                alt.Tooltip("reason_code:N", title="Type"),
                alt.Tooltip("flagged_records:Q", title="Flagged records"),
                alt.Tooltip("money_at_risk:Q", title="Money at risk (₹)", format=",.0f"),
                alt.Tooltip("avg_score:Q", title="Avg anomaly score"),
            ],
        )
        .properties(height=300, padding={"left": 20, "right": 10, "top": 5, "bottom": 5})
    )
    st.altair_chart(bars, use_container_width=True)

with right:
    top = paid.iloc[0]
    top2_share = 100 * paid.head(2)["money_at_risk"].sum() / total_money
    st.markdown("**What this means**")
    st.markdown(
        f"The AI flagged **{int(paid['flagged_records'].sum())} payslips** as unusual, "
        f"with an estimated **{inr_m(total_money)}** at risk. "
        f"The biggest type is **{top['reason_code']}** "
        f"({inr_m(top['money_at_risk'])}, {int(top['flagged_records'])} records). "
        f"The top two types make up about **{top2_share:.0f}%** of the money. "
        "'Money at risk' is the model's estimate of the exposure, not a confirmed loss. "
        "Someone in payroll should check the biggest cases first."
    )

st.markdown("**Attendance flags (no rupee value recorded)**")
st.caption(
    "The data contract says money at risk is blank for attendance rows, so these are "
    "shown as counts only. A blank is not the same as ₹0."
)
st.dataframe(
    nomoney[["reason_code", "flagged_records", "avg_score"]]
    .sort_values("flagged_records", ascending=False)
    .rename(columns={"reason_code": "Type", "flagged_records": "Flagged records",
                     "avg_score": "Avg anomaly score"}),
    hide_index=True,
    use_container_width=True,
)

st.divider()

# ------------------------------------------------------------------
# 2. Forecast vs actual with the 80% band
# ------------------------------------------------------------------
st.subheader("Forecast vs actual")
choice = st.radio(
    "Metric",
    ["Headcount (people)", "Monthly attrition (%)"],
    horizontal=True,
)
if choice.startswith("Headcount"):
    fdf = q("SELECT * FROM metrics.v_ai_forecast_headcount")
    unit, dec, ytitle = "people", 1, "Headcount (people)"
else:
    fdf = q("SELECT * FROM metrics.v_ai_forecast_attrition")
    unit, dec, ytitle = "%", 2, "Monthly attrition (%)"

fdf["month_start_date"] = pd.to_datetime(fdf["month_start_date"])
fdf = fdf[fdf["month_start_date"] >= "2024-01-01"].copy()

ai_label()
left, right = st.columns([2, 1])
with left:
    x = alt.X("month_start_date:T", title="Month")
    y_scale = alt.Scale(zero=False)
    band = (
        alt.Chart(fdf).mark_area(opacity=0.25, color="#4c78a8")
        .encode(x=x, y=alt.Y("lower_80:Q", scale=y_scale, title=ytitle), y2="upper_80:Q")
    )
    actual_line = (
        alt.Chart(fdf).mark_line(point=True, color= "#ff9f1c")
        .encode(
            x=x, y=alt.Y("actual:Q", scale=y_scale, title=ytitle),
            tooltip=[alt.Tooltip("month_start_date:T", title="Month"),
                     alt.Tooltip("actual:Q", title="Actual")],
        )
    )
    fc_line = (
        alt.Chart(fdf).mark_line(point=True, color="#4c78a8", strokeDash=[6, 4])
        .encode(
            x=x, y=alt.Y("forecast_value:Q", scale=y_scale, title=ytitle),
            tooltip=[alt.Tooltip("month_start_date:T", title="Month"),
                     alt.Tooltip("forecast_value:Q", title="AI forecast"),
                     alt.Tooltip("lower_80:Q", title="Lower 80%"),
                     alt.Tooltip("upper_80:Q", title="Upper 80%")],
        )
    )
    st.altair_chart((band + actual_line + fc_line).properties(height=340),
                    use_container_width=True)
    st.caption("Solid orange line = actual. Dashed blue line = AI forecast. "
               "Shaded area = 80% range.")

with right:
    last_act = fdf.dropna(subset=["actual"]).iloc[-1]
    fc_only = fdf.dropna(subset=["forecast_value"])
    first_fc, last_fc = fc_only.iloc[0], fc_only.iloc[-1]
    st.markdown("**What this means**")
    st.markdown(
        f"The last month with real data is **{last_act['month_start_date']:%b %Y}** "
        f"({last_act['actual']:.{dec}f} {unit}). The AI forecasts "
        f"**{first_fc['forecast_value']:.{dec}f}** for {first_fc['month_start_date']:%b %Y} "
        f"and **{last_fc['forecast_value']:.{dec}f}** for {last_fc['month_start_date']:%b %Y}. "
        "The shaded band is the 80% range: if the model is reliable, the real value "
        "should land inside it about 8 months out of 10. "
        f"The band for {last_fc['month_start_date']:%b %Y} runs from "
        f"{last_fc['lower_80']:.{dec}f} to {last_fc['upper_80']:.{dec}f}, so treat the "
        "point forecast as a rough guide."
    )
    if choice.startswith("Headcount"):
        st.markdown(
            f"Note: the first forecast ({first_fc['forecast_value']:.1f}) starts below "
            f"the last actual ({last_act['actual']:.0f}), because the simple trend "
            "model does not follow the recent jump. Be careful with the early months."
        )

st.divider()

# ------------------------------------------------------------------
# 3. Forecast error
# ------------------------------------------------------------------
st.subheader("Forecast error")
ai_label()

st.markdown("**A. The AI's published forecast (Oct 2026 to Mar 2027)**")
err = q("SELECT * FROM metrics.v_ai_forecast_error")
if err.empty:
    st.info(
        "No error can be calculated yet. The forecast covers Oct 2026 to Mar 2027, "
        "but actual data ends in Sep 2026, so there are no months where both a "
        "forecast and an actual exist. This table fills in automatically once "
        "actuals for those months arrive."
    )
else:
    st.dataframe(err, hide_index=True, use_container_width=True)

st.markdown("**B. Backtest on months where actuals are known (Apr to Sep 2026)**")
st.caption(
    "Our own check, not the AI's published forecast. We used the same kind of method "
    "(trained only on data up to Mar 2026) and compared it with what really happened. "
    "It shows how reliable this style of forecast has been."
)
bt = q("SELECT * FROM metrics.ai_backtest ORDER BY metric, month_start_date")
bt["month_start_date"] = pd.to_datetime(bt["month_start_date"]).dt.strftime("%b %Y")
bt["inside_80"] = bt["inside_80"].map({True: "Yes", False: "No"}).fillna("n/a")
hc = bt[bt["metric"] == "headcount_end"]
at = bt[bt["metric"] == "attrition_rate_monthly_pct"]

m1, m2, m3 = st.columns(3)
m1.metric("Headcount error (MAPE)", f"{hc['abs_pct_error'].mean():.2f}%")
m2.metric("Headcount average miss", f"{hc['abs_error'].mean():.1f} people")
m3.metric("Attrition average miss", f"{at['abs_error'].mean():.2f} percentage points")

cols = {"month_start_date": "Month", "forecast": "Forecast", "lower_80": "Lower 80%",
        "upper_80": "Upper 80%", "actual": "Actual", "error": "Error (forecast − actual)",
        "abs_error": "Absolute error", "abs_pct_error": "Absolute error %",
        "inside_80": "Actual inside 80% range?"}
t1, t2 = st.columns(2)
with t1:
    st.markdown("Headcount")
    st.dataframe(hc[list(cols)].rename(columns=cols), hide_index=True,
                 use_container_width=True)
with t2:
    st.markdown("Monthly attrition (%)")
    st.dataframe(at[list(cols)].drop(columns=["lower_80", "upper_80", "inside_80"])
                 .rename(columns=cols), hide_index=True, use_container_width=True)

inside = int((hc["inside_80"] == "Yes").sum())
st.markdown(
    f"**What this means:** in the backtest, headcount was off by about "
    f"**{hc['abs_pct_error'].mean():.1f}%** on average ({hc['abs_error'].mean():.1f} people), "
    f"and the real number fell inside the 80% range in **{inside} of {len(hc)}** months. "
    f"Attrition was off by about **{at['abs_error'].mean():.2f} percentage points** a month. "
    "Attrition is only around 1% a month, so even a small gap looks large as a "
    "percentage, which is why it is shown in percentage points. "
    "Six months is a small test, so this is a rough guide to reliability, not a guarantee."
)