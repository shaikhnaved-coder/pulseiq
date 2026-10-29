import duckdb
con = duckdb.connect("05_Starter/pulseiq.duckdb")

# ---- 1. Excluded rows: found by rule, from the RAW table ----
con.execute("""CREATE OR REPLACE TABLE metrics.payroll_exclusions (
    payroll_item_id VARCHAR, run_id VARCHAR, month_start_date DATE, department_id VARCHAR,
    gross_pay DOUBLE, net_pay DOUBLE, employer_cost DOUBLE, rule VARCHAR, reason VARCHAR)""")

# Rule 1: second row for the same employee in the same payroll run
con.execute("""INSERT INTO metrics.payroll_exclusions
    SELECT payroll_item_id, run_id, CAST(date_trunc('month', period_end_date) AS DATE), department_id,
           gross_pay, net_pay, employer_cost, 'duplicate_employee_month',
           'Same employee paid twice in one payroll run; the repeat row has a new item id and overstates payroll'
    FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY employee_id, run_id ORDER BY payroll_item_id) AS rn
          FROM raw.fact_payroll) WHERE rn > 1""")

# Rule 2: employee does not exist in the employee table
con.execute("""INSERT INTO metrics.payroll_exclusions
    SELECT payroll_item_id, run_id, CAST(date_trunc('month', period_end_date) AS DATE), department_id,
           gross_pay, net_pay, employer_cost, 'orphan_employee',
           'Employee id does not exist in dim_employee, so the payment cannot belong to any real employee'
    FROM raw.fact_payroll
    WHERE employee_id NOT IN (SELECT employee_id FROM wh.dim_employee)
      AND payroll_item_id NOT IN (SELECT payroll_item_id FROM metrics.payroll_exclusions)""")

# ---- 2. Valid rows = raw minus excluded ----
con.execute("""CREATE OR REPLACE VIEW metrics.v_payroll_valid AS
    SELECT * FROM raw.fact_payroll
    WHERE payroll_item_id NOT IN (SELECT payroll_item_id FROM metrics.payroll_exclusions)""")

# ---- 3. By month and department; groups under 5 people hidden ----
con.execute("""CREATE OR REPLACE VIEW metrics.m30_payroll_month_dept AS
    SELECT CAST(date_trunc('month', p.period_end_date) AS DATE) AS month_start_date,
           p.department_id, COALESCE(d.department_name, p.department_id) AS department,
           ROUND(SUM(p.gross_pay), 2) AS gross_pay, ROUND(SUM(p.net_pay), 2) AS net_pay,
           ROUND(SUM(p.employer_cost), 2) AS employer_cost,
           COUNT(DISTINCT p.employee_id) AS group_size,
           ROUND(SUM(p.employer_cost) / COUNT(DISTINCT p.employee_id), 2) AS cost_per_employee
    FROM metrics.v_payroll_valid p LEFT JOIN wh.dim_department d ON d.department_id = p.department_id
    GROUP BY 1, 2, 3 HAVING COUNT(DISTINCT p.employee_id) >= 5""")

# ---- 4. Company total by month (all departments) ----
con.execute("""CREATE OR REPLACE VIEW metrics.m31_payroll_month_total AS
    SELECT CAST(date_trunc('month', period_end_date) AS DATE) AS month_start_date,
           ROUND(SUM(gross_pay), 2) AS gross_pay, ROUND(SUM(net_pay), 2) AS net_pay,
           ROUND(SUM(employer_cost), 2) AS employer_cost, COUNT(DISTINCT employee_id) AS group_size,
           ROUND(SUM(employer_cost) / COUNT(DISTINCT employee_id), 2) AS cost_per_employee
    FROM metrics.v_payroll_valid GROUP BY 1""")

print("excluded rows:", con.execute("SELECT COUNT(*) FROM metrics.payroll_exclusions").fetchall()[0][0])
print(con.execute("SELECT payroll_item_id, run_id, department_id, rule FROM metrics.payroll_exclusions ORDER BY 1").df().to_string(index=False))
print("reconciled totals (gross, net, employer cost):",
      con.execute("SELECT ROUND(SUM(gross_pay),2), ROUND(SUM(net_pay),2), ROUND(SUM(employer_cost),2) FROM metrics.v_payroll_valid").fetchall()[0])
print("warehouse totals  (gross, net, employer cost):",
      con.execute("SELECT ROUND(SUM(gross_pay),2), ROUND(SUM(net_pay),2), ROUND(SUM(employer_cost),2) FROM wh.fact_payroll").fetchall()[0])