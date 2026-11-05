import duckdb
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
p = lambda t, s: (print("\n--", t), print(con.execute(s).fetchdf().to_string(index=False)))

for v in ["v_leave_monthly", "v_attendance_monthly"]:
    print("\n-- definition of", v)
    print(con.execute(f"SELECT sql FROM duckdb_views() WHERE view_name='{v}'").fetchone()[0])

p("leave statuses", "SELECT status, count(*) AS requests, sum(\"days\") AS total_days FROM wh.fact_leave GROUP BY 1 ORDER BY 1")
p("payroll period_end_date: most common day of month",
  "SELECT strftime(period_end_date,'%d') AS day, count(*) n FROM wh.fact_payroll GROUP BY 1 ORDER BY 2 DESC LIMIT 3")
p("m01 headcount vs warehouse start/end headcount",
  """SELECT sum(m.headcount) m01_headcount, sum(f.headcount_start) wh_start, sum(f.headcount_end) wh_end
     FROM metrics.m01_headcount m JOIN wh.fact_headcount_monthly f USING (month_start_date, department_id)""")
p("m01 rows vs warehouse rows",
  "SELECT (SELECT count(*) FROM metrics.m01_headcount) m01_rows, (SELECT count(*) FROM wh.fact_headcount_monthly) wh_rows")
p("m01 group_size range (small groups may be hidden)", "SELECT min(group_size) mn, max(group_size) mx FROM metrics.m01_headcount")
p("exits: m03 vs warehouse", """SELECT (SELECT sum(exits) FROM metrics.m03_exits) m03_exits,
                                       (SELECT sum(exits) FROM wh.fact_headcount_monthly) wh_exits""")
p("payroll: valid vs all vs exclusions", """SELECT (SELECT sum(employer_cost) FROM metrics.v_payroll_valid) valid_cost,
   (SELECT sum(employer_cost) FROM wh.fact_payroll) all_cost,
   (SELECT sum(employer_cost) FROM metrics.payroll_exclusions) excluded_cost""")