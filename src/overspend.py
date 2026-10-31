import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

for dept in ("D03", "D02"):
    print("=" * 12, dept, "=" * 12)
    print(con.execute("""
        WITH comp AS (
            SELECT CAST(date_trunc('month', period_end_date) AS DATE) AS month_start_date,
                   department_id,
                   SUM(earned_fixed_pay) AS fixed_pay,
                   SUM(overtime_pay)     AS overtime_pay,
                   SUM(variable_pay)     AS variable_pay
            FROM metrics.v_payroll_valid
            GROUP BY 1, 2
        )
        SELECT v.month_start_date AS month,
               v.budget,
               ROUND(v.actual)   AS actual,
               ROUND(v.variance) AS variance,
               v.status,
               m.group_size      AS headcount,
               ROUND(m.cost_per_employee) AS cost_per_emp,
               ROUND(c.fixed_pay)    AS fixed_pay,
               ROUND(c.overtime_pay) AS overtime_pay,
               ROUND(c.variable_pay) AS variable_pay
        FROM metrics.v_payroll_budget_variance v
        JOIN metrics.m30_payroll_month_dept m
          ON m.department_id = v.department_id
         AND m.month_start_date = v.month_start_date
        LEFT JOIN comp c
          ON c.department_id = v.department_id
         AND c.month_start_date = v.month_start_date
        WHERE v.department_id = ?
        ORDER BY v.month_start_date
    """, [dept]).df().to_string())
    print()