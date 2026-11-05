import duckdb
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
one = lambda s: con.execute(s).fetchone()[0]
lo, hi = con.execute("SELECT min(month), max(month) FROM metrics.x13_payroll").fetchone()
print(f"window: {lo} to {hi}")

rows = one("SELECT count(*) FROM metrics.v_dept_month_impact")
dups = one("SELECT count(*) FROM (SELECT department_id, month FROM metrics.v_dept_month_impact GROUP BY 1,2 HAVING count(*) > 1)")
print("rows:", rows, "(expect 198) | duplicate department-month rows:", dups, "(must be 0)")

W = lambda col: f"strftime({col}, '%Y-%m') BETWEEN '{lo}' AND '{hi}'"
checks = [  # column in the combined view, expected total from the ORIGINAL source for the same months
    ("payroll_cost",  f"SELECT sum(employer_cost) FROM metrics.v_payroll_valid WHERE {W('period_end_date')}"),
    ("overtime_cost", f"SELECT sum(overtime_pay)   FROM metrics.v_payroll_valid WHERE {W('period_end_date')}"),
    ("present_days",  f"SELECT sum(present_days)   FROM wh.fact_attendance_monthly WHERE {W('period_end_date')}"),
    ("leave_days",    f"SELECT sum(leave_days)     FROM wh.v_leave_monthly WHERE {W('month')}"),
    ("exits",         f"SELECT sum(exits)          FROM metrics.m03_exits WHERE {W('month_start_date')}"),
    ("headcount",     f"SELECT sum(headcount_end)  FROM wh.fact_headcount_monthly WHERE {W('month_start_date')}"),
    ("headcount_m01", f"SELECT sum(headcount)      FROM metrics.m01_headcount WHERE {W('month_start_date')}"),
]
for col, src in checks:
    a = one(f"SELECT COALESCE(sum({col}),0) FROM metrics.v_dept_month_impact")
    b = one(src)
    print(f"{col:14} combined={a:>18,.2f}  source={b:>18,.2f}  ", "OK" if abs(a - b) < 0.01 else "MISMATCH")

flag = one("SELECT sum(payroll_cost_incl_excluded) - sum(payroll_cost) FROM metrics.v_dept_month_impact")
print(f"payroll in raw but removed as bad rows: {flag:,.2f} (expect 410,967.46)")
print(con.execute("SELECT * FROM metrics.v_dept_month_impact LIMIT 5").fetchdf().to_string(index=False))