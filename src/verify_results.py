import duckdb

DB = "05_Starter/pulseiq.duckdb"

con = duckdb.connect(DB, read_only=True)

print("\n========== VERIFY SAVED DQ RESULTS ==========\n")

results = con.execute("""
SELECT
run_id,
run_time,
COUNT(*) AS total_checks,
SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) AS passed,
SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) AS failed,
SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) AS errors
FROM dq.dq_results
GROUP BY run_id, run_time
ORDER BY run_time DESC
LIMIT 5
""").fetchall()

for row in results:
    print(
        f"Run ID: {row[0]} | Time: {row[1]} | "
        f"Total: {row[2]} | Passed: {row[3]} | "
        f"Failed: {row[4]} | Errors: {row[5]}"
    )
con.close()

print("\n========== VERIFICATION COMPLETED ==========\n")
