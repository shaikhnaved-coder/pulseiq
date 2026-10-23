import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
END = "COALESCE(e.valid_to, DATE '9999-12-31')"

BAD = f"""
SELECT f.payroll_item_id, f.employee_id, f.employee_key AS fact_key,
       f.period_end_date, f.department_id AS fact_dept,
       e.valid_from, e.valid_to, e.is_current, e.exit_date,
       CASE WHEN f.period_end_date < e.valid_from THEN 'before valid_from'
            ELSE 'after valid_to' END AS direction,
       CASE WHEN f.period_end_date < e.valid_from
            THEN DATE_DIFF('day', f.period_end_date, e.valid_from)
            ELSE DATE_DIFF('day', e.valid_to, f.period_end_date) END AS gap_days
FROM wh.fact_payroll f
JOIN wh.dim_employee e ON f.employee_key = e.employee_key
WHERE f.period_end_date < e.valid_from OR f.period_end_date > {END}
"""

print("=== 1. Direction and size of the rows outside their dates ===")
con.sql(f"""SELECT direction, COUNT(*) AS payroll_rows, COUNT(DISTINCT employee_id) AS employees,
            MIN(gap_days) AS min_gap_days, MAX(gap_days) AS max_gap_days
            FROM ({BAD}) GROUP BY direction""").show()

print("=== 2. Are they current versions, and do these people have an exit date? ===")
con.sql(f"""SELECT is_current, direction, COUNT(*) AS payroll_rows, COUNT(exit_date) AS with_exit_date
            FROM ({BAD}) GROUP BY 1, 2""").show()

print("=== 3. How many versions WERE valid on that month end (same employee_id)? ===")
con.sql(f"""
WITH b AS ({BAD}),
m AS (SELECT b.payroll_item_id, COUNT(e.employee_key) AS valid_versions
      FROM b LEFT JOIN wh.dim_employee e
        ON e.employee_id = b.employee_id
       AND b.period_end_date >= e.valid_from
       AND b.period_end_date <= {END}
      GROUP BY 1)
SELECT valid_versions, COUNT(*) AS payroll_rows FROM m GROUP BY 1 ORDER BY 1""").show()

print("=== 4. The 10 biggest gaps ===")
con.sql(f"""SELECT payroll_item_id, employee_id, fact_key, period_end_date, valid_from, valid_to,
            is_current, exit_date, direction, gap_days
            FROM ({BAD}) ORDER BY gap_days DESC LIMIT 10""").show(max_width=250)

print("=== 5. Mover proof: employees in payroll who changed department ===")
movers = con.sql("""
    SELECT f.employee_id FROM wh.fact_payroll f
    JOIN wh.dim_employee e ON f.employee_key = e.employee_key
    GROUP BY f.employee_id HAVING COUNT(DISTINCT e.department_id) > 1
    ORDER BY 1 LIMIT 3""").fetchall()
print("movers found:", [m[0] for m in movers])
if movers:
    emp = movers[0][0]
    print(f"Payroll month by month for {emp}:")
    con.sql(f"""SELECT f.date_key, f.employee_key, e.department_id AS dept_via_key,
                f.department_id AS dept_in_fact, e.valid_from, e.valid_to
                FROM wh.fact_payroll f JOIN wh.dim_employee e ON f.employee_key = e.employee_key
                WHERE f.employee_id = '{emp}' ORDER BY f.date_key""").show(max_rows=30, max_width=250)

print("=== 6. fact_anomaly ===")
print("rows with no employee_id:", con.sql("SELECT COUNT(*) FROM wh.fact_anomaly WHERE employee_id IS NULL").fetchone()[0])
con.sql("""SELECT source_dataset, COUNT(*) AS rows_, COUNT(employee_id) AS with_employee
           FROM wh.fact_anomaly GROUP BY 1 ORDER BY 1""").show()
con.sql("SELECT period, period_key, employee_id, source_dataset FROM wh.fact_anomaly LIMIT 5").show()

print("=== 7. Columns of the remaining tables ===")
for t in ["dim_sprint", "fact_task", "fact_attendance_monthly", "fact_leave", "fact_attrition_risk"]:
    cols = [r[0] for r in con.sql(f"""SELECT column_name FROM information_schema.columns
            WHERE table_schema='wh' AND table_name='{t}' ORDER BY ordinal_position""").fetchall()]
    print(f"\\n{t}:\\n  " + ", ".join(cols))