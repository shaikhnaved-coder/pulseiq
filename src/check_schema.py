
import duckdb

con = duckdb.connect(
    "05_Starter/pulseiq.duckdb",
    read_only=True
)

query = """
SELECT COUNT(*)
FROM {schema}.fact_task
WHERE completed_date < started_date
   OR (status = 'Done' AND completed_date IS NULL)
"""

for schema in ["raw", "clean", "wh"]:
    count = con.execute(
        query.format(schema=schema)
    ).fetchone()[0]

    print(f"{schema.upper()}: {count} invalid tasks")

con.close()