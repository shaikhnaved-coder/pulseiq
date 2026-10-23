import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

for t in ["dim_employee", "dim_sprint", "fact_payroll", "fact_attendance_monthly",
          "fact_leave", "fact_attrition_risk", "fact_task", "fact_anomaly"]:
    print(f"\n== wh.{t} ==")
    for col, typ in con.sql(f"""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema = 'wh' AND table_name = '{t}'
        ORDER BY ordinal_position""").fetchall():
        print(f"  {col:32} {typ}")

print("\n== sample: wh.dim_employee, first 3 rows ==")
con.sql("SELECT * FROM wh.dim_employee LIMIT 3").show(max_width=250)
print("\n== sample: wh.fact_payroll, first 2 rows ==")
con.sql("SELECT * FROM wh.fact_payroll LIMIT 2").show(max_width=250)