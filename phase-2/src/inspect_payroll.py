import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

rows = con.execute("""
    SELECT table_schema, table_name, column_name, data_type
    FROM information_schema.columns
    WHERE lower(table_name) LIKE '%payroll%'
       OR lower(table_name) LIKE '%dept%'
       OR lower(table_name) LIKE '%department%'
    ORDER BY table_schema, table_name, ordinal_position
""").fetchall()

current = None
for schema, table, col, dtype in rows:
    if (schema, table) != current:
        current = (schema, table)
        print()
        print(f"{schema}.{table}")
    print(f"    {col}  ({dtype})")