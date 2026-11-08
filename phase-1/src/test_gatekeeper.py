import duckdb

DB = "05_Starter/pulseiq.duckdb"

con = duckdb.connect(DB)

print("\n========== GATEKEEPER TESTS ==========\n")

# TEST 1: Check that all 14 checks exist
result = con.execute("""
    SELECT COUNT(DISTINCT check_id)
    FROM dq.dq_results
""").fetchone()[0]

print("Test 1: Number of checks =", result)
assert result == 14, "Expected 14 distinct checks"
print("PASS: All 14 checks exist.\n")


# TEST 2: Check that every check has a valid status
result = con.execute("""
    SELECT COUNT(*)
    FROM dq.dq_results
    WHERE status NOT IN ('PASS', 'FAIL', 'ERROR')
       OR status IS NULL
""").fetchone()[0]

print("Test 2: Invalid statuses =", result)
assert result == 0, "Invalid statuses found"
print("PASS: All statuses are valid.\n")


# TEST 3: Check that no check has a negative bad-row count,
# except -1, which your gatekeeper uses when a check errors
result = con.execute("""
    SELECT COUNT(*)
    FROM dq.dq_results
    WHERE bad_rows < 0 AND NOT (bad_rows = -1 AND status = 'ERROR')
""").fetchone()[0]

print("Test 3: Invalid bad-row counts =", result)
assert result == 0, "Unexpected negative bad-row count"
print("PASS: Bad-row counts are valid.\n")


# TEST 4: Check that ERROR status matches bad_rows = -1
result = con.execute("""
    SELECT COUNT(*)
    FROM dq.dq_results
    WHERE (status = 'ERROR' AND bad_rows <> -1)
       OR (status <> 'ERROR' AND bad_rows = -1)
""").fetchone()[0]

print("Test 4: Inconsistent error records =", result)
assert result == 0, "Error status and bad-row count disagree"
print("PASS: Error records are consistent.\n")


# TEST 5: Check that PASS means zero bad rows
result = con.execute("""
    SELECT COUNT(*)
    FROM dq.dq_results
    WHERE status = 'PASS' AND bad_rows <> 0
""").fetchone()[0]

print("Test 5: Incorrect PASS records =", result)
assert result == 0, "A PASS check has a nonzero bad-row count"
print("PASS: PASS records have zero bad rows.\n")


# TEST 6: Check that FAIL means at least one bad row
result = con.execute("""
    SELECT COUNT(*)
    FROM dq.dq_results
    WHERE status = 'FAIL' AND bad_rows <= 0
""").fetchone()[0]

print("Test 6: Incorrect FAIL records =", result)
assert result == 0, "A FAIL check has no positive bad-row count"
print("PASS: FAIL records have positive bad-row counts.\n")


# TEST 7: Check that every expected check ID exists
expected_ids = [
    "DQ-C01", "DQ-C02", "DQ-C03", "DQ-C04",
    "DQ-C05", "DQ-C06", "DQ-C07", "DQ-C08",
    "DQ-C09", "DQ-C10", "DQ-C11", "DQ-C12",
    "DQ-C13", "DQ-C14"
]

actual_ids = {
    row[0]
    for row in con.execute("""
        SELECT DISTINCT check_id
        FROM dq.dq_results
    """).fetchall()
}

missing_ids = set(expected_ids) - actual_ids

print("Test 7: Missing check IDs =", sorted(missing_ids))
assert not missing_ids, "Some expected check IDs are missing"
print("PASS: All expected check IDs exist.\n")


# TEST 8: Check that critical failures block the gate
critical_failures = con.execute("""
    SELECT COUNT(*)
    FROM dq.dq_results
    WHERE severity = 'Critical'
      AND status <> 'PASS'
""").fetchone()[0]

print("Test 8: Critical failures =", critical_failures)

if critical_failures > 0:
    print("PASS: Critical failures should block the gate.\n")
else:
    print("INFO: No critical failures in the selected results.\n")


# TEST 9: Check the expected number of PASS and FAIL results
counts = con.execute("""
    SELECT status, COUNT(*)
    FROM dq.dq_results
    GROUP BY status
""").fetchall()

print("Test 9: Status counts =", counts)
print("INFO: Counts include all saved runs, if multiple runs exist.\n")


# TEST 10: Display the latest run's results
latest_run = con.execute("""
    SELECT run_id
    FROM dq.dq_results
    ORDER BY run_time DESC
    LIMIT 1
""").fetchone()

if latest_run:
    run_id = latest_run[0]

    print("Test 10: Latest run =", run_id)

    rows = con.execute("""
        SELECT check_id, check_name, bad_rows, status
        FROM dq.dq_results
        WHERE run_id = ?
        ORDER BY check_id
    """, [run_id]).fetchall()

    for row in rows:
        print(row)

    print("\nPASS: Latest run results retrieved.\n")
else:
    print("Test 10: No saved results found.\n")


# TEST 11: Check that the latest run contains exactly 14 results

result = con.execute("""
    SELECT COUNT(*)
    FROM dq.dq_results
    WHERE run_id = (
        SELECT run_id
        FROM dq.dq_results
        ORDER BY run_time DESC
        LIMIT 1
    )
""").fetchone()[0]

print("Test 11: Results in latest run =", result)

assert result == 14, "Expected exactly 14 results in the latest run"

print("PASS: Latest run contains all 14 results.\n")


# TEST 12: Check that critical failures exist in the latest run

result = con.execute("""
    SELECT COUNT(*)
    FROM dq.dq_results
    WHERE run_id = (
        SELECT run_id
        FROM dq.dq_results
        ORDER BY run_time DESC
        LIMIT 1
    )
    AND severity = 'Critical'
    AND status <> 'PASS'
""").fetchone()[0]

print("Test 12: Critical failures in latest run =", result)

if result > 0:
    print("PASS: Critical failures were identified.\n")
else:
    print("INFO: No critical failures found in latest run.\n")


# TEST 13: Check that the latest run has no ERROR statuses

result = con.execute("""
    SELECT COUNT(*)
    FROM dq.dq_results
    WHERE run_id = (
        SELECT run_id
        FROM dq.dq_results
        ORDER BY run_time DESC
        LIMIT 1
    )
    AND status = 'ERROR'
""").fetchone()[0]

print("Test 13: Errors in latest run =", result)

if result == 0:
    print("PASS: All checks executed without SQL errors.\n")
else:
    print("FAIL: Some checks encountered SQL errors.\n")


con.close()


print("========== TESTS COMPLETED ==========")