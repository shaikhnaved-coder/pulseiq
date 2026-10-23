import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

# How is 'Done' written in the task table?
print("task status values:",
      con.execute("SELECT DISTINCT status FROM wh.fact_task").fetchall())

checks = {
"DQ-C07 Invoice arithmetic": """
    SELECT invoice_id FROM {s}.fact_invoice
    WHERE amount_paid > total_amount OR balance_due < 0
""",
"DQ-C08 Expense arithmetic": """
    SELECT expense_id FROM {s}.fact_expense
    WHERE ABS(total_amount - (amount_excl_gst + gst_amount)) > 0.01
""",
"DQ-C09 Task dates sensible": """
    SELECT task_id FROM {s}.fact_task
    WHERE completed_date < started_date
       OR (status = 'Done' AND completed_date IS NULL)
""",
"DQ-C10 Leave dates sensible": """
    SELECT leave_request_id FROM {s}.fact_leave
    WHERE end_date < start_date
""",
}

print(f"{'check':35} {'raw':>8} {'wh':>8}")
for name, sql in checks.items():
    counts = []
    for s in ["raw", "wh"]:
        try:
            n = con.execute(f"SELECT COUNT(*) FROM ({sql.format(s=s)})").fetchone()[0]
        except Exception as e:
            n = "ERR"
            print("  error on", s, ":", str(e)[:150])
        counts.append(n)
    print(f"{name:35} {counts[0]:>8} {counts[1]:>8}")