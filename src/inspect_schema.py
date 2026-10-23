import duckdb

DB_PATH = "05_Starter/pulseiq.duckdb"
con = duckdb.connect(DB_PATH, read_only=True)

rows = con.sql("""
    SELECT table_schema, table_name, table_type
    FROM information_schema.tables
    WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
    ORDER BY table_schema, table_name
""").fetchall()

for schema, name, ttype in rows:
    n = con.sql(f'SELECT COUNT(*) FROM "{schema}"."{name}"').fetchone()[0]
    print(f"{schema}.{name:42} {n:>8} rows  [{ttype}]")

print("\nTotal objects:", len(rows))