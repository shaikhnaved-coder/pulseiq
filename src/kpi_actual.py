import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

words = ["attend", "overtime", "attrition", "exit", "task", "sprint", "delivery", "leave"]
like = " OR ".join(f"lower(table_name) LIKE '%{w}%'" for w in words)

rows = con.execute(f"""
    SELECT table_schema, table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema IN ('metrics', 'wh')
      AND ({like})
    ORDER BY table_schema, table_name, ordinal_position
""").fetchall()

current = None
for schema, table, col, dtype in rows:
    if (schema, table) != current:
        current = (schema, table)
        print()
        print(f"{schema}.{table}")
    print(f"    {col}  ({dtype})")