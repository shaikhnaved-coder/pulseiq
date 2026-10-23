import sys
import uuid
from datetime import datetime, timedelta

import duckdb

DB = "05_Starter/pulseiq.duckdb"

# C13 needs a cutoff time: anything older than 24 hours is stale
cutoff = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

# (check_id, check_name, table, severity, SQL that returns the BAD rows)
CHECKS = [
("DQ-C01", "Payroll equals ledger", "fact_payroll + fact_ledger", "Critical", """
    WITH p AS (
        SELECT strftime(CAST(period_end_date AS DATE), '%Y-%m') AS month,
               SUM(CAST(employer_cost AS DOUBLE)) AS cost
        FROM {s}.fact_payroll GROUP BY 1
    ),
    l AS (
        SELECT strftime(CAST(entry_date AS DATE), '%Y-%m') AS month,
               SUM(CAST(debit AS DOUBLE) - CAST(credit AS DOUBLE)) AS expense
        FROM {s}.fact_ledger
        WHERE CAST(account_code AS VARCHAR) IN ('5001','5002','5003','5004','5005')
        GROUP BY 1
    )
    SELECT p.month FROM p LEFT JOIN l USING (month)
    WHERE ABS(ROUND(p.cost - COALESCE(l.expense, 0), 2)) > 0.01
"""),
("DQ-C02", "Ledger balanced", "fact_ledger", "Critical", """
    SELECT entry_id FROM {s}.fact_ledger
    GROUP BY entry_id
    HAVING ABS(SUM(debit) - SUM(credit)) > 0.005
"""),
("DQ-C03", "Unique payroll rows", "fact_payroll", "Critical", """
    SELECT employee_id, run_id FROM {s}.fact_payroll
    GROUP BY employee_id, run_id HAVING COUNT(*) > 1
"""),
("DQ-C04", "No orphan employees", "fact_payroll", "Critical", """
    SELECT DISTINCT f.employee_id
    FROM {s}.fact_payroll f
    LEFT JOIN {s}.dim_employee d ON f.employee_id = d.employee_id
    WHERE d.employee_id IS NULL
"""),
("DQ-C05", "No attendance after exit", "fact_attendance_monthly", "Warning", """
    SELECT a.attendance_fact_id
    FROM {s}.fact_attendance_monthly a
    JOIN {s}.dim_employee d
      ON a.employee_id = d.employee_id AND d.is_current = 'Y'
    WHERE d.exit_date IS NOT NULL
      AND a.period_end_date > LAST_DAY(d.exit_date)
"""),
("DQ-C06", "Unpaid leave deducted", "fact_attendance_monthly + fact_payroll", "Warning", """
    WITH attendance AS (
        SELECT
            employee_id,
            CAST(period_end_date AS DATE) AS period_end_date,
            SUM(COALESCE(CAST(unpaid_absence_days AS DOUBLE), 0))
                AS unpaid_days
        FROM {s}.fact_attendance_monthly
        GROUP BY 1, 2
    ),
    payroll AS (
        SELECT
            employee_id,
            CAST(period_end_date AS DATE) AS period_end_date,
            SUM(COALESCE(CAST(lop_days AS DOUBLE), 0))
                AS lop_days
        FROM {s}.fact_payroll
        GROUP BY 1, 2
    )
    SELECT
        a.employee_id,
        a.period_end_date
    FROM attendance a
    LEFT JOIN payroll p
      ON a.employee_id = p.employee_id
     AND a.period_end_date = p.period_end_date
    WHERE a.unpaid_days > 0.5
      AND COALESCE(p.lop_days, 0) < a.unpaid_days - 0.5
"""),

("DQ-C07", "Invoice arithmetic", "fact_invoice", "Warning", """
    SELECT invoice_id FROM {s}.fact_invoice
    WHERE amount_paid > total_amount OR balance_due < 0
"""),
("DQ-C08", "Expense arithmetic", "fact_expense", "Warning", """
    SELECT expense_id FROM {s}.fact_expense
    WHERE ABS(total_amount - (amount_excl_gst + gst_amount)) > 0.01
"""),
("DQ-C09", "Task dates sensible", "fact_task", "Warning", """
    SELECT task_id FROM {s}.fact_task
    WHERE completed_date < started_date
       OR (status = 'Done' AND completed_date IS NULL)
"""),
("DQ-C10", "Leave dates sensible", "fact_leave", "Warning", """
    SELECT leave_request_id FROM {s}.fact_leave
    WHERE end_date < start_date
"""),
("DQ-C11", "AI feeds are fresh", "fact_attrition_risk", "Warning", """
    SELECT prediction_id FROM {s}.fact_attrition_risk
    WHERE as_of_date < (SELECT MAX(as_of_date) FROM {s}.fact_attrition_risk) - 7
"""),
("DQ-C12", "History does not overlap", "dim_employee", "Critical", """
    SELECT a.employee_key
    FROM {s}.dim_employee a
    JOIN {s}.dim_employee b
      ON a.employee_id = b.employee_id
     AND a.employee_key <> b.employee_key
     AND a.valid_from < b.valid_from
    WHERE COALESCE(a.valid_to, DATE '9999-12-31') > b.valid_from
"""),
("DQ-C13", "Pipeline freshness", "etl.summary", "Critical", f"""
    SELECT MAX(CAST(run_at AS TIMESTAMP)) AS last_load
    FROM etl.summary
    HAVING MAX(CAST(run_at AS TIMESTAMP)) < TIMESTAMP '{cutoff}'
"""),

("DQ-C14", "Minimum group size", "fact_payroll + fact_task", "Warning", """
    WITH payroll_groups AS (
        SELECT
            department_id AS group_id,
            strftime(CAST(period_end_date AS DATE), '%Y-%m') AS grp,
            COUNT(DISTINCT employee_id) AS group_size
        FROM {s}.fact_payroll
        GROUP BY 1, 2
    ),
    task_groups AS (
        SELECT
            team_id AS group_id,
            CAST(sprint_id AS VARCHAR) AS grp,
            COUNT(*) AS group_size
        FROM {s}.fact_task
        GROUP BY 1, 2
    )
    SELECT group_id, grp, group_size
    FROM payroll_groups
    WHERE group_size < 5

    UNION ALL

    SELECT group_id, grp, group_size
    FROM task_groups
    WHERE group_size < 5
"""),

]


def run_all(db_path=DB, schema="wh"):
    con = duckdb.connect(db_path)   # needs write access to save results
    con.execute("CREATE SCHEMA IF NOT EXISTS dq")
    con.execute("""
        CREATE TABLE IF NOT EXISTS dq.dq_results (
            run_id     VARCHAR,
            run_time   TIMESTAMP,
            check_id   VARCHAR,
            check_name VARCHAR,
            table_name VARCHAR,
            severity   VARCHAR,
            bad_rows   BIGINT,
            status     VARCHAR
        )
    """)

    run_id = uuid.uuid4().hex[:8]
    run_time = datetime.now()
    results = []

    for check_id, name, table, severity, sql in CHECKS:
        try:
            bad = con.execute(
                f"SELECT COUNT(*) FROM ({sql.format(s=schema)})"
            ).fetchone()[0]
            status = "PASS" if bad == 0 else "FAIL"
        except Exception as e:
            bad, status = -1, "ERROR"
            print(f"  {check_id} crashed: {str(e)[:150]}")
        results.append((check_id, name, table, severity, bad, status))
        con.execute(
            "INSERT INTO dq.dq_results VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [run_id, run_time, check_id, name, table, severity, bad, status],
        )

    con.close()
    return run_id, run_time, results


def print_summary(run_id, run_time, results):
    print(f"\nDATA QUALITY REPORT   run {run_id}   {run_time:%Y-%m-%d %H:%M:%S}")
    print("-" * 78)
    print(f"{'check':8} {'name':28} {'severity':9} {'bad rows':>9}  status")
    print("-" * 78)
    for cid, name, table, sev, bad, status in results:
        print(f"{cid:8} {name:28} {sev:9} {bad:>9}  {status}")
    print("-" * 78)

    passed = sum(1 for r in results if r[5] == "PASS")
    failed = [r for r in results if r[5] != "PASS"]
    critical = [r for r in failed if r[3] == "Critical"]
    print(f"{passed} passed, {len(failed)} failed or errored "
          f"({len(critical)} critical)")
    print("GATE:", "BLOCKED (critical check failed)" if critical else "OPEN")
    return 1 if critical else 0


if __name__ == "__main__":
    run_id, run_time, results = run_all()
    sys.exit(print_summary(run_id, run_time, results))