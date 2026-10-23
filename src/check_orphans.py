import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

def has_col(table, col):
    n = con.sql(f"""SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = 'wh' AND table_name = '{table}' AND column_name = '{col}'""").fetchone()[0]
    return n == 1

def one(sql):
    return con.sql(sql).fetchone()[0]

LINKS = [
    ("fact_payroll", "employee_key", "dim_employee", "employee_key"),
    ("fact_payroll", "date_key", "dim_date", "date_key"),
    ("fact_payroll", "department_id", "dim_department", "department_id"),
    ("fact_payroll", "role_id", "dim_role", "role_id"),
    ("fact_attendance_monthly", "employee_key", "dim_employee", "employee_key"),
    ("fact_attendance_monthly", "date_key", "dim_date", "date_key"),
    ("fact_attendance_monthly", "department_id", "dim_department", "department_id"),
    ("fact_leave", "employee_key", "dim_employee", "employee_key"),
    ("fact_leave", "leave_type_code", "dim_leave_type", "leave_type_code"),
    ("fact_leave", "start_date_key", "dim_date", "date_key"),
    ("fact_leave", "end_date_key", "dim_date", "date_key"),
    ("fact_headcount_monthly", "department_id", "dim_department", "department_id"),
    ("fact_headcount_monthly", "date_key", "dim_date", "date_key"),
    ("fact_ledger", "account_code", "dim_account", "account_code"),
    ("fact_ledger", "cost_center_department_id", "dim_department", "department_id"),
    ("fact_ledger", "date_key", "dim_date", "date_key"),
    ("fact_invoice", "client_id", "dim_client", "client_id"),
    ("fact_invoice", "service_line_account", "dim_account", "account_code"),
    ("fact_invoice", "invoice_date_key", "dim_date", "date_key"),
    ("fact_invoice_payment", "payment_date_key", "dim_date", "date_key"),
    ("fact_expense", "vendor_id", "dim_vendor", "vendor_id"),
    ("fact_expense", "category_account", "dim_account", "account_code"),
    ("fact_expense", "department_id", "dim_department", "department_id"),
    ("fact_expense", "expense_date_key", "dim_date", "date_key"),
    ("fact_task", "team_id", "dim_team", "team_id"),
    ("fact_task", "sprint_id", "dim_sprint", "sprint_id"),
    ("fact_task", "employee_key", "dim_employee", "employee_key"),
    ("fact_task", "assignee_employee_id", "dim_employee", "employee_id"),
    ("fact_anomaly", "employee_key", "dim_employee", "employee_key"),
    ("fact_anomaly", "employee_id", "dim_employee", "employee_id"),
    ("fact_anomaly", "period_key", "dim_date", "date_key"),
    ("fact_attrition_risk", "employee_key", "dim_employee", "employee_key"),
    ("fact_attrition_risk", "department_id", "dim_department", "department_id"),
    ("fact_attrition_risk", "as_of_date_key", "dim_date", "date_key"),
    ("fact_forecast", "department_id", "dim_department", "department_id"),
    ("fact_forecast", "forecast_month_key", "dim_date", "date_key"),
]

total = 0
for fact, fk, dim, pk in LINKS:
    if not has_col(fact, fk) or not has_col(dim, pk):
        print(f"SKIPPED {fact}.{fk} -> {dim}.{pk} (column not found)")
        continue
    rows = one(f"SELECT COUNT(*) FROM wh.{fact}")
    nulls = one(f"SELECT COUNT(*) FROM wh.{fact} WHERE {fk} IS NULL")
    sub = f"SELECT {pk} FROM wh.{dim} WHERE {pk} IS NOT NULL"
    missing = one(f"SELECT COUNT(*) FROM wh.{fact} WHERE {fk} IS NOT NULL AND {fk} NOT IN ({sub})")
    flag = "" if nulls + missing == 0 else "   <-- LOOK"
    print(f"{fact}.{fk} -> {dim}.{pk}: rows={rows} null={nulls} no_match={missing}{flag}")
    if missing:
        vals = con.sql(f"""SELECT DISTINCT {fk} FROM wh.{fact}
            WHERE {fk} IS NOT NULL AND {fk} NOT IN ({sub}) LIMIT 5""").fetchall()
        print("    example unmatched values:", [v[0] for v in vals])
    total += nulls + missing
print("\nTOTAL ORPHAN ROWS:", total)

print("\n--- Business-rule checks (not orphans) ---")
print("payroll employee-months repeated:", one(
    "SELECT COUNT(*) FROM (SELECT employee_id, date_key FROM wh.fact_payroll GROUP BY 1, 2 HAVING COUNT(*) > 1)"))
print("attendance employee-months repeated:", one(
    "SELECT COUNT(*) FROM (SELECT employee_id, date_key FROM wh.fact_attendance_monthly GROUP BY 1, 2 HAVING COUNT(*) > 1)"))
print("attendance rows in a month after the exit month:", one("""
    SELECT COUNT(*) FROM wh.fact_attendance_monthly f
    JOIN wh.dim_employee e ON f.employee_key = e.employee_key
    WHERE e.exit_date IS NOT NULL
      AND DATE_TRUNC('month', f.period_end_date) > DATE_TRUNC('month', e.exit_date)"""))
print("attendance months with no payroll row:", one("""
    SELECT COUNT(*) FROM wh.fact_attendance_monthly a WHERE NOT EXISTS
    (SELECT 1 FROM wh.fact_payroll p WHERE p.employee_id = a.employee_id AND p.date_key = a.date_key)"""))
print("payroll months with no attendance row:", one("""
    SELECT COUNT(*) FROM wh.fact_payroll p WHERE NOT EXISTS
    (SELECT 1 FROM wh.fact_attendance_monthly a WHERE p.employee_id = a.employee_id AND p.date_key = a.date_key)"""))
for r in con.sql("""
    SELECT p.payroll_item_id, p.employee_id, p.date_key FROM wh.fact_payroll p WHERE NOT EXISTS
    (SELECT 1 FROM wh.fact_attendance_monthly a WHERE p.employee_id = a.employee_id AND p.date_key = a.date_key)
    LIMIT 5""").fetchall():
    print("    payroll without attendance:", r)