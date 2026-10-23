import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

# First, see how is_current is written (Y/N, true/false, ...)
print("is_current values:",
      con.execute("SELECT DISTINCT is_current FROM wh.dim_employee").fetchall())

checks = {
"DQ-C02 Ledger balanced": """
    SELECT entry_id
    FROM wh.fact_ledger
    GROUP BY entry_id
    HAVING ABS(SUM(debit) - SUM(credit)) > 0.005
""",
"DQ-C03 Unique payroll rows": """
    SELECT employee_id, run_id
    FROM wh.fact_payroll
    GROUP BY employee_id, run_id
    HAVING COUNT(*) > 1
""",
"DQ-C04 No orphan employees": """
    SELECT DISTINCT f.employee_id
    FROM wh.fact_payroll f
    LEFT JOIN wh.dim_employee d ON f.employee_id = d.employee_id
    WHERE d.employee_id IS NULL
""",
"DQ-C05 No attendance after exit": """
    SELECT a.*
    FROM wh.fact_attendance_monthly a
    JOIN wh.dim_employee d
      ON a.employee_id = d.employee_id AND d.is_current = 'Y'
    WHERE d.exit_date IS NOT NULL
      AND a.period_end_date > LAST_DAY(d.exit_date)
""",
}

for name, sql in checks.items():
    bad = con.execute(f"SELECT COUNT(*) FROM ({sql})").fetchone()[0]
    status = "PASS" if bad == 0 else "FAIL"
    print(f"{name:35} bad rows: {bad:6}   {status}")