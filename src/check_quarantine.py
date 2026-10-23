import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
rows = con.sql("""
    SELECT source_table, row_key, reason FROM etl.quarantine
    WHERE reason LIKE '%duplicate employee-month%' OR reason LIKE '%after the exit date%'
    ORDER BY 1, 2""").fetchall()
for r in rows:
    print(" | ".join(str(x) for x in r))
print(len(rows), "rows quarantined by the new rules")
print("total in quarantine:", con.sql("SELECT COUNT(*) FROM etl.quarantine").fetchone()[0])