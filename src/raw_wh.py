import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

checks = {
"DQ-C02 Ledger balanced": """
    SELECT entry_id FROM {s}.fact_ledger
    GROUP BY entry_id
    HAVING ABS(SUM(debit) - SUM(credit)) > 0.005
""",
"DQ-C03 Unique payroll rows": """
    SELECT employee_id, run_id FROM {s}.fact_payroll
    GROUP BY employee_id, run_id
    HAVING COUNT(*) > 1
""",
"DQ-C04 No orphan employees": """
    SELECT DISTINCT f.employee_id
    FROM {s}.fact_payroll f
    LEFT JOIN {s}.dim_employee d ON f.employee_id = d.employee_id
    WHERE d.employee_id IS NULL
""",
"DQ-C05 No attendance after exit": """
    SELECT a.*
    FROM {s}.fact_attendance_monthly a
    JOIN {s}.dim_employee d
      ON a.employee_id = d.employee_id AND d.is_current = 'Y'
    WHERE d.exit_date IS NOT NULL
      AND a.period_end_date > LAST_DAY(d.exit_date)
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