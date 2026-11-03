import duckdb, pandas as pd
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 100, "display.max_colwidth", 90)

con = duckdb.connect("05_Starter/pulseiq.duckdb")   # writable: views are created in the metrics schema
con.execute("create schema if not exists metrics")

# 1. group vs detail
con.execute("""
create or replace view metrics.v_account_class as
select account_code, account_name, account_type, statement, parent_code, is_group,
       case when is_group = 'Y' then 'group' else 'detail' end as acct_level
from wh.dim_account
""")

# 2. P&L ledger lines on DETAIL accounts only (groups 4000 and 5000 never counted)
#    income is stored as credit (negative in debit-positive), so flip its sign
con.execute("""
create or replace view metrics.v_pl_detail as
select l.posting_period as month, l.entry_date, a.account_code, a.account_name, a.account_type,
       case when a.account_type = 'INCOME' then -l.signed_amount_debit_positive
            else l.signed_amount_debit_positive end as amount
from wh.fact_ledger l
join wh.dim_account a on a.account_code = l.account_code
where a.statement = 'Profit & Loss' and a.is_group = 'N'
""")

# 3. revenue, expenses, margin by month
con.execute("""
create or replace view metrics.v_pl_monthly as
with m as (
  select month,
         sum(case when account_type = 'INCOME'  then amount else 0 end) as revenue,
         sum(case when account_type = 'EXPENSE' then amount else 0 end) as expenses
  from metrics.v_pl_detail group by month)
select month, round(revenue, 2) as revenue, round(expenses, 2) as expenses,
       round(revenue - expenses, 2) as margin,
       round(100.0 * (revenue - expenses) / nullif(revenue, 0), 1) as margin_pct
from m order by month
""")

# 4. expense by category (each detail expense account)
con.execute("""
create or replace view metrics.v_expense_by_category as
select account_code, account_name as category, round(sum(amount), 2) as expenses,
       round(100.0 * sum(amount) / sum(sum(amount)) over (), 1) as pct_of_expenses
from metrics.v_pl_detail where account_type = 'EXPENSE'
group by 1, 2 order by expenses desc
""")

# 5. top 10 vendors (from expense bills, before GST)
con.execute("""
create or replace view metrics.v_top_vendors as
select v.vendor_name as vendor, count(*) as bills, round(sum(e.amount_excl_gst), 2) as spend
from wh.fact_expense e
join wh.dim_vendor v on v.vendor_id = e.vendor_id
group by 1 order by spend desc limit 10
""")

print("=== accounts: group vs detail ===")
print(con.execute("select statement, acct_level, count(*) as n from metrics.v_account_class group by all order by 1, 2").df())

print("\n=== ledger lines posted to GROUP accounts (should be 0) ===")
print(con.execute("select count(*) as lines_on_groups from wh.fact_ledger l join wh.dim_account a using (account_code) where a.is_group = 'Y'").df())

print("\n=== P&L by month ===")
print(con.execute("select * from metrics.v_pl_monthly").df().to_string())
print("\n=== P&L grand total ===")
print(con.execute("select round(sum(revenue),2) revenue, round(sum(expenses),2) expenses, round(sum(margin),2) margin, round(100.0*sum(margin)/sum(revenue),1) margin_pct from metrics.v_pl_monthly").df())

print("\n=== revenue split: operating (4001-4004) vs other income (4900) ===")
print(con.execute("select round(sum(case when account_code between 4001 and 4004 then amount else 0 end),2) as operating, round(sum(case when account_code = 4900 then amount else 0 end),2) as other_income from metrics.v_pl_detail where account_type='INCOME'").df())
print("existing m16_revenue total:", con.execute("select round(sum(revenue),2) from metrics.m16_revenue").fetchone()[0])

print("\n=== expenses by category ===")
print(con.execute("select * from metrics.v_expense_by_category").df().to_string())

print("\n=== top 10 vendors ===")
print(con.execute("select * from metrics.v_top_vendors").df())
print("\nexpense bill status counts:")
print(con.execute("select status, count(*) as n, round(sum(amount_excl_gst),0) as amount from wh.fact_expense group by 1 order by 2 desc").df())

print("\n=== metric_dictionary rows about revenue / expense / margin / profit ===")
md = pd.read_excel("03_Data/PulseIQ_Dataset.xlsx", sheet_name="metric_dictionary")
mask = md.apply(lambda r: r.astype(str).str.contains("revenue|expense|margin|profit|vendor|P&L", case=False).any(), axis=1)
print(md[mask].to_string())