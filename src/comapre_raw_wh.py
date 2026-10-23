import duckdb

DB = "05_Starter/pulseiq.duckdb"

TABLES = [
"fact_attendance_monthly",
"fact_payroll",
"fact_ledger",
"fact_invoice",
"fact_task",
"fact_leave",
"fact_attrition_risk",
"fact_expense",
"dim_employee",
]

con = duckdb.connect(DB, read_only=True)

print("\n========== RAW VS WAREHOUSE TABLE COUNTS ==========\n")

for table in TABLES:
 print(f"\n{table}")


for schema in ["raw", "wh"]:
    try:
        query = f'SELECT COUNT(*) FROM "{schema}"."{table}"'
        count = con.execute(query).fetchone()[0]
        print(f"  {schema}: {count} rows")
    except Exception as error:
        print(f"  {schema}: unavailable ({error})")

print("\n========== COMPARISON COMPLETED ==========")

con.close()
