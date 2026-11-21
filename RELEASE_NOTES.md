# PulseIQ v1.0.0 Release Notes

Author: Shaikh Naved (Data Analysts track, Aura Workforce)
Repository: https://github.com/shaikhnaved-coder/pulseiq
Data runs to: September 2026

## What is included

**Data pipeline and warehouse (phase-1)**
- ETL pipeline that checks every row against data contracts. Rows that fail go to a quarantine table with the reason.
- Result of the last full run: 62,770 rows in, 62,737 passed, 33 quarantined. A repeat run gave the same fingerprint (5249d226e200).
- DuckDB star-schema warehouse with 23 tables.
- Data-quality gate with 14 checks.
- 28 governed metric views and a metric dictionary.

**Dashboard (live)**
- Link: https://pulseiq-dashboard-naved.streamlit.app/
- Pages: workforce and headcount, attendance and leave, attrition, team productivity, payroll cost, budget vs actual, P&L and expenses, receivables and cash, cross-department impact, AI signals, executive scorecard (8 KPIs plus an overdue receivables card for Sep 2026), KPI explorer.
- KPI explorer: choose a metric and a dimension, drill down from company to department to team. Groups smaller than 5 people are hidden. What a user sees depends on the demo role (ADMIN, HR, MANAGER, EXECUTIVE).

**Metrics API (live)**
- Link: https://pulseiq-api-f9vv.onrender.com
- Five metrics: M05 attrition, M13 attendance, M16 revenue, M20 days sales outstanding, M22 task completion. Each answer has the value, definition, formula, source table and last refresh.
- Endpoints: /metrics, /metrics/{metric_id}, /freshness.
- Documents: docs/API.md and docs/lineage.md (lineage diagram for each metric).

**Reports**
- Monthly report builder: `python src/build_report.py --month YYYY-MM` (Excel file with five sections, date range and data cut-off on the cover).
- Scheduled with GitHub Actions on the 2nd of every month at 08:30 IST.
- Board pack (10 slides), consolidated report, and the Phase 1 to 4 reports.

- Final Challenge: the overdue receivables card on the scorecard (see FINAL_CHALLENGE.md).

## What is not included

- Real sign-in. Roles come from a demo users file, not real accounts.
- Automatic data refresh. When there is new data, the pipeline is run by hand and the app is redeployed. Only the monthly report is scheduled.
- Forecasts checked against real future data. They are checked only against my own backtest (headcount error 1.97%, attrition error 0.54 percentage points).
- Live company data. The data is the programme dataset.

## Known limits

- **Data-quality gate is BLOCKED.** The latest run (484e1ec1) had 7 checks passed and 7 failed, 3 of them critical. The failures are documented as known limitations. They were not corrected. Production use needs a formal decision on each one and an owner for fixing it.
- Groups under 5 people are hidden, so some small teams cannot be analysed. Someone who runs many different queries could still compare results. A next step is rounding counts to the nearest 5.
- The free hosting plans sleep when unused. The first request to the API can take about a minute, and the dashboard can take a few seconds to wake up.
- `last_refresh` in the API is the time the metrics database file was last changed. On the live service it is the deploy time.