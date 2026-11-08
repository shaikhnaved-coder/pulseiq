CREATE SCHEMA IF NOT EXISTS metrics;

-- M01 Headcount (minimum group 5)
CREATE OR REPLACE VIEW metrics.m01_headcount AS
SELECT month_start_date, department_id,
       headcount_end AS headcount,
       headcount_end AS group_size
FROM wh.fact_headcount_monthly
WHERE headcount_end >= 5;

-- M02 Hires (minimum group 5)
CREATE OR REPLACE VIEW metrics.m02_hires AS
SELECT month_start_date, department_id,
       hires,
       headcount_end AS group_size
FROM wh.fact_headcount_monthly
WHERE headcount_end >= 5;

-- M03 Exits (minimum group 5)
CREATE OR REPLACE VIEW metrics.m03_exits AS
SELECT month_start_date, department_id,
       exits,
       headcount_end AS group_size
FROM wh.fact_headcount_monthly
WHERE headcount_end >= 5;

-- M04 Attrition rate, monthly = exits / headcount at start x 100 (minimum group 10)
CREATE OR REPLACE VIEW metrics.m04_attrition_monthly AS
SELECT month_start_date, department_id,
       ROUND(100.0 * exits / NULLIF(headcount_start, 0), 2) AS attrition_pct,
       headcount_start AS group_size
FROM wh.fact_headcount_monthly
WHERE headcount_start >= 10;

--M05 Attrition rate, rolling 12 months (minimum group 10)
CREATE OR REPLACE VIEW metrics.m05_attrition_rolling12 AS
WITH w AS (
  SELECT month_start_date, department_id,
         SUM(exits)         OVER win AS exits_12m,
         AVG(headcount_end) OVER win AS avg_headcount_12m,
         COUNT(*)           OVER win AS months_in_window
  FROM wh.fact_headcount_monthly
  WINDOW win AS (PARTITION BY department_id ORDER BY month_start_date
                 ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)
)
SELECT month_start_date, department_id,
       ROUND(100.0 * exits_12m / NULLIF(avg_headcount_12m, 0), 2) AS attrition_12m_pct,
       ROUND(avg_headcount_12m, 1) AS group_size
FROM w
WHERE months_in_window = 12
  AND avg_headcount_12m >= 10;

-- M06 Voluntary attrition rate, rolling 12 months (minimum group 10)
CREATE OR REPLACE VIEW metrics.m06_voluntary_attrition AS
WITH w AS (
  SELECT month_start_date, department_id,
         SUM(voluntary_exits) OVER win AS vol_exits_12m,
         AVG(headcount_end)   OVER win AS avg_headcount_12m,
         COUNT(*)             OVER win AS months_in_window
  FROM wh.fact_headcount_monthly
  WINDOW win AS (PARTITION BY department_id ORDER BY month_start_date
                 ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)
)
SELECT month_start_date, department_id,
       ROUND(100.0 * vol_exits_12m / NULLIF(avg_headcount_12m, 0), 2) AS voluntary_attrition_12m_pct,
       ROUND(avg_headcount_12m, 1) AS group_size
FROM w
WHERE months_in_window = 12
  AND avg_headcount_12m >= 10;

-- M07 Gross pay (minimum group 5)
CREATE OR REPLACE VIEW metrics.m07_gross_pay AS
SELECT DATE_TRUNC('month', period_end_date)::DATE AS month_start_date, department_id,
       ROUND(SUM(gross_pay), 2) AS gross_pay,
       COUNT(DISTINCT employee_id) AS group_size
FROM wh.fact_payroll
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

-- M08 Net pay (minimum group 5)
CREATE OR REPLACE VIEW metrics.m08_net_pay AS
SELECT DATE_TRUNC('month', period_end_date)::DATE AS month_start_date, department_id,
       ROUND(SUM(net_pay), 2) AS net_pay,
       COUNT(DISTINCT employee_id) AS group_size
FROM wh.fact_payroll
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

-- M09 Payroll cost = employer cost (minimum group 5)
CREATE OR REPLACE VIEW metrics.m09_payroll_cost AS
SELECT DATE_TRUNC('month', period_end_date)::DATE AS month_start_date, department_id,
       ROUND(SUM(employer_cost), 2) AS employer_cost,
       COUNT(DISTINCT employee_id) AS group_size
FROM wh.fact_payroll
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

-- M10 Cost per head = employer cost / employees paid (minimum group 5)
CREATE OR REPLACE VIEW metrics.m10_cost_per_head AS
SELECT DATE_TRUNC('month', period_end_date)::DATE AS month_start_date, department_id,
       ROUND(SUM(employer_cost) / NULLIF(COUNT(DISTINCT employee_id), 0), 2) AS cost_per_head,
       COUNT(DISTINCT employee_id) AS group_size
FROM wh.fact_payroll
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

-- M11 Overtime share = overtime pay / employer cost x 100 (minimum group 5)
CREATE OR REPLACE VIEW metrics.m11_overtime_share AS
SELECT DATE_TRUNC('month', period_end_date)::DATE AS month_start_date, department_id,
       ROUND(100.0 * SUM(overtime_pay) / NULLIF(SUM(employer_cost), 0), 2) AS overtime_share_pct,
       COUNT(DISTINCT employee_id) AS group_size
FROM wh.fact_payroll
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

-- M12 Variable pay share = variable pay / gross pay x 100 (minimum group 5)
CREATE OR REPLACE VIEW metrics.m12_variable_pay_share AS
SELECT DATE_TRUNC('month', period_end_date)::DATE AS month_start_date, department_id,
       ROUND(100.0 * SUM(variable_pay) / NULLIF(SUM(gross_pay), 0), 2) AS variable_pay_share_pct,
       COUNT(DISTINCT employee_id) AS group_size
FROM wh.fact_payroll
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

-- M15 Leave without pay days (minimum group 5)
CREATE OR REPLACE VIEW metrics.m15_lop_days AS
SELECT DATE_TRUNC('month', period_end_date)::DATE AS month_start_date, department_id,
       ROUND(SUM(lop_days), 1) AS lop_days,
       COUNT(DISTINCT employee_id) AS group_size
FROM wh.fact_payroll
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

-- M13 Attendance rate = (present days + 0.5 x half days) / scheduled days (minimum group 5)
CREATE OR REPLACE VIEW metrics.m13_attendance_rate AS
SELECT DATE_TRUNC('month', period_end_date)::DATE AS month_start_date, department_id,
       ROUND((SUM(present_days) + 0.5 * SUM(half_days_unpaid)) / NULLIF(SUM(scheduled_days), 0), 4) AS attendance_rate,
       COUNT(DISTINCT employee_id) AS group_size
FROM wh.fact_attendance_monthly
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

-- M14 Late arrival rate = late arrivals / present days (minimum group 5)
CREATE OR REPLACE VIEW metrics.m14_late_arrival_rate AS
SELECT DATE_TRUNC('month', period_end_date)::DATE AS month_start_date, department_id,
       ROUND(SUM(late_arrivals) / NULLIF(SUM(present_days), 0), 4) AS late_arrival_rate,
       COUNT(DISTINCT employee_id) AS group_size
FROM wh.fact_attendance_monthly
GROUP BY 1, 2
HAVING COUNT(DISTINCT employee_id) >= 5;

-- M16 Revenue = money in the income accounts 4001 to 4004, by account and month
-- (income is stored as a negative number in the ledger, so we flip the sign)
CREATE OR REPLACE VIEW metrics.m16_revenue AS
SELECT DATE_TRUNC('month', entry_date)::DATE AS month_start_date, account_code,
       ROUND(-SUM(signed_amount_debit_positive), 2) AS revenue
FROM wh.fact_ledger
WHERE account_code BETWEEN 4001 AND 4004
GROUP BY 1, 2;

-- M17 Net profit = income minus expenses (all 4xxx and 5xxx accounts), by month
CREATE OR REPLACE VIEW metrics.m17_net_profit AS
SELECT DATE_TRUNC('month', entry_date)::DATE AS month_start_date,
       ROUND(-SUM(signed_amount_debit_positive), 2) AS net_profit
FROM wh.fact_ledger
WHERE account_code BETWEEN 4000 AND 5999
GROUP BY 1;

-- M18 Operating margin = net profit / revenue x 100 (uses M16 and M17, so the definitions stay the same)
CREATE OR REPLACE VIEW metrics.m18_operating_margin AS
SELECT p.month_start_date,
       ROUND(100.0 * p.net_profit / NULLIF(r.revenue, 0), 2) AS operating_margin_pct
FROM metrics.m17_net_profit p
JOIN (SELECT month_start_date, SUM(revenue) AS revenue
      FROM metrics.m16_revenue GROUP BY 1) r USING (month_start_date);

-- M19 Payroll as % of revenue = payroll accounts 5001 to 5005 / revenue x 100
CREATE OR REPLACE VIEW metrics.m19_payroll_pct_revenue AS
SELECT pc.month_start_date,
       pc.payroll_cost,
       ROUND(100.0 * pc.payroll_cost / NULLIF(r.revenue, 0), 2) AS payroll_pct_of_revenue
FROM (SELECT DATE_TRUNC('month', entry_date)::DATE AS month_start_date,
             SUM(signed_amount_debit_positive) AS payroll_cost
      FROM wh.fact_ledger
      WHERE account_code BETWEEN 5001 AND 5005
      GROUP BY 1) pc
JOIN (SELECT month_start_date, SUM(revenue) AS revenue
      FROM metrics.m16_revenue GROUP BY 1) r USING (month_start_date);

-- M20 DSO (days sales outstanding) = money still to collect / invoices of last 90 days x 90, at each month end
-- money still to collect = ledger account 1100 up to the month end
-- invoices of last 90 days = total_amount of invoices (not DRAFT, not CANCELLED) in the 90 days up to month end
CREATE OR REPLACE VIEW metrics.m20_dso AS
WITH months AS (
  SELECT DISTINCT month_start_date, month_end_date FROM wh.dim_date
  WHERE month_end_date BETWEEN (SELECT MIN(entry_date) FROM wh.fact_ledger)
                           AND (SELECT MAX(entry_date) FROM wh.fact_ledger)
),
x AS (
  SELECT m.month_start_date,
         (SELECT SUM(l.signed_amount_debit_positive) FROM wh.fact_ledger l
           WHERE l.account_code = 1100 AND l.entry_date <= m.month_end_date) AS closing_receivables,
         (SELECT SUM(i.total_amount) FROM wh.fact_invoice i
           WHERE i.status NOT IN ('DRAFT', 'CANCELLED')
             AND i.invoice_date >  m.month_end_date - 90
             AND i.invoice_date <= m.month_end_date) AS revenue_incl_gst_90d
  FROM months m
)
SELECT month_start_date, closing_receivables, revenue_incl_gst_90d,
       ROUND(90.0 * closing_receivables / NULLIF(revenue_incl_gst_90d, 0), 1) AS dso_days
FROM x;

-- M21 Overdue receivables = unpaid money past its due date, by client, on the last ledger date
CREATE OR REPLACE VIEW metrics.m21_overdue_receivables AS
WITH rd AS (SELECT MAX(entry_date) AS report_date FROM wh.fact_ledger)
SELECT rd.report_date, i.client_id,
       SUM(i.balance_due) AS overdue_receivables,
       COUNT(*) AS overdue_invoices
FROM wh.fact_invoice i, rd
WHERE i.due_date < rd.report_date
  AND i.status NOT IN ('DRAFT', 'CANCELLED')
  AND i.balance_due > 0
GROUP BY 1, 2;

-- M22 Task completion rate = Done tasks / tasks not cancelled x 100 (minimum 5 tasks)
CREATE OR REPLACE VIEW metrics.m22_task_completion_rate AS
SELECT s.end_date AS sprint_end_date, t.sprint_id, t.team_id, tm.department_id,
       ROUND(100.0 * COUNT(*) FILTER (WHERE t.status = 'Done')
             / NULLIF(COUNT(*) FILTER (WHERE t.status <> 'Cancelled'), 0), 2) AS task_completion_pct,
       COUNT(*) FILTER (WHERE t.status <> 'Cancelled') AS group_size
FROM wh.fact_task t
JOIN wh.dim_sprint s USING (sprint_id)
JOIN wh.dim_team tm USING (team_id)
GROUP BY 1, 2, 3, 4
HAVING COUNT(*) FILTER (WHERE t.status <> 'Cancelled') >= 5;

-- M23 On-time delivery rate = Done on time / Done x 100 (minimum 5 tasks)
CREATE OR REPLACE VIEW metrics.m23_on_time_delivery AS
SELECT s.end_date AS sprint_end_date, t.sprint_id, t.team_id, tm.department_id,
       ROUND(100.0 * COUNT(*) FILTER (WHERE t.status = 'Done' AND t.completed_on_time = 'Y')
             / NULLIF(COUNT(*) FILTER (WHERE t.status = 'Done'), 0), 2) AS on_time_pct,
       COUNT(*) FILTER (WHERE t.status = 'Done') AS group_size
FROM wh.fact_task t
JOIN wh.dim_sprint s USING (sprint_id)
JOIN wh.dim_team tm USING (team_id)
GROUP BY 1, 2, 3, 4
HAVING COUNT(*) FILTER (WHERE t.status = 'Done') >= 5;

-- M24 Velocity = story points of Done tasks (the dictionary has no minimum for this one)
CREATE OR REPLACE VIEW metrics.m24_velocity AS
SELECT s.end_date AS sprint_end_date, t.sprint_id, t.team_id, tm.department_id,
       SUM(t.story_points) FILTER (WHERE t.status = 'Done') AS velocity_points
FROM wh.fact_task t
JOIN wh.dim_sprint s USING (sprint_id)
JOIN wh.dim_team tm USING (team_id)
GROUP BY 1, 2, 3, 4;

-- M25 Average cycle time = average days from started to completed, Done tasks only (minimum 5 tasks)
-- negative days are data errors, so they are left out
CREATE OR REPLACE VIEW metrics.m25_avg_cycle_time AS
SELECT s.end_date AS sprint_end_date, t.sprint_id, t.team_id, tm.department_id,
       ROUND(AVG(t.completed_date - t.started_date), 2) AS avg_cycle_days,
       COUNT(*) AS group_size
FROM wh.fact_task t
JOIN wh.dim_sprint s USING (sprint_id)
JOIN wh.dim_team tm USING (team_id)
WHERE t.status = 'Done'
  AND t.completed_date - t.started_date >= 0
GROUP BY 1, 2, 3, 4
HAVING COUNT(*) >= 5;

-- M26 Anomaly flag rate = flagged records / records checked x 100, by source and month
-- fact_anomaly only keeps the flagged rows, so dividing by its own count would always give 100%.
-- The records checked are the rows in the payroll / attendance table for that month.
CREATE OR REPLACE VIEW metrics.m26_anomaly_flag_rate AS
WITH flagged AS (
  SELECT source_dataset, period AS month_start_date, COUNT(*) AS flagged_records
  FROM wh.fact_anomaly
  WHERE flagged = 'Y'
  GROUP BY 1, 2
),
scored AS (
  SELECT 'payroll_monthly_features' AS source_dataset,
         DATE_TRUNC('month', period_end_date)::DATE AS month_start_date, COUNT(*) AS scored_records
  FROM wh.fact_payroll GROUP BY 2
  UNION ALL
  SELECT 'attendance_monthly_features',
         DATE_TRUNC('month', period_end_date)::DATE, COUNT(*)
  FROM wh.fact_attendance_monthly GROUP BY 2
)
SELECT s.source_dataset, s.month_start_date,
       COALESCE(f.flagged_records, 0) AS flagged_records,
       s.scored_records,
       ROUND(100.0 * COALESCE(f.flagged_records, 0) / NULLIF(s.scored_records, 0), 2) AS anomaly_flag_pct
FROM scored s
LEFT JOIN flagged f USING (source_dataset, month_start_date);

-- M27 High-risk share = employees in the High band / employees scored x 100, by department (minimum 10)
CREATE OR REPLACE VIEW metrics.m27_high_risk_share AS
SELECT as_of_date, department_id,
       ROUND(100.0 * COUNT(*) FILTER (WHERE risk_band = 'High') / NULLIF(COUNT(*), 0), 2) AS high_risk_pct,
       COUNT(*) AS group_size
FROM wh.fact_attrition_risk
GROUP BY 1, 2
HAVING COUNT(*) >= 10;

-- M28 Forecast error (MAPE) = how far the headcount forecast was from the real headcount, in %
-- only months that have BOTH a forecast and a real number show up
CREATE OR REPLACE VIEW metrics.m28_forecast_error AS
WITH e AS (
  SELECT f.forecast_month AS month_start_date, f.department_id,
         f.forecast_value, h.headcount_end AS actual,
         100.0 * ABS(h.headcount_end - f.forecast_value) / NULLIF(h.headcount_end, 0) AS abs_pct_error
  FROM wh.fact_forecast f
  JOIN wh.fact_headcount_monthly h
    ON h.department_id = f.department_id AND h.month_start_date = f.forecast_month
  WHERE f.metric = 'headcount_end'
)
SELECT month_start_date, department_id, forecast_value, actual,
       ROUND(abs_pct_error, 2) AS abs_pct_error,
       ROUND(AVG(abs_pct_error) OVER (PARTITION BY department_id ORDER BY month_start_date), 2) AS mape_pct
FROM e;

-- metric_catalog: one row per metric with its name, definition, source, owner and the view that holds it
CREATE OR REPLACE VIEW metrics.metric_catalog AS
SELECT d.metric_id,
       d.metric_name,
       d.business_definition,
       d.formula,
       d.source_table,
       d.owner_team,
       d.grain,
       d.unit,
       d.minimum_group_size,
       v.view_name AS metric_view
FROM clean.metric_dictionary d
LEFT JOIN (SELECT view_name FROM duckdb_views()
           WHERE schema_name = 'metrics' AND view_name LIKE 'm__\_%' ESCAPE '\') v
       ON LOWER(d.metric_id) = LEFT(v.view_name, 3);

-- Helper views for the dashboard (not new metrics; the app may only read the metrics schema)

-- department names, so charts show "Engineering" instead of "D01"
CREATE OR REPLACE VIEW metrics.lookup_department AS
SELECT department_id, department_name
FROM wh.dim_department;

-- people working today, by city tier (minimum group 5)
CREATE OR REPLACE VIEW metrics.app_headcount_by_tier AS
SELECT l.city_tier, COUNT(*) AS headcount, COUNT(*) AS group_size
FROM wh.dim_employee e
JOIN wh.dim_location l USING (work_location)
WHERE e.is_current = 'Y' AND e.employment_status = 'Active'
GROUP BY 1
HAVING COUNT(*) >= 5;

-- people working today, by work mode (minimum group 5)
CREATE OR REPLACE VIEW metrics.app_headcount_by_work_mode AS
SELECT work_mode, COUNT(*) AS headcount, COUNT(*) AS group_size
FROM wh.dim_employee
WHERE is_current = 'Y' AND employment_status = 'Active'
GROUP BY 1
HAVING COUNT(*) >= 5;