import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

checks = [("D04", "2025-04-01"), ("D03", "2025-10-01"), ("D01", "2025-04-01")]

for dept, month in checks:
    print("=" * 50)
    print("Department", dept, "| Month", month)

    budget = con.execute("""
        SELECT budget_payroll_cost
        FROM raw.budget_payroll_dept_month
        WHERE department_id = ? AND month = CAST(? AS DATE)
    """, [dept, month]).fetchone()[0]
    print("Budget (from raw budget file):", budget)

    n, g, pf, esi = con.execute("""
        SELECT COUNT(*),
               ROUND(SUM(gross_pay), 2),
               ROUND(SUM(pf_employer), 2),
               ROUND(SUM(esi_employer), 2)
        FROM clean.fact_payroll
        WHERE department_id = ?
          AND date_trunc('month', period_end_date) = CAST(? AS DATE)
          AND payroll_item_id NOT IN (SELECT payroll_item_id FROM metrics.payroll_exclusions)
    """, [dept, month]).fetchone()
    print("Payroll rows used:", n)
    print("Sum of gross_pay     :", g)
    print("Sum of pf_employer   :", pf)
    print("Sum of esi_employer  :", esi)