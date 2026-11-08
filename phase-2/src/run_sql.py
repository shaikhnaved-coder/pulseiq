import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb")
con.execute(open("src/mymetrics.sql", encoding="utf-8").read())

for v in ["lookup_department", "app_headcount_by_tier", "app_headcount_by_work_mode"]:
    print(v)
    print(con.execute(f"SELECT * FROM metrics.{v} ORDER BY 1").fetchdf().to_string())
    print()