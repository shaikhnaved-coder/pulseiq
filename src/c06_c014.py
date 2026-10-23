import duckdb

con = duckdb.connect(
    "05_Starter/pulseiq.duckdb",
    read_only=True
)

print("\n--- Metric dictionary minimum group sizes ---")

print(con.execute("""
    SELECT
        metric_id,
        metric_name,
        source_table,
        grain,
        minimum_group_size
    FROM clean.metric_dictionary
    ORDER BY metric_id
""").fetchall())

print("\n--- Payroll group counts ---")

print(con.execute("""
    SELECT
        department_id,
        strftime(CAST(period_end_date AS DATE), '%Y-%m') AS month,
        COUNT(DISTINCT employee_id) AS employee_count
    FROM wh.fact_payroll
    GROUP BY 1, 2
    ORDER BY employee_count, department_id, month
    LIMIT 20
""").fetchall())

print("\n--- Task group counts ---")

print(con.execute("""
    SELECT
        team_id,
        sprint_id,
        COUNT(*) AS task_count
    FROM wh.fact_task
    GROUP BY 1, 2
    ORDER BY task_count, team_id, sprint_id
    LIMIT 20
""").fetchall())

con.close()