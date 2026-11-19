# PulseIQ Metrics API

A small read-only API. It returns the latest value of 5 metrics, with the definition, source table and last refresh.

## Run it locally

```
uvicorn api.main:app --reload
```

Then open http://127.0.0.1:8000/docs for the automatic interactive page.

## Endpoints

| Endpoint | What it returns |
|---|---|
| GET /metrics | List of the 5 exposed metrics |
| GET /metrics/{metric_id} | Latest value, definition, formula, source, last refresh |
| GET /freshness | The data freshness statement |

Exposed metrics: M16 Revenue, M20 Days sales outstanding, M05 Attrition (rolling 12 months), M13 Attendance rate, M22 Task completion rate.

## Example: GET /metrics/M16

```json
{
  "metric_id": "M16",
  "name": "Revenue",
  "value": 80268200.0,
  "unit": "INR",
  "month": "2026-09-01",
  "target": 70000000.0,
  "status": "Green",
  "definition": "Income booked in the ledger (accounts 4001-4004).",
  "formula": "-SUM(signed_amount) for accounts 4001-4004",
  "source_table": "fact_ledger",
  "last_refresh": "2026-10-25 12:39:28",
  "freshness": "Data runs to 2026-09. The ETL last ran on 2026-10-25 12:39:28."
}
```

## Example: GET /freshness

```json
{
  "data_through": "2026-09",
  "last_etl_run": "2026-10-25 12:39:28",
  "statement": "Data runs to 2026-09. The ETL last ran on 2026-10-25 12:39:28."
}
```

## Errors

An unknown metric id returns 404 with a message listing the valid ids.

## Lineage

See lineage.md for the path of each number from raw table to dashboard.
