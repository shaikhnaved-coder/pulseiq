import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

print("1) D10 rows in m04_attrition_monthly (Apr 2025 onward):")
print(con.execute("""
    SELECT month_start_date, attrition_pct, group_size
    FROM metrics.m04_attrition_monthly
    WHERE department_id = 'D10' AND month_start_date >= DATE '2025-04-01'
    ORDER BY month_start_date
""").df().to_string())

print()
print("2) D10 rows in m03_exits (Apr 2025 onward):")
print(con.execute("""
    SELECT month_start_date, exits, group_size
    FROM metrics.m03_exits
    WHERE department_id = 'D10' AND month_start_date >= DATE '2025-04-01'
    ORDER BY month_start_date
""").df().to_string())

print()
print("3) D10 headcount in the attendance view (group_size by month):")
print(con.execute("""
    SELECT month_start_date, group_size
    FROM metrics.m13_attendance_rate
    WHERE department_id = 'D10'
    ORDER BY month_start_date
""").df().to_string())

print()
print("4) Smallest group_size anywhere in m04 (all departments, all months):")
print(con.execute("""
    SELECT MIN(group_size) AS min_group, COUNT(*) AS n_rows
    FROM metrics.m04_attrition_monthly
""").df().to_string())