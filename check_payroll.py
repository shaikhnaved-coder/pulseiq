import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

print("\n========== TEST 1: DUPLICATE PAYROLL RECORDS ==========")

query_duplicates = """
SELECT payroll_item_id, COUNT(*) AS occurrences
FROM raw.fact_payroll
GROUP BY payroll_item_id
HAVING COUNT(*) > 1
ORDER BY occurrences DESC
"""

duplicates = con.execute(query_duplicates).fetchdf()

if duplicates.empty:
 print("No duplicate payroll_item_id values found.")
else:
 print(duplicates.to_string(index=False))

print("\n========== TEST 2: ORPHAN EMPLOYEE IDS ==========")

query_orphans = """
SELECT DISTINCT p.employee_id
FROM raw.fact_payroll p
LEFT JOIN raw.dim_employee e
ON p.employee_id = e.employee_id
WHERE e.employee_id IS NULL
ORDER BY p.employee_id
"""

orphans = con.execute(query_orphans).fetchdf()

if orphans.empty:
 print("No orphan employee IDs found in raw payroll.")
else:
 print(orphans.to_string(index=False))

print("\n========== TEST 3: RAW VS WH PAYROLL IDS ==========")

query_missing = """
SELECT r.payroll_item_id
FROM raw.fact_payroll r
LEFT JOIN wh.fact_payroll w
ON r.payroll_item_id = w.payroll_item_id
WHERE w.payroll_item_id IS NULL
ORDER BY r.payroll_item_id
"""

missing = con.execute(query_missing).fetchdf()

print("Payroll IDs in RAW but not in WH:", len(missing))

if not missing.empty:
 print(missing.to_string(index=False))

print("\n========== TEST 4: DETAILS OF EXCLUDED PAYROLL RECORDS ==========")

query_details = """
SELECT
payroll_item_id,
employee_id,
run_id,
period_end_date,
gross_pay,
total_deductions,
net_pay
FROM raw.fact_payroll
WHERE payroll_item_id IN (
'PI-X0001',
'PI-X0002',
'PI-X0003',
'PI-X0004'
)
ORDER BY payroll_item_id
"""

details = con.execute(query_details).fetchdf()

print(details.to_string(index=False))

print("\n========== END OF INSPECTION ==========")

print("\n========== TEST 5: C03 DUPLICATE EMPLOYEE/RUN PAIRS ==========")

duplicates_c03 = con.execute("""
SELECT employee_id, run_id, COUNT(*) AS occurrences
FROM raw.fact_payroll
GROUP BY employee_id, run_id
HAVING COUNT(*) > 1
ORDER BY occurrences DESC
""").fetchdf()

if duplicates_c03.empty:
 print("No duplicate employee_id/run_id pairs found.")
else:
 print(duplicates_c03.to_string(index=False))

print("\n========== TEST 6: C04 ORPHAN EMPLOYEES ==========")

orphans_c04 = con.execute("""
SELECT p.payroll_item_id, p.employee_id
FROM raw.fact_payroll p
LEFT JOIN raw.dim_employee e
ON p.employee_id = e.employee_id
WHERE e.employee_id IS NULL
ORDER BY p.payroll_item_id
""").fetchdf()

if orphans_c04.empty:
 print("No orphan employees found.")
else:
 print(orphans_c04.to_string(index=False))

print("\n========== C03: DUPLICATES IN RAW VS WH ==========")

for schema in ["raw", "wh"]:
 query = """
 SELECT COUNT(*)
 FROM (
 SELECT employee_id, run_id
 FROM """ + schema + """.fact_payroll
 GROUP BY employee_id, run_id
 HAVING COUNT(*) > 1
 ) AS duplicate_pairs
 """


count = con.execute(query).fetchone()[0]
print(f"{schema}: {count} duplicate employee/run pairs")


print("\n========== C04: ORPHANS IN RAW VS WH ==========")

for schema in ["raw", "wh"]:
 query = """
 SELECT COUNT(*)
 FROM """ + schema + """.fact_payroll p
 LEFT JOIN """ + schema + """.dim_employee e
 ON p.employee_id = e.employee_id
 WHERE e.employee_id IS NULL
 """


count = con.execute(query).fetchone()[0]
print(f"{schema}: {count} payroll rows with orphan employees")


con.close()
