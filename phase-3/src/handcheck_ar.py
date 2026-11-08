import duckdb
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
print(con.execute("""SELECT invoice_id, total_amount, amount_paid, balance_due,
       days_past_due_at_cutoff, status FROM wh.fact_invoice
       WHERE status = 'PARTIALLY_PAID'""").fetchall())