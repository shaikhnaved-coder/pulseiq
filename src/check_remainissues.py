import duckdb

DB = "05_Starter/pulseiq.duckdb"
con = duckdb.connect(DB, read_only=True)

print("\n========== DQ-04: LEDGER BALANCE ==========")

print(
con.execute(
"""
SELECT
entry_id,
SUM(debit) AS total_debits,
SUM(credit) AS total_credits,
ROUND(SUM(debit) - SUM(credit), 2) AS difference,
COUNT(*) AS ledger_lines
FROM raw.fact_ledger
WHERE entry_id = 'JE-002094'
GROUP BY entry_id
"""
).fetchdf().to_string(index=False)
)

print("\n========== DQ-11: EMPLOYEE HISTORY COLUMNS ==========")

print(
con.execute("DESCRIBE raw.dim_employee").fetchdf().to_string(index=False)
)

print("\n========== DQ-11: EMPLOYEE HISTORY EXAMPLES ==========")

print(
con.execute(
"""
SELECT employee_id, employee_key, valid_from, valid_to
FROM raw.dim_employee
ORDER BY employee_id, valid_from
LIMIT 15
"""
).fetchdf().to_string(index=False)
)

print("\n========== DQ-11: OVERLAPPING EMPLOYEE HISTORY ==========")

print(
con.execute(
"""
SELECT
a.employee_id,
a.employee_key AS key_a,
a.valid_from AS from_a,
a.valid_to AS to_a,
b.employee_key AS key_b,
b.valid_from AS from_b,
b.valid_to AS to_b
FROM raw.dim_employee a
JOIN raw.dim_employee b
ON a.employee_id = b.employee_id
AND a.employee_key < b.employee_key
AND COALESCE(a.valid_to, DATE '9999-12-31') >= b.valid_from
ORDER BY a.employee_id
LIMIT 20
"""
).fetchdf().to_string(index=False)
)

con.close()
