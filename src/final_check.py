import sys, duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
END = "COALESCE(e.valid_to, DATE '9999-12-31')"
OUT = open("step4_final_output.txt", "w", encoding="utf-8")
sys.stdout = OUT

def one(sql):
    return con.sql(sql).fetchone()[0]

def table(sql):
    r = con.sql(sql)
    print(" | ".join(r.columns))
    for row in r.fetchall():
        print(" | ".join(str(v) for v in row))
    print()

print("=== A. The 82 payroll rows outside their version dates: is it the exit month? ===")
table(f"""
SELECT COUNT(*) AS rows_,
       SUM(CASE WHEN DATE_TRUNC('month', f.period_end_date) = DATE_TRUNC('month', e.exit_date) THEN 1 ELSE 0 END) AS in_exit_month,
       SUM(CASE WHEN e.valid_to = e.exit_date THEN 1 ELSE 0 END) AS valid_to_equals_exit_date,
       SUM(CASE WHEN f.period_end_date > e.exit_date THEN 1 ELSE 0 END) AS after_exit_date
FROM wh.fact_payroll f JOIN wh.dim_employee e ON f.employee_key = e.employee_key
WHERE f.period_end_date > {END}""")

print("=== B. Payroll employee-months that appear more than once ===")
print("employee-months with more than one payroll row:", one("""
    SELECT COUNT(*) FROM (SELECT employee_id, date_key FROM wh.fact_payroll
                          GROUP BY 1, 2 HAVING COUNT(*) > 1)"""))
table("""
SELECT employee_id, date_key, COUNT(*) AS n,
       STRING_AGG(payroll_item_id, ', ') AS item_ids,
       STRING_AGG(run_id, ', ') AS run_ids,
       STRING_AGG(CAST(net_pay AS VARCHAR), ', ') AS net_pays
FROM wh.fact_payroll GROUP BY 1, 2 HAVING COUNT(*) > 1
ORDER BY 1, 2 LIMIT 20""")

print("=== C. employee_key checks on the other facts that carry it ===")
CHECKS = [
    ("fact_attendance_monthly", "f.period_end_date", True),
    ("fact_leave", "f.start_date", False),
    ("fact_attrition_risk", "f.as_of_date", True),
]
for fact, d, has_dept in CHECKS:
    print("--", fact)
    print("rows:", one(f"SELECT COUNT(*) FROM wh.{fact}"))
    print("employee_key is NULL:", one(f"SELECT COUNT(*) FROM wh.{fact} WHERE employee_key IS NULL"))
    print("employee_key not in dim_employee:", one(f"""SELECT COUNT(*) FROM wh.{fact} f
        LEFT JOIN wh.dim_employee e ON f.employee_key = e.employee_key
        WHERE f.employee_key IS NOT NULL AND e.employee_key IS NULL"""))
    print("key belongs to a different employee_id:", one(f"""SELECT COUNT(*) FROM wh.{fact} f
        JOIN wh.dim_employee e ON f.employee_key = e.employee_key WHERE e.employee_id <> f.employee_id"""))
    print("date outside the version's dates:", one(f"""SELECT COUNT(*) FROM wh.{fact} f
        JOIN wh.dim_employee e ON f.employee_key = e.employee_key
        WHERE CAST({d} AS DATE) < e.valid_from OR CAST({d} AS DATE) > {END}"""))
    if has_dept:
        print("department differs from the version's department:", one(f"""SELECT COUNT(*) FROM wh.{fact} f
            JOIN wh.dim_employee e ON f.employee_key = e.employee_key WHERE f.department_id <> e.department_id"""))
    print()

print("=== D. The tasks with no employee version valid at the sprint end ===")
table(f"""
WITH m AS (
  SELECT t.task_id, t.assignee_employee_id AS emp, s.start_date, s.end_date,
         COUNT(e.employee_key) AS versions
  FROM wh.fact_task t
  JOIN wh.dim_sprint s ON s.sprint_id = t.sprint_id
  LEFT JOIN wh.dim_employee e
    ON e.employee_id = t.assignee_employee_id
   AND s.end_date >= e.valid_from AND s.end_date <= {END}
  GROUP BY ALL),
z AS (SELECT * FROM m WHERE versions = 0),
r AS (SELECT employee_id, MIN(valid_from) AS first_from,
             MAX(COALESCE(valid_to, DATE '9999-12-31')) AS last_to
      FROM wh.dim_employee GROUP BY 1)
SELECT CASE WHEN z.end_date < r.first_from THEN 'sprint ends before first version'
            WHEN z.end_date > r.last_to THEN 'sprint ends after last version ended'
            ELSE 'falls in a gap between versions' END AS reason,
       COUNT(*) AS tasks, COUNT(DISTINCT z.emp) AS employees,
       SUM(CASE WHEN EXISTS (SELECT 1 FROM wh.dim_employee e2
             WHERE e2.employee_id = z.emp AND z.start_date >= e2.valid_from
               AND z.start_date <= COALESCE(e2.valid_to, DATE '9999-12-31')) THEN 1 ELSE 0 END) AS valid_at_sprint_start
FROM z JOIN r ON r.employee_id = z.emp GROUP BY 1""")

print("=== E. fact_anomaly: employee versions valid at the period end ===")
table(f"""
WITH m AS (
  SELECT a.result_id, COUNT(e.employee_key) AS versions
  FROM wh.fact_anomaly a
  LEFT JOIN wh.dim_employee e
    ON e.employee_id = a.employee_id
   AND CAST(STRPTIME(CAST(a.period_key AS VARCHAR), '%Y%m%d') AS DATE) >= e.valid_from
   AND CAST(STRPTIME(CAST(a.period_key AS VARCHAR), '%Y%m%d') AS DATE) <= {END}
  GROUP BY 1)
SELECT versions, COUNT(*) AS anomalies FROM m GROUP BY 1 ORDER BY 1""")

sys.stdout = sys.__stdout__
OUT.close()
print("Saved step4_final_output.txt")