import duckdb, pandas as pd
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 100)

con = duckdb.connect("05_Starter/pulseiq.duckdb")

# 1. final monthly P&L, aligned to the metric dictionary:
#    M16 revenue = 4001-4004, 4900 other income shown separately, M17 net profit = revenue + other income - expenses
con.execute("""
create or replace view metrics.v_pl_monthly as
with m as (
  select month,
    sum(case when account_code between 4001 and 4004 then amount else 0 end) as revenue,
    sum(case when account_code = 4900 then amount else 0 end) as other_income,
    sum(case when account_type = 'EXPENSE' then amount else 0 end) as expenses
  from metrics.v_pl_detail group by month)
select month, round(revenue,2) as revenue, round(other_income,2) as other_income, round(expenses,2) as expenses,
       round(revenue + other_income - expenses, 2) as net_profit,
       round(100.0 * (revenue + other_income - expenses) / nullif(revenue,0), 1) as margin_pct
from m order by month
""")

# 2. my totals (from the views)
mine = con.execute("select sum(revenue), sum(expenses), sum(net_profit) from metrics.v_pl_monthly").fetchone()
my_margin = 100 * mine[2] / mine[0]

# 3. targets, computed straight from fact_ledger with the dictionary formulas (no joins, no views)
q = lambda sql: con.execute(sql).fetchone()[0]
rev_m16   = q("select sum(revenue) from metrics.m16_revenue")
rev_led   = -q("select sum(signed_amount_debit_positive) from wh.fact_ledger where account_code between 4001 and 4004")
exp_led   = q("select sum(signed_amount_debit_positive) from wh.fact_ledger where account_code between 5000 and 5999")
np_led    = -q("select sum(signed_amount_debit_positive) from wh.fact_ledger where account_code between 4000 and 5999")
margin_t  = 100 * np_led / rev_led

rows = [
 ("Revenue vs governed metric M16 (m16_revenue)", mine[0], rev_m16, 1),
 ("Revenue vs fact_ledger, accounts 4001-4004",  mine[0], rev_led, 1),
 ("Expenses vs fact_ledger, accounts 5xxx",      mine[1], exp_led, 1),
 ("Net profit vs M17 formula (4xxx less 5xxx)",  mine[2], np_led, 1),
 ("Operating margin % vs M18 formula",           my_margin, margin_t, 0.05),
]
out = pd.DataFrame([{"Check": n, "My total": round(a, 2), "Dictionary / ledger": round(b, 2),
                     "Difference": round(a - b, 2), "Status": "TIES" if abs(a - b) <= tol else "CHECK"}
                    for n, a, b, tol in rows])
print(out.to_string(index=False))
out.to_csv("docs/pnl_tieout.csv", index=False)

# 4. month by month revenue vs m16_revenue
bad = q("""select count(*) from metrics.v_pl_monthly p
           left join (select strftime(month_start_date,'%Y-%m') m, sum(revenue) r from metrics.m16_revenue group by 1) g on g.m = p.month
           where abs(p.revenue - coalesce(g.r,0)) > 1""")
print("\nMonths where revenue differs from m16_revenue:", bad, "of 18")

# 5. expense bills vs ledger, account by account
print("\n=== expense bills (before GST) vs ledger, by account ===")
print(con.execute("""
with b as (select category_account as account_code, sum(amount_excl_gst) as bills from wh.fact_expense group by 1),
     l as (select account_code, sum(signed_amount_debit_positive) as ledger from wh.fact_ledger group by 1)
select b.account_code, round(b.bills) as bills, round(l.ledger) as ledger, round(l.ledger - b.bills) as diff
from b left join l using (account_code) order by 1""").df().to_string(index=False))

# 6. facts for your 3 findings
print("\n=== facts for findings ===")
print(con.execute("select month, revenue, expenses, net_profit, margin_pct from metrics.v_pl_monthly order by margin_pct desc").df().iloc[[0, 1, -2, -1]].to_string(index=False))
print("\nTop vendor shares of total bill spend:")
print(con.execute("""
with v as (select v.vendor_name, sum(e.amount_excl_gst) s from wh.fact_expense e join wh.dim_vendor v using (vendor_id) group by 1),
     t as (select sum(s) tot from v)
select (select round(100*sum(s)/max(tot),1) from (select s from v order by s desc limit 3), t) as top3_pct,
       (select round(100*sum(s)/max(tot),1) from (select s from v order by s desc limit 10), t) as top10_pct,
       (select round(tot) from t) as total_bills""").df())
print("Bills as % of all P&L expenses:", round(100 * q("select sum(amount_excl_gst) from wh.fact_expense") / exp_led, 1))
