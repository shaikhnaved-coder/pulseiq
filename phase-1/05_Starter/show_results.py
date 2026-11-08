import duckdb

con = duckdb.connect("pulseiq.duckdb")
print(con.execute("SELECT table_name, rows_in, rows_passed, rows_quarantined, rows_balanced FROM etl.summary ORDER BY table_name").df().to_string(index=False))
print()
print(con.execute("SELECT source_table, row_key, reason FROM etl.quarantine ORDER BY source_table, row_id").df().to_string(index=False))