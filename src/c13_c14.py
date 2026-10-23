import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

print("C13: last load time")
print(con.execute("""
    SELECT MAX(CAST(run_at AS TIMESTAMP)) AS last_load,
           CURRENT_TIMESTAMP AS now_time
    FROM etl.summary
""").df().to_string())

print("\nC14: minimum group size rules")
print(con.execute("""
    SELECT metric_id, metric_name, source_table, grain, minimum_group_size
    FROM clean.metric_dictionary
    ORDER BY metric_id
""").df().to_string())