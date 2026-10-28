import duckdb
con = duckdb.connect("05_Starter/pulseiq.duckdb")

# 1) Attendance by month x department
con.execute("""
CREATE OR REPLACE VIEW wh.v_attendance_monthly AS
SELECT
  date_trunc('month', period_end_date)               AS month,
  department_id                                       AS department,
  SUM(scheduled_days)                                 AS scheduled_days,
  SUM(present_days)                                   AS present_days,
  ROUND(100.0 * SUM(present_days) / NULLIF(SUM(scheduled_days),0), 2) AS attendance_rate,
  SUM(late_arrivals)                                  AS late_arrivals,
  ROUND(SUM(overtime_hours), 1)                       AS overtime_hours,
  SUM(paid_leave_days)                                AS paid_leave_days,
  SUM(unpaid_absence_days)                            AS unpaid_absence_days,
  SUM(wfh_days)                                       AS wfh_days
FROM wh.fact_attendance_monthly
GROUP BY 1, 2
""")

# 2) Leave days by month x department x leave type (approved/pending, not rejected)
con.execute("""
CREATE OR REPLACE VIEW wh.v_leave_monthly AS
SELECT
  date_trunc('month', l.start_date)  AS month,
  e.department_id                    AS department,
  t.leave_type_name                  AS leave_type,
  SUM(l.days)                        AS leave_days,
  COUNT(*)                           AS requests
FROM wh.fact_leave l
JOIN wh.dim_employee e   ON e.employee_key = l.employee_key
JOIN wh.dim_leave_type t ON t.leave_type_code = l.leave_type_code
WHERE UPPER(l.status) NOT IN ('REJECTED','CANCELLED','CANCELED')
GROUP BY 1, 2, 3
""")

# 3) Holidays and long weekends per month, from dim_date
con.execute("""
CREATE OR REPLACE VIEW wh.v_holiday_months AS
SELECT
  date_trunc('month', date)                                         AS month,
  COUNT(*) FILTER (WHERE UPPER(is_holiday) IN ('Y','YES','TRUE','1')) AS holidays,
  COUNT(*) FILTER (WHERE UPPER(is_holiday) IN ('Y','YES','TRUE','1')
                   AND dayofweek(date) IN (1,5))                    AS long_weekends,
  COUNT(*) FILTER (WHERE UPPER(is_working_day) IN ('Y','YES','TRUE','1')) AS working_days,
  string_agg(strftime(date, '%d %b (%a)'), ', ' ORDER BY date)
      FILTER (WHERE UPPER(is_holiday) IN ('Y','YES','TRUE','1'))    AS holiday_dates
FROM wh.dim_date
GROUP BY 1
""")

for v in ["v_attendance_monthly", "v_leave_monthly", "v_holiday_months"]:
       print(v, con.execute(f"SELECT COUNT(*) FROM wh.{v}").fetchall()[0][0], "rows")