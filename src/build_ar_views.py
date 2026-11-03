import duckdb
con = duckdb.connect("05_Starter/pulseiq.duckdb")
con.execute("CREATE SCHEMA IF NOT EXISTS metrics")

# Rule: only SENT, OVERDUE, PARTIALLY_PAID are open. Open amount = balance_due.
con.execute("""
CREATE OR REPLACE VIEW metrics.v_ar_open AS
SELECT i.invoice_id, i.client_id, c.client_name, i.status, i.invoice_date, i.due_date,
       i.total_amount, i.amount_paid, i.balance_due AS open_amount,
       COALESCE(i.days_past_due_at_cutoff, 0) AS days_past_due,
       CASE WHEN COALESCE(i.days_past_due_at_cutoff, 0) <= 30 THEN '0-30'
            WHEN i.days_past_due_at_cutoff <= 60 THEN '31-60'
            WHEN i.days_past_due_at_cutoff <= 90 THEN '61-90'
            ELSE '90+' END AS bucket
FROM wh.fact_invoice i LEFT JOIN wh.dim_client c USING (client_id)
WHERE upper(i.status) IN ('SENT','OVERDUE','PARTIALLY_PAID')
""")

# All four buckets always appear, even when one is empty (shows 0)
con.execute("""
CREATE OR REPLACE VIEW metrics.v_ar_ageing AS
SELECT b.bucket,
       count(o.invoice_id) AS invoices,
       COALESCE(sum(o.open_amount), 0) AS open_amount
FROM (VALUES ('0-30',1), ('31-60',2), ('61-90',3), ('90+',4)) b(bucket, sort_order)
LEFT JOIN metrics.v_ar_open o ON o.bucket = b.bucket
GROUP BY b.bucket, b.sort_order
ORDER BY b.sort_order
""")

con.execute("""
CREATE OR REPLACE VIEW metrics.v_days_to_pay AS
SELECT c.client_name AS client, count(*) AS paid_invoices,
       round(avg(i.days_to_pay), 1) AS avg_days_to_pay
FROM wh.fact_invoice i LEFT JOIN wh.dim_client c USING (client_id)
WHERE i.days_to_pay IS NOT NULL
GROUP BY 1
""")

# Cash in = payments received. Cash out = monthly expenses from the P&L view.
con.execute("""
CREATE OR REPLACE VIEW metrics.v_cash_monthly AS
WITH cin AS (SELECT strftime(payment_date, '%Y-%m') AS month, sum(amount) AS cash_in
             FROM wh.fact_invoice_payment GROUP BY 1),
     cout AS (SELECT CAST(month AS VARCHAR) AS month, sum(expenses) AS cash_out
              FROM metrics.v_pl_monthly GROUP BY 1)
SELECT COALESCE(cin.month, cout.month) AS month,
       round(COALESCE(cash_in, 0), 2) AS cash_in,
       round(COALESCE(cash_out, 0), 2) AS cash_out,
       round(COALESCE(cash_in, 0) - COALESCE(cash_out, 0), 2) AS net_cash
FROM cin FULL OUTER JOIN cout USING (month)
ORDER BY 1
""")

con.execute("""
CREATE OR REPLACE VIEW metrics.v_overdue_by_client AS
SELECT client_name AS client, count(*) AS overdue_invoices, sum(open_amount) AS overdue_amount
FROM metrics.v_ar_open WHERE upper(status) = 'OVERDUE'
GROUP BY 1 ORDER BY overdue_amount DESC
""")
print("AR views built")