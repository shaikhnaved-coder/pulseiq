import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

tables = [
"fact_attendance_monthly",
"fact_payroll",
"fact_ledger",
"fact_invoice",
"fact_task",
"fact_leave",
"fact_attrition_risk",
"fact_expense",
"dim_employee"
]

print("\n========== RAW VS WAREHOUSE ROW COUNTS ==========")

for table in tables:
 raw_count = con.execute("SELECT COUNT(*) FROM raw." + table).fetchone()[0]
 wh_count = con.execute("SELECT COUNT(*) FROM wh." + table).fetchone()[0]


 print("\nTable:", table)
 print("RAW rows:", raw_count)
 print("WH rows:", wh_count)

 if raw_count == wh_count:
    print("Result: Same row count")
 else:
    print("Result: Different row counts")


print("\nCOMPARISON COMPLETED")
con.close()


