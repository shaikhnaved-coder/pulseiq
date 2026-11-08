import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

print("1) Where is kpi_targets?")
print(con.execute("""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE lower(table_name) LIKE '%kpi%'
""").fetchall())

print()
print("2) Budget vs two possible actuals, first 2 months")
df = con.execute("""
    SELECT b.month,
           b.department_id,
           b.budget_payroll_cost AS budget,
           ROUND(a.gross_pay)    AS gross_pay,
           ROUND(a.employer_cost) AS employer_cost
    FROM clean.budget_payroll_dept_month b
    LEFT JOIN metrics.m30_payroll_month_dept a
           ON a.department_id = b.department_id
          AND a.month_start_date = b.month
    WHERE b.month IN (
        SELECT DISTINCT month
        FROM clean.budget_payroll_dept_month
        ORDER BY month
        LIMIT 2)
    ORDER BY b.month, b.department_id
""").df()
print(df.to_string())

print()
print("3) Budget rows with NO matching actual row (join check)")
print(con.execute("""
    SELECT COUNT(*)
    FROM clean.budget_payroll_dept_month b
    LEFT JOIN metrics.m30_payroll_month_dept a
           ON a.department_id = b.department_id
          AND a.month_start_date = b.month
    WHERE a.department_id IS NULL
""").fetchall())