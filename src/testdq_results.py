import duckdb
import importlib.util
from pathlib import Path

# Database path
DB = "05_Starter/pulseiq.duckdb"

print("\n" + "=" * 90)
print("PULSEIQ — ALL 14 DATA QUALITY RULES")
print("=" * 90)

# Load the existing gatekeeper script
gatekeeper_path = Path("src/gatekeeper.py")

if not gatekeeper_path.exists():
    raise FileNotFoundError(
        "Cannot find src/gatekeeper.py. "
        "Run this script from the project root folder."
    )

spec = importlib.util.spec_from_file_location(
    "gatekeeper",
    gatekeeper_path
)

gatekeeper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gatekeeper)

checks = gatekeeper.CHECKS

con = duckdb.connect(DB, read_only=True)

passed = 0
failed = 0
errors = 0

try:
    for check_id, name, table, severity, sql in checks:
        print(f"\n{check_id} — {name}")
        print("-" * 70)

        try:
            # Use the warehouse schema for the SQL checks
            query = sql.format(s="wh")

            # Count the rows returned by the rule
            bad_rows = con.execute(
                f"SELECT COUNT(*) FROM ({query}) AS bad_rows"
            ).fetchone()[0]

            if bad_rows == 0:
                status = "PASS"
                passed += 1
            else:
                status = "FAIL"
                failed += 1

            print("Table:", table)
            print("Severity:", severity)
            print("Bad rows:", bad_rows)
            print("Status:", status)

        except Exception as error:
            errors += 1
            print("Status: ERROR")
            print("Reason:", str(error))

finally:
    con.close()

print("\n" + "=" * 90)
print("FINAL SUMMARY")
print("=" * 90)
print("Total checks:", len(checks))
print("Passed:", passed)
print("Failed:", failed)
print("Errors:", errors)

if errors == 0 and failed == 0:
    print("\nRESULT: All checks passed against the current warehouse.")
elif errors == 0:
    print("\nRESULT: All checks executed, but some found bad rows.")
else:
    print("\nRESULT: Some checks could not execute and need investigation.")

print("=" * 90)