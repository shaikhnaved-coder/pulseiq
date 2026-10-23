import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
END = "COALESCE(e.valid_to, DATE '9999-12-31')"

def show(title, sql):
    r = con.sql(sql)
    print("==", title)
    print(" | ".join(r.columns))
    for row in r.fetchall():
        print(" | ".join(str(v) for v in row))
    print()

show("1. The 85 attendance rows outside their version dates", f"""
SELECT COUNT(*) AS rows_,
  SUM(CASE WHEN DATE_TRUNC('month', f.period_end_date) = DATE_TRUNC('month', e.exit_date) THEN 1 ELSE 0 END) AS in_exit_month,
  SUM(CASE WHEN e.valid_to = e.exit_date THEN 1 ELSE 0 END) AS valid_to_equals_exit_date,
  SUM(CASE WHEN f.period_end_date < e.valid_from THEN 1 ELSE 0 END) AS before_valid_from,
  SUM(CASE WHEN f.period_end_date > {END} THEN 1 ELSE 0 END) AS after_valid_to
FROM wh.fact_attendance_monthly f JOIN wh.dim_employee e ON f.employee_key = e.employee_key
WHERE f.period_end_date < e.valid_from OR f.period_end_date > {END}""")

show("2. Rows NOT in the exit month (up to 10)", f"""
SELECT f.attendance_fact_id, f.employee_id, f.employee_key, f.period_end_date,
       e.valid_from, e.valid_to, e.exit_date, e.is_current
FROM wh.fact_attendance_monthly f JOIN wh.dim_employee e ON f.employee_key = e.employee_key
WHERE (f.period_end_date < e.valid_from OR f.period_end_date > {END})
  AND DATE_TRUNC('month', f.period_end_date) <> DATE_TRUNC('month', e.exit_date)
LIMIT 10""")

show("3. Repeated employee-months in attendance", """
SELECT COUNT(*) AS repeated_employee_months FROM
 (SELECT employee_id, date_key FROM wh.fact_attendance_monthly GROUP BY 1, 2 HAVING COUNT(*) > 1)""")

show("4. Attendance employee-months with no payroll row", """
SELECT COUNT(*) AS attendance_without_payroll
FROM wh.fact_attendance_monthly a
WHERE NOT EXISTS (SELECT 1 FROM wh.fact_payroll p
                  WHERE p.employee_id = a.employee_id AND p.date_key = a.date_key)""")

show("5. Payroll employee-months with no attendance row", """
SELECT COUNT(*) AS payroll_without_attendance
FROM wh.fact_payroll p
WHERE NOT EXISTS (SELECT 1 FROM wh.fact_attendance_monthly a
                  WHERE p.employee_id = a.employee_id AND p.date_key = a.date_key)""")