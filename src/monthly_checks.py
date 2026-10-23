import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

def cols(t):
    return [r[0] for r in con.sql(f"""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='wh' AND table_name='{t}'
        ORDER BY ordinal_position""").fetchall()]

def one(sql):
    return con.sql(sql).fetchone()[0]

print("=== COLUMNS (one line per table) ===")
for t in ["dim_employee", "dim_sprint", "fact_payroll", "fact_attendance_monthly",
          "fact_leave", "fact_attrition_risk", "fact_task", "fact_anomaly"]:
    print(f"\n{t}:\n  " + ", ".join(cols(t)))

print("\n=== CHECK A: payroll employee_key points to the same person ===")
print("rows whose key belongs to another employee_id:", one("""
    SELECT COUNT(*) FROM wh.fact_payroll f
    JOIN wh.dim_employee e ON f.employee_key = e.employee_key
    WHERE e.employee_id <> f.employee_id"""))
print("rows whose key is not in dim_employee:", one("""
    SELECT COUNT(*) FROM wh.fact_payroll f
    LEFT JOIN wh.dim_employee e ON f.employee_key = e.employee_key
    WHERE e.employee_key IS NULL"""))

print("\n=== CHECK B: payroll month falls inside the version's dates ===")
print("rows outside valid_from..valid_to:", one("""
    SELECT COUNT(*) FROM wh.fact_payroll f
    JOIN wh.dim_employee e ON f.employee_key = e.employee_key
    WHERE f.period_end_date < e.valid_from
       OR f.period_end_date > COALESCE(e.valid_to, DATE '9999-12-31')"""))

print("\n=== CHECK C: overlapping versions in dim_employee ===")
print("pairs of overlapping versions:", one("""
    SELECT COUNT(*) FROM wh.dim_employee a
    JOIN wh.dim_employee b
      ON a.employee_id = b.employee_id AND a.employee_key < b.employee_key
     AND a.valid_from <= COALESCE(b.valid_to, DATE '9999-12-31')
     AND b.valid_from <= COALESCE(a.valid_to, DATE '9999-12-31')"""))
print("example overlaps (up to 5):")
con.sql("""
    SELECT a.employee_id, a.employee_key AS key_a, a.valid_from AS from_a, a.valid_to AS to_a,
           b.employee_key AS key_b, b.valid_from AS from_b, b.valid_to AS to_b
    FROM wh.dim_employee a JOIN wh.dim_employee b
      ON a.employee_id = b.employee_id AND a.employee_key < b.employee_key
     AND a.valid_from <= COALESCE(b.valid_to, DATE '9999-12-31')
     AND b.valid_from <= COALESCE(a.valid_to, DATE '9999-12-31')
    ORDER BY 1 LIMIT 5""").show(max_width=200)

print("employees without exactly one is_current='Y' version:", one("""
    SELECT COUNT(*) FROM (
      SELECT employee_id FROM wh.dim_employee
      GROUP BY employee_id HAVING SUM(CASE WHEN is_current='Y' THEN 1 ELSE 0 END) <> 1)"""))

print("\n=== CHECK D: department through employee_key ===")
dept = next((c for c in cols("dim_employee") if c.lower().startswith("department")), None)
if not dept:
    print("dim_employee has no column starting with 'department'. Send me the column list above.")
else:
    print(f"department column in dim_employee: {dept}")
    print("payroll rows where fact department differs from the version's department:", one(f"""
        SELECT COUNT(*) FROM wh.fact_payroll f
        JOIN wh.dim_employee e ON f.employee_key = e.employee_key
        WHERE f.department_id <> e.{dept}"""))
    mover = con.sql(f"""
        SELECT employee_id FROM wh.dim_employee
        GROUP BY employee_id HAVING COUNT(DISTINCT {dept}) > 1 LIMIT 1""").fetchone()
    if mover:
        print(f"\nMOVER PROOF: {mover[0]} payroll month by month")
        con.sql(f"""
            SELECT f.date_key, f.employee_key, e.{dept} AS dept_via_key, f.department_id AS dept_in_fact
            FROM wh.fact_payroll f JOIN wh.dim_employee e ON f.employee_key = e.employee_key
            WHERE f.employee_id = '{mover[0]}' ORDER BY f.date_key""").show(max_rows=30, max_width=200)
    else:
        print("No employee with more than one department found.")