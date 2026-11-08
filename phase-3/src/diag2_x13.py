import duckdb, pandas as pd
pd.options.display.float_format = "{:,.2f}".format
pd.options.display.width = 200
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
p = lambda t, s: (print("\n--", t), print(con.execute(s).fetchdf().to_string(index=False)))

p("1. Months and departments covered by each source", """
SELECT 'm01_headcount' src, min(month_start_date) first_month, max(month_start_date) last_month,
       count(DISTINCT department_id) depts, count(*) dept_months FROM metrics.m01_headcount
UNION ALL SELECT 'wh_headcount', min(month_start_date), max(month_start_date),
       count(DISTINCT department_id), count(*) FROM wh.fact_headcount_monthly
UNION ALL SELECT 'payroll_valid', min(period_end_date), max(period_end_date),
       count(DISTINCT department_id), count(DISTINCT department_id || strftime(period_end_date,'%Y-%m')) FROM metrics.v_payroll_valid
UNION ALL SELECT 'attendance', min(period_end_date), max(period_end_date),
       count(DISTINCT department_id), count(DISTINCT department_id || strftime(period_end_date,'%Y-%m')) FROM wh.fact_attendance_monthly
UNION ALL SELECT 'leave_view', min(month), max(month),
       count(DISTINCT department), count(DISTINCT department || strftime(month,'%Y-%m')) FROM wh.v_leave_monthly
""")

p("2. Department-months in the warehouse but missing from m01, by department", """
SELECT d.department_id, d.department_name, d.is_leadership, count(*) AS missing_rows,
       min(f.headcount_end) AS min_headcount, max(f.headcount_end) AS max_headcount
FROM wh.fact_headcount_monthly f JOIN wh.dim_department d USING (department_id)
WHERE NOT EXISTS (SELECT 1 FROM metrics.m01_headcount m
                  WHERE m.department_id = f.department_id AND m.month_start_date = f.month_start_date)
GROUP BY 1, 2, 3 ORDER BY 4 DESC
""")

p("3. Total headcount (summed over all months): warehouse vs m01", """
SELECT (SELECT sum(headcount_end) FROM wh.fact_headcount_monthly) wh_total_end,
       (SELECT sum(headcount) FROM metrics.m01_headcount) m01_total
""")

p("4. Payroll with full precision", """
SELECT (SELECT sum(employer_cost) FROM wh.fact_payroll) all_cost,
       (SELECT sum(employer_cost) FROM metrics.v_payroll_valid) valid_cost,
       (SELECT sum(employer_cost) FROM wh.fact_payroll) - (SELECT sum(employer_cost) FROM metrics.v_payroll_valid) AS difference,
       (SELECT sum(employer_cost) FROM metrics.payroll_exclusions) excluded_cost,
       (SELECT count(*) FROM wh.fact_payroll) all_rows,
       (SELECT count(*) FROM metrics.v_payroll_valid) valid_rows,
       (SELECT count(*) FROM metrics.payroll_exclusions) excluded_rows
""")

p("5. Leave: what the view counts, and how many requests cross a month boundary", """
SELECT sum(CASE WHEN upper(status) NOT IN ('REJECTED','CANCELLED','CANCELED') THEN "days" END) AS in_view_days,
       sum(CASE WHEN upper(status) = 'APPROVED' THEN "days" END) AS approved_only_days,
       count(*) FILTER (WHERE date_trunc('month', start_date) <> date_trunc('month', end_date)) AS requests_crossing_months
FROM wh.fact_leave
""")