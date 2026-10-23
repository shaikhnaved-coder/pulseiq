import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

query = """
SELECT 'RAW' AS source, COUNT(*) AS total_rows
FROM raw.fact_payroll

UNION ALL

SELECT 'WH' AS source, COUNT(*) AS total_rows
FROM wh.fact_payroll;
"""

print("\n========== PAYROLL ROW COUNTS ==========")
print(con.execute(query).fetchdf().to_string(index=False))

print("\n========== PAYROLL TABLE COLUMNS ==========")

columns = con.execute("""
SELECT table_schema, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'fact_payroll'
AND table_schema IN ('raw', 'wh')
ORDER BY table_schema, ordinal_position
""").fetchdf()

print(columns.to_string(index=False))

con.close()
