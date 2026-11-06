from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parents[2] / "05_Starter" / "pulseiq.duckdb"

st.set_page_config(page_title="Executive scorecard", layout="wide")


@st.cache_data
def load() -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute(
        "SELECT * FROM metrics.v_scorecard ORDER BY kpi_id, month_start_date"
    ).df()
    con.close()
    df["month_start_date"] = pd.to_datetime(df["month_start_date"])
    return df


COL = {"Green": "#2e9e5b", "Amber": "#e0a800", "Red": "#d64545", "Grey": "#888888"}

WHY = {
    "K1": "Shows whether the business earns enough to pay for everything else.",
    "K2": "One number for: are we making money on what we earn?",
    "K3": "Payroll is the biggest cost; this shows if people cost is outgrowing income.",
    "K4": "Profit means little if customers pay late; this is how long cash takes to arrive.",
    "K5": "Losing people is costly and hard to reverse; 12-month view because monthly is too noisy.",
    "K6": "Shows the capacity the company really has, and early morale problems.",
    "K7": "Shows whether planned work is being delivered (sample task feed).",
    "K8": "Overtime signals stretched capacity and extra cost.",
}

# detail page for each KPI: (url path, label). The url is the page file name,
# with spaces turned into underscores and without .py
LINKS = {
    "K1": ("/Expenses", "P&L and expenses"),
    "K2": ("/Expenses", "P&L and expenses"),
    "K3": ("/Payroll_cost", "Payroll cost"),
    "K4": ("/Recievable_Cash", "Receivables and cash"),
    "K5": ("/Attrition", "Attrition"),
    "K6": ("/Attendance_and_Leave", "Attendance and leave"),
    "K7": ("/Team_Productivity", "Team productivity"),
    "K8": ("/Budget_vs_Actual", "Budget vs actual"),
}


def fmt(k, v):
    if k == "K1":
        return f"₹{v / 1e6:,.2f} M"
    if k == "K4":
        return f"{v:.1f} days"
    return f"{v:.2f}%"


def fmt_change(k, c):
    if k == "K1":
        return f"{c / 1e6:+,.2f} M"
    if k == "K4":
        return f"{c:+.1f} days"
    return f"{c:+.2f} pts"


def spark(vals, color):
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    ys = [22 - (v - lo) / span * 20 for v in vals]
    pts = " ".join(f"{i * 100 / (len(vals) - 1):.1f},{y:.1f}" for i, y in enumerate(ys))
    return (
        '<svg width="100" height="24" viewBox="0 0 100 24" xmlns="http://www.w3.org/2000/svg">'
        f'<polyline fill="none" stroke="currentColor" stroke-width="1.6" points="{pts}"/>'
        f'<circle cx="100" cy="{ys[-1]:.1f}" r="2.5" fill="{color}"/></svg>'
    )


CSS = """
<style>
.sc-title {font-size: 1.6rem; font-weight: 700; margin: 0;}
.sc-sub {opacity: .75; font-size: .85rem; margin-bottom: .6rem;}
.sc-grid {display: grid; grid-template-columns: 1fr 1fr; gap: 10px;}
.sc-tile {border: 1px solid rgba(128,128,128,.5); border-radius: 8px; padding: 10px 12px; min-height: 200px; break-inside: avoid;}
.sc-head {display: flex; justify-content: space-between; align-items: center; font-weight: 600; font-size: .95rem;}
.sc-badge {display: inline-flex; align-items: center; gap: 6px; font-size: .75rem; font-weight: 700; letter-spacing: .04em;}
.sc-dot {width: 14px; height: 14px; border-radius: 50%; display: inline-block;}
.sc-value {font-size: 1.9rem; font-weight: 700; line-height: 1.15; margin-top: 4px;}
.sc-row {display: flex; justify-content: space-between; align-items: flex-end; gap: 8px;}
.sc-line {font-size: .8rem; opacity: .9;}
.sc-small {font-size: .68rem; opacity: .7; line-height: 1.3;}
.sc-why {font-size: .75rem; margin-top: 4px; line-height: 1.3;}
.sc-tile a {font-size: .75rem; font-weight: 600; text-decoration: underline;}
.sc-foot {font-size: .68rem; opacity: .8; margin-top: 10px; line-height: 1.4;}
@media print {
  @page {size: A4 portrait; margin: 8mm;}
  [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"],
  [data-testid="stSelectbox"], [data-testid="stCaptionContainer"], footer {display: none !important;}
  html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {background: #fff !important;}
  .block-container {padding: 0 !important; max-width: 100% !important;} [data-testid="stAppViewContainer"], [data-testid="stMain"], section.main, .stApp {overflow: visible !important; height: auto !important; position: static !important;}
  .sc-wrap, .sc-wrap * {color: #111 !important;}
  .sc-wrap {-webkit-print-color-adjust: exact; print-color-adjust: exact;}
  .sc-tile {height: 61mm; min-height: 0; overflow: hidden; border: 1px solid #999;}
  .sc-value {font-size: 1.6rem;}
  .sc-line {font-size: .72rem;}
  .sc-why {font-size: .7rem;} .sc-small {font-size: .62rem;}
}
</style>
"""
CSS = " ".join(CSS.split())

df = load()
months = [pd.Timestamp(m) for m in sorted(df["month_start_date"].unique(), reverse=True)]
sel = st.selectbox("Month", months, format_func=lambda d: d.strftime("%b %Y"))
st.caption("To print: press Ctrl+P and choose A4. This month picker and note are hidden on paper.")

cur = df[df["month_start_date"] == sel]
counts = cur["status"].value_counts()
g, a, rd = (int(counts.get(s, 0)) for s in ["Green", "Amber", "Red"])

tiles = []
for k in sorted(cur["kpi_id"].unique()):
    r = cur[cur["kpi_id"] == k].iloc[0]
    hist = df[(df["kpi_id"] == k) & (df["month_start_date"] <= sel)].tail(6)["value"].tolist()
    col = COL[r["status"]]

    ch = r["change"]
    if pd.isna(ch):
        trend, tcol = "first month in data", "#888888"
    elif abs(ch) < 0.005:
        trend, tcol = "▬ no change vs last month", "#888888"
    else:
        good = (ch > 0) == (r["direction"] == "higher")
        arrow = "▲" if ch > 0 else "▼"
        trend = f"{arrow} {fmt_change(k, ch)} vs last month"
        tcol = COL["Green"] if good else COL["Red"]

    label = "Benchmark" if str(r["target_source"]).startswith("Benchmark") else "Target"
    url, page_label = LINKS[k]
    tiles.append(
        '<div class="sc-tile">'
        f'<div class="sc-head"><span>{r["kpi_name"]}</span>'
        f'<span class="sc-badge"><span class="sc-dot" style="background:{col}"></span>{r["status"].upper()}</span></div>'
        f'<div class="sc-row"><div><div class="sc-value">{fmt(k, r["value"])}</div>'
        f'<div class="sc-line">{label}: {fmt(k, r["target"])} &nbsp;|&nbsp; <span style="color:{tcol}">{trend}</span></div></div>'
        f'<div>{spark(hist, col)}<div class="sc-small" style="text-align:right">last {len(hist)} months</div></div></div>'
        f'<div class="sc-why">{WHY[k]}</div>'
        f'<div class="sc-small">{r["target_source"]}<br>Source: {r["metric_id"]} · {r["metric_view"]}</div>'
        f'<div style="margin-top:4px"><a href="{url}" target="_self">Details: {page_label} →</a></div>'
        "</div>"
    )

foot = (
    "Status rule: Green = on or better than target. Amber = worse, but inside the tolerance band "
    "(revenue ₹5 M, margin 3 pts, payroll % 3 pts, DSO 5 days, attrition 2 pts, attendance 1.5 pts, "
    "task completion 5 pts, overtime 0.5 pts). Red = beyond the band. "
    "Targets for attrition (1% a month x 12), attendance, task completion and overtime come from kpi_targets. "
    "Revenue, margin, payroll % and DSO have no target in the data, so their benchmark is the company's "
    "own 18-month average, to be replaced by a finance target. "
    "Every value comes from metrics.v_scorecard, which reads only the metric views."
)

body = (
    '<div class="sc-wrap">'
    f'<div class="sc-title">Company health scorecard: {sel.strftime("%b %Y")}</div>'
    f'<div class="sc-sub">{g} green · {a} amber · {rd} red</div>'
    f'<div class="sc-grid">{"".join(tiles)}</div>'
    f'<div class="sc-foot">{foot}</div>'
    "</div>"
)
st.markdown(CSS + body, unsafe_allow_html=True)