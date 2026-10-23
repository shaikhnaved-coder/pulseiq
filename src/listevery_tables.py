import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

rows = con.execute("""
    SELECT table_schema, table_name, table_type
    FROM information_schema.tables
    WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
    ORDER BY table_schema, table_name
""").fetchall()

for schema, name, kind in rows:
    print(f"{schema:8} {name:35} {kind}")