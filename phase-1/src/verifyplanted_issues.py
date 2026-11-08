import duckdb

DB = "05_Starter/pulseiq.duckdb"

tests = [
("DQ-01", "fact_attendance_monthly", "attendance_fact_id",
["FA-X0001", "FA-X0002", "FA-X0003", "FA-X0004"]),
("DQ-02", "fact_payroll", "payroll_item_id",
["PI-X0001", "PI-X0002"]),
("DQ-03", "fact_payroll", "payroll_item_id",
["PI-X0003", "PI-X0004"]),
("DQ-04", "fact_ledger", "entry_id",
["JE-002094"]),
("DQ-05", "fact_invoice", "invoice_id",
["INV-00385"]),
("DQ-06", "fact_task", "task_id",
["TASK-19891", "TASK-09527", "TASK-06380", "TASK-22599",
"TASK-27674", "TASK-02895", "TASK-17389", "TASK-27078",
"TASK-10799", "TASK-02741", "TASK-07633", "TASK-24674"]),
("DQ-07", "fact_task", "task_id",
["TASK-16893", "TASK-13041", "TASK-17714", "TASK-26149",
"TASK-27926", "TASK-03925", "TASK-17544", "TASK-17195"]),
("DQ-08", "fact_leave", "leave_request_id",
["LR-002286", "LR-000025"]),
("DQ-09", "fact_attrition_risk", "prediction_id",
["AR-0119", "AR-0238", "AR-0221", "AR-0279", "AR-0278"]),
("DQ-10", "fact_expense", "expense_id",
["EXP-00371"]),
("DQ-11", "dim_employee", "employee_key",
["100000"]),
]

con = duckdb.connect(DB, read_only=True)

print("\n========== PLANTED ISSUE RECORD VERIFICATION ==========\n")

for issue_id, table, key, ids in tests:
    print(f"{issue_id} | {table}")

    columns = [
        row[0]
        for row in con.execute(f"DESCRIBE raw.{table}").fetchall()
    ]

    if key not in columns:
        print(f"  Column '{key}' not found.")
        print(f"  Available columns: {columns}\n")
        continue

    placeholders = ", ".join(["?"] * len(ids))

    query = (
        f'SELECT COUNT(*) FROM raw."{table}" '
        f'WHERE CAST("{key}" AS VARCHAR) IN ({placeholders})'
    )

    count = con.execute(query, ids).fetchone()[0]

    print(f"  Expected IDs: {len(ids)}")
    print(f"  Matching rows: {count}\n")

con.close()

print("========== VERIFICATION COMPLETED ==========")