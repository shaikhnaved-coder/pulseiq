import duckdb
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
KEYS = ["headcount","payroll","attend","leave","employee","attrition","exit","overtime","dept","department"]
rows = con.execute("""SELECT table_schema, table_name FROM information_schema.tables
                      WHERE table_schema IN ('wh','metrics') ORDER BY 1,2""").fetchall()
for s, t in rows:
    if any(k in t.lower() for k in KEYS):
        print("\n==", f"{s}.{t}")
        print(con.execute(f"DESCRIBE {s}.{t}").fetchdf()[["column_name","column_type"]].to_string(index=False))