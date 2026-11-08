import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb")

con.execute("""
CREATE OR REPLACE VIEW metrics.v_payroll_budget_variance AS
SELECT *,
       CASE
         WHEN actual IS NULL       THEN 'Grey'
         WHEN variance_pct <= 2    THEN 'Green'
         WHEN variance_pct <= 5    THEN 'Amber'
         ELSE 'Red'
       END AS status
FROM (
    SELECT b.month AS month_start_date,
           b.department_id,
           d.department_name,
           b.budget_payroll_cost AS budget,
           a.employer_cost AS actual,
           a.employer_cost - b.budget_payroll_cost AS variance,
           ROUND((a.employer_cost - b.budget_payroll_cost) * 100.0
                 / b.budget_payroll_cost, 2) AS variance_pct
    FROM clean.budget_payroll_dept_month b
    LEFT JOIN metrics.m30_payroll_month_dept a
           ON a.department_id = b.department_id
          AND a.month_start_date = b.month
    LEFT JOIN clean.dim_department d
           ON d.department_id = b.department_id
)
""")

v = "metrics.v_payroll_budget_variance"

print("Rows in view:", con.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0])

print()
print("Status counts:")
print(con.execute(f"SELECT status, COUNT(*) AS n FROM {v} GROUP BY status ORDER BY n DESC").df().to_string())

print()
print("D00 (first 2 rows):")
print(con.execute(f"SELECT * FROM {v} WHERE department_id='D00' ORDER BY month_start_date LIMIT 2").df().to_string())

print()
print("First month, all departments:")
print(con.execute(f"""SELECT * FROM {v}
    WHERE month_start_date = (SELECT MIN(month_start_date) FROM {v})
    ORDER BY department_id""").df().to_string())