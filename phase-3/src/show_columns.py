import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
views = ["m01_headcount", "m04_attrition_monthly", "m09_payroll_cost",
         "v_pl_monthly", "m13_attendance_rate"]

for v in views:
    print("\n==", v)
    print(con.sql(f"select * from metrics.{v} limit 3").df().to_string())