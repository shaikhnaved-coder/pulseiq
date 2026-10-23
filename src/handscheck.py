import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)


def show(title, raw_sql, view_sql, how):
    print("=" * 70)
    print(title)
    print("Raw numbers :", con.execute(raw_sql).fetchone())
    print("Calculator  :", how)
    print("View says   :", con.execute(view_sql).fetchone())
    print()


show("1. M04 Attrition, Engineering (D01), Sep 2026",
     "SELECT exits, headcount_start FROM wh.fact_headcount_monthly "
     "WHERE department_id='D01' AND month_start_date='2026-09-01'",
     "SELECT attrition_pct FROM metrics.m04_attrition_monthly "
     "WHERE department_id='D01' AND month_start_date='2026-09-01'",
     "exits / headcount_start x 100")

show("2. M10 Cost per head, Data & AI (D03), Sep 2026",
     "SELECT SUM(employer_cost), COUNT(DISTINCT employee_id) FROM wh.fact_payroll "
     "WHERE department_id='D03' AND period_end_date BETWEEN '2026-09-01' AND '2026-09-30'",
     "SELECT cost_per_head FROM metrics.m10_cost_per_head "
     "WHERE department_id='D03' AND month_start_date='2026-09-01'",
     "total employer cost / employees paid")

show("3. M13 Attendance rate, Sales (D04), Sep 2026",
     "SELECT SUM(present_days), SUM(half_days_unpaid), SUM(scheduled_days) FROM wh.fact_attendance_monthly "
     "WHERE department_id='D04' AND period_end_date BETWEEN '2026-09-01' AND '2026-09-30'",
     "SELECT attendance_rate FROM metrics.m13_attendance_rate "
     "WHERE department_id='D04' AND month_start_date='2026-09-01'",
     "(present + 0.5 x half days) / scheduled")

show("4. M22 Task completion, team T01, sprint SP-01",
     "SELECT COUNT(*) FILTER (WHERE status='Done'), COUNT(*) FILTER (WHERE status<>'Cancelled') "
     "FROM wh.fact_task WHERE team_id='T01' AND sprint_id='SP-01'",
     "SELECT task_completion_pct FROM metrics.m22_task_completion_rate "
     "WHERE team_id='T01' AND sprint_id='SP-01'",
     "done / not cancelled x 100")

show("5. M18 Operating margin, Apr 2025",
     "SELECT -SUM(signed_amount_debit_positive) FILTER (WHERE account_code BETWEEN 4001 AND 4004), "
     "-SUM(signed_amount_debit_positive) FILTER (WHERE account_code BETWEEN 4000 AND 5999) "
     "FROM wh.fact_ledger WHERE entry_date BETWEEN '2025-04-01' AND '2025-04-30'",
     "SELECT operating_margin_pct FROM metrics.m18_operating_margin WHERE month_start_date='2025-04-01'",
     "net profit / revenue x 100   (raw numbers are: revenue first, then net profit)")