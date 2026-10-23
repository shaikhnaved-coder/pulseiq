import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

checks = {
"DQ-C01 Payroll equals ledger": """
    WITH p AS (
        SELECT strftime(CAST(period_end_date AS DATE), '%Y-%m') AS month,
               SUM(CAST(employer_cost AS DOUBLE)) AS cost
        FROM {s}.fact_payroll GROUP BY 1
    ),
    l AS (
        SELECT strftime(CAST(entry_date AS DATE), '%Y-%m') AS month,
               SUM(CAST(debit AS DOUBLE) - CAST(credit AS DOUBLE)) AS expense
        FROM {s}.fact_ledger
        WHERE CAST(account_code AS VARCHAR) IN ('5001','5002','5003','5004','5005')
        GROUP BY 1
    )
    SELECT p.month, ROUND(p.cost - COALESCE(l.expense, 0), 2) AS diff
    FROM p LEFT JOIN l USING (month)
    WHERE ABS(ROUND(p.cost - COALESCE(l.expense, 0), 2)) > 0.01
""",
"DQ-C06 Unpaid leave deducted": """
    SELECT a.employee_id, a.period_end_date,
           a.unpaid_absence_days, p.lop_days
    FROM {s}.fact_attendance_monthly a
    JOIN {s}.fact_payroll p
      ON a.employee_id = p.employee_id
     AND CAST(a.period_end_date AS DATE) = CAST(p.period_end_date AS DATE)
    WHERE ABS(CAST(a.unpaid_absence_days AS DOUBLE)
            - CAST(p.lop_days AS DOUBLE)) > 0.5
""",
}

print(f"{'check':35} {'raw':>8} {'wh':>8}")
for name, sql in checks.items():
    counts = []
    for s in ["raw", "wh"]:
        try:
            n = con.execute(f"SELECT COUNT(*) FROM ({sql.format(s=s)})").fetchone()[0]
        except Exception as e:
            n = "ERR"
            print("  error on", s, ":", str(e)[:150])
        counts.append(n)
    print(f"{name:35} {counts[0]:>8} {counts[1]:>8}")

# Does the C06 join actually match rows?
print()
print("Rows matched by the C06 join:", con.execute("""
    SELECT COUNT(*)
    FROM wh.fact_attendance_monthly a
    JOIN wh.fact_payroll p
      ON a.employee_id = p.employee_id
     AND CAST(a.period_end_date AS DATE) = CAST(p.period_end_date AS DATE)
""").fetchone()[0])
print("Rows in attendance table:", con.execute(
    "SELECT COUNT(*) FROM wh.fact_attendance_monthly").fetchone()[0])