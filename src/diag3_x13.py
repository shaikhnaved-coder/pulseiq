import duckdb, pandas as pd
pd.options.display.width = 220
pd.options.display.max_colwidth = 120
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
p = lambda t, s: (print("\n--", t), print(con.execute(s).fetchdf().to_string(index=False)))
print(con.execute("SELECT sql FROM duckdb_views() WHERE view_name='v_payroll_valid'").fetchone()[0][:1500])
p("the 4 excluded payroll rows", "SELECT payroll_item_id, month_start_date, department_id, employer_cost, rule, reason FROM metrics.payroll_exclusions")
p("are those rows still inside v_payroll_valid?", """SELECT count(*) AS flagged_rows_still_in_valid
   FROM metrics.v_payroll_valid WHERE payroll_item_id IN (SELECT payroll_item_id FROM metrics.payroll_exclusions)""")