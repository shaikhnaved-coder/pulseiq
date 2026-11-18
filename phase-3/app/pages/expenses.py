from db import get_connection
from pathlib import Path
import duckdb
import pandas as pd
import streamlit as st


@st.cache_data
def load(sql, params=None):
    con = get_connection()
    df = con.execute(sql, params or []).df()
    con.close()
    return df

def inr(x):
    return f"{x:,.0f}"

st.title("P&L and Expense Analytics")
st.caption("Source: fact_ledger, detail accounts only (group headings 4000 and 5000 are never counted). Amounts in INR.")

pnl = load("select * from metrics.v_pl_monthly order by month")
sel = st.selectbox("Select month", ["All months"] + pnl["month"].tolist())

# ---------- numbers for the selected month ----------
if sel == "All months":
    lines = load("select account_code, account_name, account_type, sum(amount) as amt from metrics.v_pl_detail group by all order by 1")
else:
    lines = load("select account_code, account_name, account_type, sum(amount) as amt from metrics.v_pl_detail where month = ? group by all order by 1", [sel])

rev_lines = lines[lines["account_code"].between(4001, 4004)]
oth_lines = lines[lines["account_code"] == 4900]
exp_lines = lines[lines["account_type"] == "EXPENSE"]
revenue = rev_lines["amt"].sum()
other = oth_lines["amt"].sum()
expenses = exp_lines["amt"].sum()
net = revenue + other - expenses
margin = 100 * net / revenue if revenue else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue", inr(revenue))
c2.metric("Expenses", inr(expenses))
c3.metric("Net profit", inr(net))
c4.metric("Operating margin", f"{margin:.1f}%")

# ---------- the P&L statement table ----------
st.subheader(f"P&L statement: {sel}")
rows = [("INCOME", "")]
rows += [(f"   {r.account_code}  {r.account_name}", inr(r.amt)) for r in rev_lines.itertuples()]
rows += [("Total revenue (4001-4004)", inr(revenue))]
rows += [(f"   {r.account_code}  {r.account_name}", inr(r.amt)) for r in oth_lines.itertuples()]
rows += [("Total income", inr(revenue + other)), ("", ""), ("EXPENSES", "")]
rows += [(f"   {r.account_code}  {r.account_name}", inr(r.amt)) for r in exp_lines.itertuples()]
rows += [("Total expenses", inr(expenses)), ("", ""), ("NET PROFIT", inr(net)), ("Operating margin %", f"{margin:.1f}%")]
st.dataframe(pd.DataFrame(rows, columns=["Line", "Amount (INR)"]), use_container_width=True, hide_index=True, height=800)

# ---------- trend ----------
st.subheader("Revenue, expenses and net profit by month")
st.line_chart(pnl.set_index("month")[["revenue", "expenses", "net_profit"]])
st.subheader("Operating margin % by month")
st.bar_chart(pnl.set_index("month")[["margin_pct"]])

# ---------- expense by category and vendors ----------
left, right = st.columns(2)
with left:
    st.subheader("Expenses by category (all months)")
    cat = load("select category, expenses, pct_of_expenses from metrics.v_expense_by_category")
    st.bar_chart(cat.set_index("category")[["expenses"]])
    st.dataframe(cat, use_container_width=True, hide_index=True)
with right:
    st.subheader("Top 10 vendors by bill value")
    ven = load("select vendor, bills, spend from metrics.v_top_vendors")
    st.bar_chart(ven.set_index("vendor")[["spend"]])
    st.dataframe(ven, use_container_width=True, hide_index=True)
    st.caption("Vendor spend is from expense bills before GST. It is about 16% of all P&L expenses, because payroll is booked directly in the ledger.")

# ---------- tie-out ----------
st.subheader("Tie-out to the governed metrics")
tie_path = Path(__file__).resolve().parents[2] / "docs" / "pnl_tieout.csv"
if tie_path.exists():
    st.dataframe(pd.read_csv(tie_path), use_container_width=True, hide_index=True)
st.caption("The README sheet has no profit headline, so totals are tied to the metric dictionary: M16 Revenue, M17 Net profit, M18 Operating margin.")
