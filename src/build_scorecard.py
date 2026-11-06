import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb")

con.execute("""
CREATE OR REPLACE VIEW metrics.v_scorecard AS
WITH
rev AS (SELECT month_start_date, SUM(revenue) AS v
        FROM metrics.m16_revenue GROUP BY 1),
mar AS (SELECT month_start_date, operating_margin_pct AS v
        FROM metrics.m18_operating_margin),
pay AS (SELECT month_start_date, payroll_pct_of_revenue AS v
        FROM metrics.m19_payroll_pct_revenue),
dso AS (SELECT month_start_date, dso_days AS v FROM metrics.m20_dso),

-- Attrition: M05 formula for the whole company, from M01 (headcount) and M03 (exits)
hx AS (SELECT h.month_start_date, SUM(h.headcount) AS hc, SUM(x.exits) AS ex
       FROM metrics.m01_headcount h
       JOIN metrics.m03_exits x USING (month_start_date, department_id)
       GROUP BY 1),
att AS (SELECT month_start_date,
               ROUND(100.0 * SUM(ex) OVER w / NULLIF(AVG(hc) OVER w, 0), 2) AS v
        FROM hx
        WINDOW w AS (ORDER BY month_start_date
                     ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)),

-- Attendance: M13 weighted by employees, shown as a percent
atn AS (SELECT month_start_date,
               ROUND(100.0 * SUM(attendance_rate * group_size) / SUM(group_size), 2) AS v
        FROM metrics.m13_attendance_rate GROUP BY 1),

-- Task completion: M22 weighted by tasks in scope, grouped by the month the sprint ends
tsk AS (SELECT CAST(date_trunc('month', sprint_end_date) AS DATE) AS month_start_date,
               ROUND(SUM(task_completion_pct * group_size) / SUM(group_size), 2) AS v
        FROM metrics.m22_task_completion_rate GROUP BY 1),

-- Overtime share: M11 weighted by employer cost (M09); its target is weighted the same way
ot AS (SELECT s.month_start_date,
              ROUND(SUM(s.overtime_share_pct * c.employer_cost) / SUM(c.employer_cost), 3) AS v,
              ROUND(SUM(t.overtime_share_target_pct * c.employer_cost) / SUM(c.employer_cost), 3) AS tgt
       FROM metrics.m11_overtime_share s
       JOIN metrics.m09_payroll_cost c USING (month_start_date, department_id)
       JOIN clean.kpi_targets t
         ON t.month = s.month_start_date AND t.department_id = s.department_id
       GROUP BY 1),

-- Targets from the data (kpi_targets)
tg AS (SELECT month AS month_start_date,
              ROUND(100 * AVG(attendance_rate_target), 2)   AS att_t,
              ROUND(12 * AVG(attrition_monthly_target_pct), 2) AS attr_t,
              ROUND(AVG(task_completion_target_pct), 2)     AS task_t
       FROM clean.kpi_targets GROUP BY 1),

allk AS (
  SELECT 'K1' AS kpi_id, month_start_date, v AS value,
         ROUND(AVG(v) OVER () / 1000000.0, 1) * 1000000 AS target FROM rev
  UNION ALL SELECT 'K2', month_start_date, v, ROUND(AVG(v) OVER (), 1) FROM mar
  UNION ALL SELECT 'K3', month_start_date, v, ROUND(AVG(v) OVER (), 1) FROM pay
  UNION ALL SELECT 'K4', month_start_date, v, ROUND(AVG(v) OVER (), 1) FROM dso
  UNION ALL SELECT 'K5', a.month_start_date, a.v, tg.attr_t
            FROM att a JOIN tg USING (month_start_date)
  UNION ALL SELECT 'K6', b.month_start_date, b.v, tg.att_t
            FROM atn b JOIN tg USING (month_start_date)
  UNION ALL SELECT 'K7', k.month_start_date, k.v, tg.task_t
            FROM tsk k JOIN tg USING (month_start_date)
  UNION ALL SELECT 'K8', month_start_date, v, tgt FROM ot
),

rules(kpi_id, kpi_name, metric_id, metric_view, unit, direction, amber_band, target_source) AS (
  VALUES
  ('K1','Revenue','M16','m16_revenue (sum of accounts)','INR','higher',5000000,
   'Benchmark: 18-month company average (no target in data)'),
  ('K2','Operating margin','M18','m18_operating_margin','percent','higher',3,
   'Benchmark: 18-month company average (no target in data)'),
  ('K3','Payroll as % of revenue','M19','m19_payroll_pct_revenue','percent','lower',3,
   'Benchmark: 18-month company average (no target in data)'),
  ('K4','Days sales outstanding','M20','m20_dso','days','lower',5,
   'Benchmark: 18-month company average (no target in data)'),
  ('K5','Attrition, rolling 12 months','M05','m01_headcount + m03_exits (M05 formula, all departments)','percent','lower',2,
   'kpi_targets: 1% a month x 12'),
  ('K6','Attendance rate','M13','m13_attendance_rate (weighted by employees)','percent','higher',1.5,
   'kpi_targets'),
  ('K7','Task completion rate','M22','m22_task_completion_rate (weighted by tasks)','percent','higher',5,
   'kpi_targets'),
  ('K8','Overtime share','M11','m11_overtime_share x m09_payroll_cost (weighted by cost)','percent','lower',0.5,
   'kpi_targets, weighted by cost')
)

SELECT a.month_start_date, a.kpi_id, r.kpi_name, r.metric_id, r.metric_view, r.unit,
       a.value, a.target, r.target_source, r.direction, r.amber_band,
       LAG(a.value) OVER (PARTITION BY a.kpi_id ORDER BY a.month_start_date) AS prev_value,
       ROUND(a.value - LAG(a.value) OVER (PARTITION BY a.kpi_id
                                          ORDER BY a.month_start_date), 3) AS change,
       CASE
         WHEN a.target IS NULL THEN 'Grey'
         WHEN r.direction = 'higher' THEN
              CASE WHEN a.value >= a.target THEN 'Green'
                   WHEN a.value >= a.target - r.amber_band THEN 'Amber'
                   ELSE 'Red' END
         ELSE CASE WHEN a.value <= a.target THEN 'Green'
                   WHEN a.value <= a.target + r.amber_band THEN 'Amber'
                   ELSE 'Red' END
       END AS status
FROM allk a JOIN rules r USING (kpi_id)
""")

def show(title, sql):
    print("\n" + "=" * 70)
    print(title)
    for r in con.execute(sql).fetchall():
        print(r)

show("ROWS: (rows, months, KPIs, null values, null targets)  expect 144, 18, 8, 0, 0",
     """SELECT COUNT(*), COUNT(DISTINCT month_start_date), COUNT(DISTINCT kpi_id),
               SUM(CASE WHEN value IS NULL THEN 1 ELSE 0 END),
               SUM(CASE WHEN target IS NULL THEN 1 ELSE 0 END)
        FROM metrics.v_scorecard""")

show("SEP 2026: (kpi, name, value, target, previous, status)",
     """SELECT kpi_id, kpi_name, value, target, prev_value, status
        FROM metrics.v_scorecard
        WHERE month_start_date = DATE '2026-09-01' ORDER BY kpi_id""")

show("AUG 2026: (kpi, name, value, target, previous, status)",
     """SELECT kpi_id, kpi_name, value, target, prev_value, status
        FROM metrics.v_scorecard
        WHERE month_start_date = DATE '2026-08-01' ORDER BY kpi_id""")

show("STATUS counts over all months: (kpi, green, amber, red, grey)",
     """SELECT kpi_id,
               SUM(CASE WHEN status = 'Green' THEN 1 ELSE 0 END),
               SUM(CASE WHEN status = 'Amber' THEN 1 ELSE 0 END),
               SUM(CASE WHEN status = 'Red'   THEN 1 ELSE 0 END),
               SUM(CASE WHEN status = 'Grey'  THEN 1 ELSE 0 END)
        FROM metrics.v_scorecard GROUP BY 1 ORDER BY 1""")

print("\nDone. View metrics.v_scorecard created.")