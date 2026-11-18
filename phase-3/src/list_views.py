import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
rows = con.sql("""
    select table_schema, table_name
    from information_schema.tables
    where table_schema not in ('information_schema', 'pg_catalog')
    order by table_schema, table_name
""").fetchall()

for schema, name in rows:
    print(schema, ".", name)