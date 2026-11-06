import duckdb

# Opens the database for writing (Streamlit must be stopped first)
con = duckdb.connect("05_Starter/pulseiq.duckdb")

# 1. Anomalies by type, biggest money first.
#    money_at_risk is blank for attendance rows, so we keep a separate
#    count of rows with and without a rupee value. NULL is never turned into 0.
con.execute("""
CREATE OR REPLACE VIEW metrics.v_ai_anomaly_by_type AS
SELECT
    reason_code,
    source_dataset,
    MIN(reason_text)                          AS example_reason,
    COUNT(*)                                  AS flagged_records,
    COUNT(money_at_risk)                      AS records_with_money,
    COUNT(*) - COUNT(money_at_risk)           AS records_without_money,
    ROUND(SUM(money_at_risk), 2)              AS money_at_risk,
    ROUND(AVG(anomaly_score), 3)              AS avg_score
FROM wh.fact_anomaly
WHERE flagged = 'Y'
GROUP BY reason_code, source_dataset
ORDER BY money_at_risk DESC NULLS LAST, flagged_records DESC
""")

# 2. Company headcount: actual and forecast (80% range) by month.
#    Actual company total = sum over all departments (D00 is only Executive).
con.execute("""
CREATE OR REPLACE VIEW metrics.v_ai_forecast_headcount AS
WITH act AS (
    SELECT month_start_date AS month_start_date,
           SUM(headcount_end) AS actual
    FROM wh.fact_headcount_monthly
    GROUP BY 1
),
fc AS (
    SELECT forecast_month AS month_start_date,
           forecast_value, lower_80, upper_80, method, trained_through
    FROM wh.fact_forecast
    WHERE metric = 'headcount_end' AND department_id = 'ALL'
)
SELECT COALESCE(a.month_start_date, f.month_start_date) AS month_start_date,
       a.actual, f.forecast_value, f.lower_80, f.upper_80,
       f.method, f.trained_through
FROM act a
FULL OUTER JOIN fc f ON a.month_start_date = f.month_start_date
ORDER BY 1
""")

# 3. Company monthly attrition %: actual and forecast.
con.execute("""
CREATE OR REPLACE VIEW metrics.v_ai_forecast_attrition AS
WITH act AS (
    SELECT month_start_date AS month_start_date,
           ROUND(100.0 * SUM(exits) / NULLIF(SUM(headcount_start), 0), 2) AS actual
    FROM wh.fact_headcount_monthly
    GROUP BY 1
),
fc AS (
    SELECT forecast_month AS month_start_date,
           forecast_value, lower_80, upper_80, method, trained_through
    FROM wh.fact_forecast
    WHERE metric = 'attrition_rate_monthly_pct' AND department_id = 'ALL'
)
SELECT COALESCE(a.month_start_date, f.month_start_date) AS month_start_date,
       a.actual, f.forecast_value, f.lower_80, f.upper_80,
       f.method, f.trained_through
FROM act a
FULL OUTER JOIN fc f ON a.month_start_date = f.month_start_date
ORDER BY 1
""")

# 4. Forecast error: only months where BOTH forecast and actual exist.
con.execute("""
CREATE OR REPLACE VIEW metrics.v_ai_forecast_error AS
SELECT month_start_date, 'headcount_end' AS metric,
       forecast_value, actual, lower_80, upper_80,
       ROUND(forecast_value - actual, 2) AS error,
       ROUND(100.0 * ABS(actual - forecast_value) / NULLIF(actual, 0), 2) AS abs_pct_error,
       (actual BETWEEN lower_80 AND upper_80) AS inside_80_range
FROM metrics.v_ai_forecast_headcount
WHERE actual IS NOT NULL AND forecast_value IS NOT NULL
UNION ALL
SELECT month_start_date, 'attrition_rate_monthly_pct',
       forecast_value, actual, lower_80, upper_80,
       ROUND(forecast_value - actual, 2),
       ROUND(100.0 * ABS(actual - forecast_value) / NULLIF(actual, 0), 2),
       (actual BETWEEN lower_80 AND upper_80)
FROM metrics.v_ai_forecast_attrition
WHERE actual IS NOT NULL AND forecast_value IS NOT NULL
""")

def show(title, sql):
    print("\n" + "=" * 60)
    print(title)
    for r in con.execute(sql).fetchall():
        print(r)

show("ANOMALY by type: (reason, source, flagged, with_money, without_money, money, avg_score)",
     """SELECT reason_code, source_dataset, flagged_records, records_with_money,
               records_without_money, money_at_risk, avg_score
        FROM metrics.v_ai_anomaly_by_type""")

show("CHECK anomaly totals: (view flagged, table flagged, view money, table money)",
     """SELECT (SELECT SUM(flagged_records) FROM metrics.v_ai_anomaly_by_type),
               (SELECT COUNT(*) FROM wh.fact_anomaly WHERE flagged = 'Y'),
               (SELECT ROUND(SUM(money_at_risk), 2) FROM metrics.v_ai_anomaly_by_type),
               (SELECT ROUND(SUM(money_at_risk), 2) FROM wh.fact_anomaly WHERE flagged = 'Y')""")

show("HEADCOUNT actual vs forecast, from 2026-04: (month, actual, forecast, lower, upper)",
     """SELECT month_start_date, actual, forecast_value, lower_80, upper_80
        FROM metrics.v_ai_forecast_headcount
        WHERE month_start_date >= DATE '2026-04-01'""")

show("ATTRITION actual vs forecast, from 2026-04: (month, actual, forecast, lower, upper)",
     """SELECT month_start_date, actual, forecast_value, lower_80, upper_80
        FROM metrics.v_ai_forecast_attrition
        WHERE month_start_date >= DATE '2026-04-01'""")

show("CHECK: does ALL equal the sum of departments? (month, ALL, sum D01-D10)",
     """SELECT forecast_month,
               SUM(CASE WHEN department_id = 'ALL' THEN forecast_value END),
               ROUND(SUM(CASE WHEN department_id <> 'ALL' THEN forecast_value END), 1)
        FROM wh.fact_forecast WHERE metric = 'headcount_end'
        GROUP BY 1 ORDER BY 1""")

show("FORECAST ERROR rows (months with both forecast and actual): (count)",
     "SELECT COUNT(*) FROM metrics.v_ai_forecast_error")

print("\nDone. Views created in the metrics schema.")