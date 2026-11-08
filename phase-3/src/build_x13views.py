import duckdb
con = duckdb.connect("05_Starter/pulseiq.duckdb")
con.execute("CREATE SCHEMA IF NOT EXISTS metrics")

# Each source is first totalled to ONE row per (department_id, month). Month looks like '2025-04'.
# Headcount = month-end headcount from the warehouse (same definition as m01, but it keeps the
# 1-person Executive Office that m01 hides). m01's own value is kept as headcount_m01.
HEADCOUNT_SQL = """
SELECT f.department_id, strftime(f.month_start_date, '%Y-%m') AS month,
       f.headcount_end AS headcount, m.headcount AS headcount_m01
FROM wh.fact_headcount_monthly f
LEFT JOIN metrics.m01_headcount m
       ON m.department_id = f.department_id AND m.month_start_date = f.month_start_date
"""
# payroll_cost = clean payroll (the 4 bad rows already removed by v_payroll_valid).
# *_incl_excluded = raw payroll including the 4 bad rows, kept only for the reference comparison.
PAYROLL_SQL = """
SELECT v.department_id, v.month, v.payroll_cost, v.gross_pay, v.overtime_cost,
       r.payroll_cost_raw  AS payroll_cost_incl_excluded,
       r.overtime_cost_raw AS overtime_cost_incl_excluded
FROM (SELECT department_id, strftime(period_end_date, '%Y-%m') AS month,
             sum(employer_cost) AS payroll_cost, sum(gross_pay) AS gross_pay, sum(overtime_pay) AS overtime_cost
      FROM metrics.v_payroll_valid GROUP BY 1, 2) v
LEFT JOIN (SELECT department_id, strftime(period_end_date, '%Y-%m') AS month,
                  sum(employer_cost) AS payroll_cost_raw, sum(overtime_pay) AS overtime_cost_raw
           FROM raw.fact_payroll GROUP BY 1, 2) r USING (department_id, month)
"""
# Attendance rate counts a half day as half a day present: (present + 0.5 x half days) / scheduled days.
# The older present-only formula is kept as attendance_rate_present_only_pct for the comparison notes.
ATTENDANCE_SQL = """
SELECT department_id, strftime(period_end_date, '%Y-%m') AS month,
       sum(scheduled_days) AS scheduled_days, sum(present_days) AS present_days,
       sum(half_days_unpaid) AS half_days_unpaid,
       sum(paid_leave_days) AS paid_leave_days, sum(unpaid_absence_days) AS unpaid_absence_days,
       sum(overtime_hours) AS overtime_hours,
       round(100.0 * (sum(present_days) + 0.5 * sum(half_days_unpaid)) / nullif(sum(scheduled_days), 0), 2) AS attendance_rate_pct,
       round(100.0 * sum(present_days) / nullif(sum(scheduled_days), 0), 2) AS attendance_rate_present_only_pct
FROM wh.fact_attendance_monthly GROUP BY 1, 2
"""
LEAVE_SQL = """
SELECT department AS department_id, strftime(month, '%Y-%m') AS month, sum(leave_days) AS leave_days
FROM wh.v_leave_monthly GROUP BY 1, 2
"""
ATTRITION_SQL = """
SELECT e.department_id, strftime(e.month_start_date, '%Y-%m') AS month, e.exits, a.attrition_pct
FROM metrics.m03_exits e
LEFT JOIN metrics.m04_attrition_monthly a USING (month_start_date, department_id)
"""

for name, sql in [("x13_headcount", HEADCOUNT_SQL), ("x13_payroll", PAYROLL_SQL),
                  ("x13_attendance", ATTENDANCE_SQL), ("x13_leave", LEAVE_SQL),
                  ("x13_attrition", ATTRITION_SQL)]:
    con.execute(f"CREATE OR REPLACE VIEW metrics.{name} AS {sql}")

# Join step: a spine of every department-month seen in any source, limited to the months payroll covers,
# then LEFT JOIN each already-aggregated source onto it (explicit ON, so no ambiguous columns).
con.execute("""
CREATE OR REPLACE VIEW metrics.v_dept_month_impact AS
WITH spine AS (
    SELECT department_id, month FROM metrics.x13_headcount
    UNION SELECT department_id, month FROM metrics.x13_payroll
    UNION SELECT department_id, month FROM metrics.x13_attendance
    UNION SELECT department_id, month FROM metrics.x13_leave
    UNION SELECT department_id, month FROM metrics.x13_attrition
)
SELECT s.department_id, dd.department_name, s.month,
       h.headcount, h.headcount_m01,
       p.payroll_cost, p.payroll_cost_incl_excluded, p.gross_pay,
       p.overtime_cost, p.overtime_cost_incl_excluded,
       round(100.0 * p.overtime_cost / nullif(p.payroll_cost, 0), 2) AS overtime_pct_of_cost,
       a.scheduled_days, a.present_days, a.half_days_unpaid,
       a.attendance_rate_pct, a.attendance_rate_present_only_pct, a.overtime_hours,
       a.paid_leave_days, a.unpaid_absence_days,
       COALESCE(l.leave_days, 0) AS leave_days,
       round(COALESCE(l.leave_days, 0) / nullif(h.headcount, 0), 3) AS leave_days_per_head,
       COALESCE(x.exits, 0) AS exits, x.attrition_pct
FROM spine s
LEFT JOIN metrics.x13_headcount  h ON h.department_id = s.department_id AND h.month = s.month
LEFT JOIN metrics.x13_payroll    p ON p.department_id = s.department_id AND p.month = s.month
LEFT JOIN metrics.x13_attendance a ON a.department_id = s.department_id AND a.month = s.month
LEFT JOIN metrics.x13_leave      l ON l.department_id = s.department_id AND l.month = s.month
LEFT JOIN metrics.x13_attrition  x ON x.department_id = s.department_id AND x.month = s.month
LEFT JOIN wh.dim_department      dd ON dd.department_id = s.department_id
WHERE s.month BETWEEN (SELECT min(month) FROM metrics.x13_payroll)
                  AND (SELECT max(month) FROM metrics.x13_payroll)
ORDER BY 1, 3
""")
print("x13 views built")