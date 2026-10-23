import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

print("\n========== DATA QUALITY CHECK CATALOG ==========")

query = """
SELECT *
FROM raw.dq_checks_catalog
ORDER BY 1
"""

result = con.execute(query).fetchdf()

print(result.to_string(index=False))

print("\n========== CATALOG COMPLETE ==========")

con.close()
