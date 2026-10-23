import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

targets = [("wh", "fact_attendance_monthly"),
           ("etl", "summary"),
           ("etl", "quarantine"),
           ("clean", "metric_dictionary")]

for schema, table in targets:
    cols = con.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = ? AND table_name = ?
        ORDER BY ordinal_position
    """, [schema, table]).fetchall()
    print(f"\n{schema}.{table}")
    for name, dtype in cols:
        print(f"   {name:35} {dtype}")

# Also show what is inside etl.summary
print("\netl.summary contents:")
print(con.execute("SELECT * FROM etl.summary LIMIT 20").df().to_string())