import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

print("Ledger sample rows for salary accounts:")
print(con.execute("""
    SELECT entry_id, entry_date, posting_period, account_code, debit, credit
    FROM wh.fact_ledger
    WHERE CAST(account_code AS VARCHAR) IN ('5001','5002','5003','5004','5005')
    LIMIT 8
""").df().to_string())

print("\nMonthly comparison (payroll vs ledger):")
print(con.execute("""
    WITH p AS (
        SELECT strftime(CAST(period_end_date AS DATE), '%Y-%m') AS month,
               SUM(employer_cost) AS payroll_cost
        FROM wh.fact_payroll
        GROUP BY 1
    ),
    l AS (
        SELECT strftime(CAST(entry_date AS DATE), '%Y-%m') AS month,
               SUM(debit - credit) AS ledger_expense
        FROM wh.fact_ledger
        WHERE CAST(account_code AS VARCHAR) IN ('5001','5002','5003','5004','5005')
        GROUP BY 1
    )
    SELECT p.month, p.payroll_cost, l.ledger_expense,
           p.payroll_cost - l.ledger_expense AS diff
    FROM p LEFT JOIN l USING (month)
    ORDER BY p.month
""").df().to_string())