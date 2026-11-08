import duckdb
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
p = lambda s: print(con.execute(s).fetchdf().to_string(index=False))

print("\n-- statuses");  p("SELECT status, count(*) n, sum(balance_due) bal FROM wh.fact_invoice GROUP BY 1 ORDER BY 1")
print("\n-- dataset buckets"); p("SELECT ageing_bucket_at_cutoff b, min(days_past_due_at_cutoff) mn, max(days_past_due_at_cutoff) mx, count(*) n FROM wh.fact_invoice GROUP BY 1 ORDER BY 2")
print("\n-- tables that may hold cash out"); p("""SELECT table_schema, table_name FROM information_schema.tables
  WHERE table_schema IN ('wh','metrics') AND (lower(table_name) LIKE '%vendor%' OR lower(table_name) LIKE '%bill%'
  OR lower(table_name) LIKE '%expense%' OR lower(table_name) LIKE '%payable%' OR lower(table_name) LIKE '%ledger%'
  OR lower(table_name) LIKE '%pl_%' OR lower(table_name) LIKE '%bank%')""")
for v in ["metrics.v_pl_monthly", "metrics.v_expense_by_category"]:
    print("\n--", v); p(f"DESCRIBE {v}")
print("\n-- v_pl_monthly sample"); p("SELECT * FROM metrics.v_pl_monthly LIMIT 5")