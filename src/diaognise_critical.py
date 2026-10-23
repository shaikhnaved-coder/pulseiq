
import duckdb

DB = "05_Starter/pulseiq.duckdb"

con = duckdb.connect(DB, read_only=True)

print("\n========== DQ-C01: PAYROLL VS LEDGER ==========")

query_c01 = """
SELECT *
FROM wh.fact_ledger
WHERE entry_id = 'JE-002094'
  AND CAST(account_code AS VARCHAR) = '5001'
ORDER BY debit DESC
"""

try:
    rows = con.execute(query_c01).fetchdf()
    print(rows.to_string(index=False))
except Exception as e:
    print("DQ-C01 diagnostic error:", e)

print("\n========== DQ-C12: EMPLOYEE HISTORY OVERLAP ==========")

query_c12 = """
SELECT
    a.employee_id,
    a.employee_key AS first_key,
    a.valid_from AS first_valid_from,
    a.valid_to AS first_valid_to,
    b.employee_key AS second_key,
    b.valid_from AS second_valid_from,
    b.valid_to AS second_valid_to
FROM wh.dim_employee a
JOIN wh.dim_employee b
    ON a.employee_id = b.employee_id
   AND a.employee_key <> b.employee_key
   AND a.valid_from < b.valid_from
WHERE COALESCE(a.valid_to, DATE '9999-12-31') >= b.valid_from
ORDER BY a.employee_id, a.valid_from
"""

try:
    rows = con.execute(query_c12).fetchdf()
    print(rows.to_string(index=False))
except Exception as e:
    print("DQ-C12 diagnostic error:", e)


print("\n========== JUNE PAYROLL RECONCILIATION ==========")

query = """
WITH payroll AS (
    SELECT
        department_id,
        ROUND(SUM(
            CAST(basic AS DOUBLE)
            + CAST(hra AS DOUBLE)
            + CAST(conveyance AS DOUBLE)
            + CAST(medical AS DOUBLE)
            + CAST(special_allowance AS DOUBLE)
        ), 2) AS payroll_fixed_pay
    FROM wh.fact_payroll
    WHERE strftime(CAST(period_end_date AS DATE), '%Y-%m') = '2026-06'
    GROUP BY department_id
),
ledger AS (
    SELECT
        cost_center_department_id AS department_id,
        ROUND(SUM(CAST(debit AS DOUBLE) - CAST(credit AS DOUBLE)), 2)
            AS ledger_fixed_pay
    FROM wh.fact_ledger
    WHERE posting_period = '2026-06'
      AND CAST(account_code AS VARCHAR) = '5001'
      AND source_type = 'PAYROLL_RUN'
    GROUP BY cost_center_department_id
)
SELECT
    COALESCE(p.department_id, l.department_id) AS department_id,
    p.payroll_fixed_pay,
    l.ledger_fixed_pay,
    ROUND(
        COALESCE(l.ledger_fixed_pay, 0)
        - COALESCE(p.payroll_fixed_pay, 0), 2
    ) AS difference
FROM payroll p
FULL OUTER JOIN ledger l USING (department_id)
ORDER BY department_id
"""

try:
    print(con.execute(query).fetchdf().to_string(index=False))
except Exception as e:
    print("Reconciliation error:", e)


print("\n========== D01 JUNE PAYROLL SOURCE ==========")

query = """
SELECT *
FROM wh.fact_payroll
WHERE department_id = 'D01'
  AND strftime(CAST(period_end_date AS DATE), '%Y-%m') = '2026-06'
ORDER BY employee_id
"""

try:
    print(con.execute(query).fetchdf().to_string(index=False))
except Exception as e:
    print("Payroll inspection error:", e)


con.close()

