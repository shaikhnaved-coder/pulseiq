import duckdb, csv
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
one = lambda s: con.execute(s).fetchone()[0]
OPEN = "upper(status) IN ('SENT','OVERDUE','PARTIALLY_PAID')"

total_open  = one(f"SELECT sum(balance_due) FROM wh.fact_invoice WHERE {OPEN}")
bucket_sum  = one("SELECT sum(open_amount) FROM metrics.v_ar_ageing")
calc_open   = one(f"SELECT sum(total_amount - amount_paid) FROM wh.fact_invoice WHERE {OPEN}")
excluded    = one(f"SELECT sum(balance_due) FROM wh.fact_invoice WHERE NOT ({OPEN})")
od_status   = one("SELECT COALESCE(sum(overdue_amount), 0) FROM metrics.v_overdue_by_client")
od_past_due = one("SELECT COALESCE(sum(open_amount), 0) FROM metrics.v_ar_open WHERE days_past_due > 0")
m21         = one("""SELECT sum(overdue_receivables) FROM metrics.m21_overdue_receivables
                     WHERE report_date = (SELECT max(report_date) FROM metrics.m21_overdue_receivables)""")

if m21 == od_status:        m21_result = "TIES (status OVERDUE)"
elif m21 == od_past_due:    m21_result = "TIES (all open invoices past due)"
else:                       m21_result = "DIFFERENT - explain in README"

rows = [("check", "value", "result"),
        ("Total open receivables (balance_due, SENT/OVERDUE/PARTIALLY_PAID)", total_open, ""),
        ("Sum of the 4 ageing buckets", bucket_sum, "TIES" if bucket_sum == total_open else "DOES NOT TIE"),
        ("Total minus paid on open invoices", calc_open, "TIES" if calc_open == total_open else "DIFFERENT"),
        ("Balance on non-open invoices (DRAFT, PAID, CANCELLED) left out", excluded, "info"),
        ("Overdue by client (status OVERDUE)", od_status, ""),
        ("Open invoices past due (any status)", od_past_due, ""),
        ("metrics.m21 overdue receivables (latest report_date)", m21, m21_result)]
for b, n, a in con.execute("SELECT bucket, invoices, open_amount FROM metrics.v_ar_ageing").fetchall():
    rows.append((f"Bucket {b} ({n} invoices)", a, ""))
with open("docs/ar_bucket_check.csv", "w", newline="") as f:
    csv.writer(f).writerows(rows)
for r in rows: print(r)