import duckdb

DB_PATH = "05_Starter/pulseiq.duckdb"
SRC = "clean"
con = duckdb.connect(DB_PATH)
con.sql("CREATE SCHEMA IF NOT EXISTS wh")

PKS = {
    "dim_date": ["date_key"], "dim_employee": ["employee_key"],
    "dim_department": ["department_id"], "dim_role": ["role_id"],
    "dim_location": ["work_location"], "dim_leave_type": ["leave_type_code"],
    "dim_account": ["account_code"], "dim_client": ["client_id"],
    "dim_vendor": ["vendor_id"], "dim_team": ["team_id"], "dim_sprint": ["sprint_id"],
    "fact_payroll": ["payroll_item_id"],
    "fact_attendance_monthly": ["attendance_fact_id"],
    "fact_leave": ["leave_request_id"],
    "fact_headcount_monthly": ["date_key", "department_id"],
    "fact_ledger": ["line_id"], "fact_invoice": ["invoice_id"],
    "fact_invoice_payment": ["payment_id"], "fact_expense": ["expense_id"],
    "fact_task": ["task_id"], "fact_anomaly": ["result_id"],
    "fact_attrition_risk": ["prediction_id"], "fact_forecast": ["forecast_id"],
}

END1 = "COALESCE(e1.valid_to, DATE '9999-12-31')"
END2 = "COALESCE(e2.valid_to, DATE '9999-12-31')"

# Facts that only carry employee_id get an employee_key, chosen by date.
EXTRA = {
    "fact_task": f"""
        SELECT t.*, COALESCE(e1.employee_key, e2.employee_key) AS employee_key
        FROM {SRC}.fact_task t
        LEFT JOIN {SRC}.dim_sprint s ON s.sprint_id = t.sprint_id
        LEFT JOIN wh.dim_employee e1 ON e1.employee_id = t.assignee_employee_id
             AND s.end_date >= e1.valid_from AND s.end_date <= {END1}
        LEFT JOIN wh.dim_employee e2 ON e2.employee_id = t.assignee_employee_id
             AND s.start_date >= e2.valid_from AND s.start_date <= {END2}
    """,
    "fact_anomaly": f"""
        SELECT a.*, COALESCE(e1.employee_key, e2.employee_key) AS employee_key
        FROM {SRC}.fact_anomaly a
        LEFT JOIN wh.dim_employee e1 ON e1.employee_id = a.employee_id
             AND CAST(STRPTIME(CAST(a.period_key AS VARCHAR), '%Y%m%d') AS DATE) >= e1.valid_from
             AND CAST(STRPTIME(CAST(a.period_key AS VARCHAR), '%Y%m%d') AS DATE) <= {END1}
        LEFT JOIN wh.dim_employee e2 ON e2.employee_id = a.employee_id
             AND a.period >= e2.valid_from AND a.period <= {END2}
    """,
}

def build(table, pk_cols):
    cols = con.sql(f"""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_schema = '{SRC}' AND table_name = '{table}'
        ORDER BY ordinal_position""").fetchall()
    if not cols:
        raise SystemExit(f"Source table {SRC}.{table} not found.")
    col_ddl = ", ".join(f'"{c}" {t}' for c, t in cols)
    if table in EXTRA:
        col_ddl += ', "employee_key" BIGINT'
        source = EXTRA[table]
    else:
        source = f'SELECT * FROM "{SRC}"."{table}"'
    pk = ", ".join(f'"{c}"' for c in pk_cols)
    con.sql(f"DROP TABLE IF EXISTS wh.{table}")
    con.sql(f"CREATE TABLE wh.{table} ({col_ddl}, PRIMARY KEY ({pk}))")
    con.sql(f"INSERT INTO wh.{table} {source}")

for table, pk_cols in PKS.items():
    build(table, pk_cols)

print(f"{'table':28}{'clean':>9}{'wh':>9}  result")
bad = 0
for table in PKS:
    a = con.sql(f'SELECT COUNT(*) FROM "{SRC}"."{table}"').fetchall()[0][0]
    b = con.sql(f"SELECT COUNT(*) FROM wh.{table}").fetchall()[0][0]
    bad += (a != b)
    print(f"{table:28}{a:>9}{b:>9}  {'OK' if a == b else 'MISMATCH'}")
print()
for t in EXTRA:
    n = con.sql(f"SELECT COUNT(*) FROM wh.{t} WHERE employee_key IS NULL").fetchall()[0][0]
    print(f"{t}: rows with no employee_key = {n}")
print("\nAll tables match." if bad == 0 else f"\n{bad} table(s) do not match.")