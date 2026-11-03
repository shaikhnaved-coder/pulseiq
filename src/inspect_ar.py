import duckdb
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
rows = con.execute("""
    SELECT table_schema, table_name FROM information_schema.tables
    WHERE lower(table_name) LIKE '%invoice%' OR lower(table_name) LIKE '%payment%'
       OR lower(table_name) LIKE '%cash%' OR lower(table_name) LIKE '%client%'
       OR lower(table_name) LIKE '%receiv%'
""").fetchall()
for r in rows:
    print("\n==", r[0] + "." + r[1])
    print(con.execute(f"DESCRIBE {r[0]}.{r[1]}").fetchdf()[["column_name","column_type"]].to_string(index=False))