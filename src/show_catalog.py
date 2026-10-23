import duckdb
import pandas as pd

pd.set_option("display.max_colwidth", None)
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", None)

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

# Do the two copies match?
for schema in ["raw", "clean"]:
    n = con.execute(f"SELECT COUNT(*) FROM {schema}.dq_checks_catalog").fetchone()[0]
    print(schema, "row count:", n)

# Show the full catalog
print()
print(con.execute("SELECT * FROM raw.dq_checks_catalog").df().to_string())