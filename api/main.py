from datetime import datetime
from pathlib import Path
import duckdb
from fastapi import FastAPI, HTTPException

DB_PATH = Path(__file__).resolve().parent.parent / "phase-3" / "05_Starter" / "pulseiq_metrics.duckdb"
DB = str(DB_PATH)
ALLOWED = {"M16", "M20", "M05", "M13", "M22"}

app = FastAPI(title="PulseIQ Metrics API")


def last_refresh():
    return datetime.fromtimestamp(DB_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


@app.get("/metrics")
def list_metrics():
    con = duckdb.connect(DB, read_only=True)
    try:
        rows = con.execute(
            "SELECT metric_id, metric_name, unit FROM metrics.metric_catalog "
            "WHERE metric_id IN ('M05','M13','M16','M20','M22') ORDER BY metric_id"
        ).fetchall()
    finally:
        con.close()
    return [{"metric_id": r[0], "name": r[1], "unit": r[2]} for r in rows]


@app.get("/freshness")
def freshness():
    con = duckdb.connect(DB, read_only=True)
    try:
        month = con.execute("SELECT MAX(month_start_date) FROM metrics.v_scorecard").fetchone()[0]
    finally:
        con.close()
    refresh = last_refresh()
    return {
        "data_through": str(month)[:7],
        "last_refresh": refresh,
        "statement": "Data runs to " + str(month)[:7] + ". The metrics database was last refreshed on " + refresh + ".",
    }


@app.get("/metrics/{metric_id}")
def get_metric(metric_id: str):
    metric_id = metric_id.upper()
    if metric_id not in ALLOWED:
        raise HTTPException(status_code=404, detail="Metric not exposed. Try one of: " + ", ".join(sorted(ALLOWED)))

    con = duckdb.connect(DB, read_only=True)
    try:
        cat = con.execute(
            "SELECT metric_name, business_definition, formula, source_table, unit "
            "FROM metrics.metric_catalog WHERE metric_id = ?", [metric_id]
        ).fetchone()
        latest = con.execute(
            "SELECT month_start_date, value, target, status FROM metrics.v_scorecard "
            "WHERE metric_id = ? ORDER BY month_start_date DESC LIMIT 1", [metric_id]
        ).fetchone()
    finally:
        con.close()

    refresh = last_refresh()
    return {
        "metric_id": metric_id,
        "name": cat[0],
        "value": latest[1],
        "unit": cat[4],
        "month": str(latest[0]),
        "target": latest[2],
        "status": latest[3],
        "definition": cat[1],
        "formula": cat[2],
        "source_table": cat[3],
        "last_refresh": refresh,
        "freshness": "Data runs to " + str(latest[0])[:7] + ". The metrics database was last refreshed on " + refresh + ".",
    }
