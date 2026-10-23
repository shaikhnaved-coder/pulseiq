import duckdb, sys

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

README = {
    "dim_date": 2557, "dim_employee": 1606, "dim_department": 11, "dim_role": 58,
    "dim_location": 9, "dim_leave_type": 6, "dim_account": 47, "dim_client": 28,
    "dim_vendor": 30, "dim_team": 16, "dim_sprint": 38,
    "fact_payroll": 7344, "fact_attendance_monthly": 7343, "fact_leave": 3441,
    "fact_headcount_monthly": 891, "fact_ledger": 6784, "fact_invoice": 743,
    "fact_invoice_payment": 709, "fact_expense": 501, "fact_task": 28868,
    "fact_anomaly": 405, "fact_attrition_risk": 430, "fact_forecast": 72,
}

def n(sql):
    return con.sql(sql).fetchone()[0]

bad = 0
tot = dict(raw=0, quar=0, passed=0, wh=0)
print(f"{'table':26}{'README':>8}{'raw':>8}{'quar':>6}{'passed':>8}{'clean':>8}{'wh':>8}  result")
for t, readme in README.items():
    s = con.sql(f"SELECT rows_in, rows_passed, rows_quarantined FROM etl.summary WHERE table_name = '{t}'").fetchone()
    if s is None:
        print(f"{t:26} not in etl.summary"); bad += 1; continue
    rin, passed, quar = s
    raw, clean, wh = n(f"SELECT COUNT(*) FROM raw.{t}"), n(f"SELECT COUNT(*) FROM clean.{t}"), n(f"SELECT COUNT(*) FROM wh.{t}")
    ok = (readme == raw == rin) and (rin == passed + quar) and (clean == passed) and (wh == passed)
    bad += (not ok)
    print(f"{t:26}{readme:>8}{raw:>8}{quar:>6}{passed:>8}{clean:>8}{wh:>8}  {'OK' if ok else 'MISMATCH'}")
    tot["raw"] += raw; tot["quar"] += quar; tot["passed"] += passed; tot["wh"] += wh

print(f"\nTOTAL raw={tot['raw']}  quarantined={tot['quar']}  passed={tot['passed']}  warehouse={tot['wh']}")
print("RECONCILED: nothing lost." if bad == 0 else f"{bad} table(s) do not reconcile.")
sys.exit(1 if bad else 0)