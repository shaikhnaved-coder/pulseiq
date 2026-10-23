import duckdb

DB = "05_Starter/pulseiq.duckdb"

con = duckdb.connect(DB, read_only=True)

query = """
SELECT
    row_key,
    failed_checks,
    reason
FROM etl.quarantine
WHERE source_table = 'fact_payroll'
ORDER BY row_key
"""

result = con.execute(query).fetchdf()

print("\n========== QUARANTINED PAYROLL RECORDS ==========\n")

if result.empty:
    print("No quarantined payroll records found.")
else:
    print(result.to_string(index=False))

con.close()