import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb")

con.execute("""
CREATE OR REPLACE VIEW metrics.v_overspend_rank AS
SELECT department_id,
       department_name,
       SUM(budget)   AS total_budget,
       SUM(actual)   AS total_actual,
       SUM(variance) AS total_variance,
       ROUND(SUM(variance) * 100.0 / SUM(budget), 2) AS variance_pct,
       COUNT(*) FILTER (WHERE variance > 0)       AS months_over_budget,
       COUNT(*) FILTER (WHERE status = 'Red')     AS red_months,
       COUNT(*) FILTER (WHERE status = 'Amber')   AS amber_months,
       RANK() OVER (ORDER BY SUM(variance) DESC)  AS rank_by_amount,
       RANK() OVER (ORDER BY SUM(variance) * 1.0 / SUM(budget) DESC) AS rank_by_pct
FROM metrics.v_payroll_budget_variance
WHERE actual IS NOT NULL
GROUP BY department_id, department_name
""")

print(con.execute("""
    SELECT rank_by_amount, department_id, department_name,
           total_budget, ROUND(total_actual) AS total_actual,
           ROUND(total_variance) AS total_variance, variance_pct,
           months_over_budget, red_months, amber_months, rank_by_pct
    FROM metrics.v_overspend_rank
    ORDER BY rank_by_amount
""").df().to_string())