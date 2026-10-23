import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

tables = ["fact_ledger", "fact_payroll", "dim_employee", "fact_attendance",
          "fact_invoice", "fact_expense", "fact_task", "fact_leave",
          "fact_attrition_risk", "etl_run_log", "payroll", "ledger"]

for t in tables:
    rows = con.execute("""
        SELECT table_schema, column_name
        FROM information_schema.columns
        WHERE table_name = ?
        ORDER BY table_schema, ordinal_position
    """, [t]).fetchall()
    print("\n" + t)
    print(rows if rows else "  NOT FOUND")