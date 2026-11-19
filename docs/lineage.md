# Metric lineage

Each number travels: raw table, ETL, warehouse table, metric view, scorecard view, dashboard.

## M16 Revenue
```mermaid
flowchart LR
  A[raw.fact_ledger] --> B[ETL: clean and validate] --> C[wh.fact_ledger] --> D[metrics.m16_revenue] --> E[metrics.v_scorecard] --> F[Streamlit dashboard]
```

## M20 Days sales outstanding
```mermaid
flowchart LR
  A1[raw.fact_invoice] --> B[ETL: clean and validate]
  A2[raw.fact_ledger] --> B
  B --> C[wh.fact_invoice and wh.fact_ledger] --> D[metrics.m20_dso] --> E[metrics.v_scorecard] --> F[Streamlit dashboard]
```

## M05 Attrition, rolling 12 months
```mermaid
flowchart LR
  A[raw.fact_headcount_monthly] --> B[ETL: clean and validate] --> C[wh.fact_headcount_monthly]
  C --> D1[metrics.m01_headcount] --> D[metrics.m05_attrition_rolling12]
  C --> D2[metrics.m03_exits] --> D
  D --> E[metrics.v_scorecard] --> F[Streamlit dashboard]
```

## M13 Attendance rate
```mermaid
flowchart LR
  A[raw.fact_attendance_monthly] --> B[ETL: clean and validate] --> C[wh.fact_attendance_monthly] --> D[metrics.m13_attendance_rate] --> E[metrics.v_scorecard] --> F[Streamlit dashboard]
```

## M22 Task completion rate
```mermaid
flowchart LR
  A[raw.fact_task] --> B[ETL: clean and validate] --> C[wh.fact_task] --> D[metrics.m22_task_completion_rate] --> E[metrics.v_scorecard] --> F[Streamlit dashboard]
```
