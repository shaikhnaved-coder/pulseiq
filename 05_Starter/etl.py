

"""
etl.py - PulseIQ PQ-01: validate every raw table against its data contract.
 
Run (from the 05_Starter folder, with the venv active):
    python load_to_duckdb.py     # only needed once, builds schema 'raw'
    python etl.py                # validates everything, prints the count summary
 
What it builds inside pulseiq.duckdb
    clean.<table>      rows that passed every check
    etl.quarantine     rows that failed, one line per bad row, with the reason(s)
    etl.summary        per table: rows_in, rows_passed, rows_quarantined
 
Rule: rows_in = rows_passed + rows_quarantined for every table, so no row can
disappear silently. Re-running rebuilds all three outputs from raw, so it is safe
to run as many times as you like.
"""
import hashlib
import json
import re
import sys
from datetime import datetime
 
import duckdb
import pandas as pd
 
DB_FILE = "pulseiq.duckdb"
 
# Tables that have NO contract of their own are checked against data_dictionary
# (type + "can it be empty?"). These are the facts we also add a primary key to.
PRIMARY_KEYS = {
    "fact_payroll": ["payroll_item_id"],
    "fact_attendance_monthly": ["attendance_fact_id"],
    "fact_leave": ["leave_request_id"],
    "fact_headcount_monthly": ["date_key", "department_id"],
    "fact_ledger": ["line_id"],
    "fact_invoice": ["invoice_id"],
    "fact_invoice_payment": ["payment_id"],
    "fact_expense": ["expense_id"],
}
 
# Any column with this name must point to a real row in this dimension.
FOREIGN_KEYS = {
    "employee_id": ("dim_employee", "employee_id"),
    "department_id": ("dim_department", "department_id"),
}
 
 
# ----------------------------------------------------------------------------
# 1. THE CONTRACTS (copied from data_contracts.csv, same as your contracts.md)
# ----------------------------------------------------------------------------
def col(type_, nullable=False, **rules):
    """One column's promise: type, can it be empty, plus optional rules."""
    return {"type": type_, "nullable": nullable, **rules}
 
 
CONTRACTS = {
    "fact_task": {
        "key": ["task_id"],
        "columns": {
            "task_id": col("string", pattern=r"TASK-\d{5}", unique=True),
            "team_id": col("string", fk=("dim_team", "team_id")),
            "sprint_id": col("string", fk=("dim_sprint", "sprint_id")),
            "assignee_employee_id": col("string", fk=("dim_employee", "employee_id")),
            "task_type": col("string", allowed=["Feature", "Bug", "Chore", "Spike"]),
            "priority": col("string", allowed=["P1", "P2", "P3", "P4"]),
            "story_points": col("int", allowed=["1", "2", "3", "5", "8", "13"]),
            "created_date": col("date"),
            "started_date": col("date", nullable=True),
            "due_date": col("date"),
            "completed_date": col("date", nullable=True),
            "status": col("string", allowed=["Done", "In Progress", "Blocked", "To Do", "Cancelled"]),
            "reopened_count": col("int", min=0),
        },
    },
    "fact_attrition_risk": {
        "key": ["prediction_id"],
        "columns": {
            "prediction_id": col("string", pattern=r"AR-\d{4}", unique=True),
            "employee_id": col("string"),  # must be an ACTIVE employee (custom rule below)
            "department_id": col("string", fk=("dim_department", "department_id")),
            "as_of_date": col("date"),
            "risk_score_12m": col("decimal", pattern=r"\d(\.\d{1,3})?", min=0, max=1),
            "risk_band": col("string", allowed=["Low", "Medium", "High"]),
            "top_reason_1": col("string", nullable=True),
            "top_reason_2": col("string", nullable=True),
            "top_reason_3": col("string", nullable=True),
            "model_version": col("string"),
        },
    },
    "fact_forecast": {
        "key": ["forecast_id"],
        "columns": {
            "forecast_id": col("string", pattern=r"FC-\d{4}", unique=True),
            "metric": col("string", allowed=["headcount_end", "attrition_rate_monthly_pct"]),
            "department_id": col("string"),  # department id or ALL (custom rule below)
            "forecast_month": col("date", pattern=r"\d{4}-\d{2}-01"),
            "forecast_value": col("decimal", min=0),
            "lower_80": col("decimal"),
            "upper_80": col("decimal"),
            "method": col("string"),
            "trained_through": col("string", pattern=r"\d{4}-(0[1-9]|1[0-2])"),
        },
    },
    "fact_anomaly": {
        "key": ["result_id"],
        "columns": {
            "result_id": col("string", pattern=r"AN-\d{4}", unique=True),
            "source_dataset": col("string", allowed=["attendance_monthly_features", "payroll_monthly_features"]),
            "record_id": col("string"),
            "employee_id": col("string", fk=("dim_employee", "employee_id")),
            "period": col("date"),
            "anomaly_score": col("decimal", pattern=r"\d(\.\d{1,3})?", min=0, max=1),
            "flagged": col("string", allowed=["Y", "N"]),
            "reason_code": col("string"),
            "reason_text": col("string"),
            "money_at_risk": col("decimal", nullable=True),
            "model_version": col("string"),
            "scored_at": col("timestamp"),
        },
    },
}
 
 
# ----------------------------------------------------------------------------
# 2. SMALL HELPERS
# ----------------------------------------------------------------------------
def as_text(df, c):
    """Column as text. Missing values stay missing (NA)."""
    return df[c].astype("string")
 
 
def is_blank(s):
    """True where the value is missing or only spaces."""
    return (s.isna() | s.str.strip().eq("")).fillna(True).astype(bool)
 
 
def as_bool(mask):
    return mask.fillna(False).astype(bool)
 
 
def to_date(s):
    return pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
 
 
def valid_type(s, type_):
    """True where the text can be read as the promised type (blank counts as valid
    here, because 'can it be empty?' is a separate check)."""
    blank = is_blank(s)
    if type_ == "string":
        ok = pd.Series(True, index=s.index)
    elif type_ == "int":
        ok = s.str.fullmatch(r"-?\d+(\.0+)?").fillna(False).astype(bool)
    elif type_ == "decimal":
        ok = pd.to_numeric(s, errors="coerce").notna()
    elif type_ == "date":
        ok = to_date(s).notna()
    elif type_ == "timestamp":
        ok = pd.to_datetime(s, format="ISO8601", errors="coerce").notna()
    else:
        raise ValueError(f"unknown type {type_}")
    return ok | blank
 
 
# ----------------------------------------------------------------------------
# 3. THE CHECKER: one table in, a list of (mask, reason) out
# ----------------------------------------------------------------------------
def checks_for_column(df, name, spec, lookup, checks):
    s = as_text(df, name)
    blank = is_blank(s)
 
    if not spec["nullable"]:
        checks.append((blank, f"{name}: empty but contract says it cannot be empty"))
 
    checks.append((~valid_type(s, spec["type"]), f"{name}: not a valid {spec['type']}"))
 
    if "pattern" in spec:
        bad = ~blank & ~s.str.fullmatch(spec["pattern"]).fillna(False).astype(bool)
        checks.append((bad, f"{name}: wrong format (expected {spec['pattern']})"))
 
    if "allowed" in spec:
        bad = ~blank & ~s.isin(spec["allowed"])
        checks.append((bad, f"{name}: value not in allowed list {spec['allowed']}"))
 
    if "min" in spec or "max" in spec:
        n = pd.to_numeric(s, errors="coerce")
        if "min" in spec:
            checks.append((as_bool(n < spec["min"]), f"{name}: below minimum {spec['min']}"))
        if "max" in spec:
            checks.append((as_bool(n > spec["max"]), f"{name}: above maximum {spec['max']}"))
 
    if spec.get("unique"):
        checks.append((s.duplicated(keep="first") & ~blank, f"{name}: duplicate value (must be unique)"))
 
    if "fk" in spec:
        parent_table, parent_col = spec["fk"]
        known = lookup(parent_table, parent_col)
        checks.append((~blank & ~s.isin(known), f"{name}: not found in {parent_table}.{parent_col}"))
 
 
def custom_rules(table, df, lookup, checks):
    """Rules that compare columns with each other (or with another table)."""
    if table == "fact_task":
        status = as_text(df, "status")
        created, started = to_date(as_text(df, "created_date")), to_date(as_text(df, "started_date"))
        completed, due = to_date(as_text(df, "completed_date")), to_date(as_text(df, "due_date"))
        checks.append((as_bool(created > started), "created_date is after started_date"))
        checks.append((is_blank(as_text(df, "started_date")) & status.ne("To Do").fillna(False).astype(bool),
                       "started_date is empty but status is not To Do"))
        checks.append((is_blank(as_text(df, "completed_date")) & status.eq("Done").fillna(False).astype(bool),
                       "status is Done but completed_date is empty"))
        checks.append((as_bool(completed < started), "completed_date is before started_date"))
        sprint_end = lookup("dim_sprint", "sprint_id", value_col="end_date", as_map=True)
        expected = as_text(df, "sprint_id").map(sprint_end)
        checks.append((as_bool(to_date(expected) != due) & expected.notna(), "due_date is not the sprint end date"))
 
    elif table == "fact_attrition_risk":
        active = lookup("dim_employee", "employee_id", where="is_current = 'Y' AND employment_status = 'Active'")
        emp = as_text(df, "employee_id")
        checks.append((~is_blank(emp) & ~emp.isin(active), "employee_id: not an active employee in dim_employee"))
        asof = as_text(df, "as_of_date")
        batch_date = asof.mode().iloc[0] if asof.notna().any() else None
        checks.append((asof.notna() & asof.ne(batch_date).fillna(False).astype(bool),
                       f"as_of_date differs from the batch date ({batch_date})"))
 
    elif table == "fact_forecast":
        dept = as_text(df, "department_id")
        known = set(lookup("dim_department", "department_id")) | {"ALL"}
        checks.append((~is_blank(dept) & ~dept.isin(known), "department_id: not a department id or ALL"))
        fv = pd.to_numeric(as_text(df, "forecast_value"), errors="coerce")
        lo = pd.to_numeric(as_text(df, "lower_80"), errors="coerce")
        hi = pd.to_numeric(as_text(df, "upper_80"), errors="coerce")
        checks.append((as_bool(lo > fv), "lower_80 is above forecast_value"))
        checks.append((as_bool(hi < fv), "upper_80 is below forecast_value"))
 
    elif table == "fact_anomaly":
        src = as_text(df, "source_dataset")
        money = as_text(df, "money_at_risk")
        checks.append((src.eq("payroll_monthly_features").fillna(False).astype(bool) & is_blank(money),
                       "money_at_risk is empty for a payroll row"))
        checks.append((src.eq("attendance_monthly_features").fillna(False).astype(bool) & ~is_blank(money),
                       "money_at_risk must be blank for an attendance row"))
 
 
def contract_from_dictionary(table, dictionary):
    """For tables without a data_contracts entry: type + empty-or-not from data_dictionary."""
    rows = dictionary[dictionary["sheet"] == table]
    type_map = {"text": "string", "integer": "int", "decimal": "decimal", "date": "date", "timestamp": "timestamp"}
    columns = {}
    for _, r in rows.iterrows():
        # fact tables: a column with zero empties in the dictionary must never be empty.
        # reference tables (dimensions, targets, governance sheets): types only.
        nullable = int(r["null_count"]) > 0 or not table.startswith("fact_")
        columns[r["column"]] = col(type_map[r["data_type"]], nullable=nullable)
    return {"key": PRIMARY_KEYS.get(table, []), "columns": columns}
 
 
def validate(table, df, contract, lookup):
    """Return (list of checks, number of rows). Each check is (bad-row mask, reason)."""
    checks = []
    missing = [c for c in contract["columns"] if c not in df.columns]
    if missing:
        raise SystemExit(f"{table}: contract columns missing from the data: {missing}")
 
    for name, spec in contract["columns"].items():
        checks_for_column(df, name, spec, lookup, checks)
 
    # tables checked from the dictionary also get a unique primary key + foreign keys
    if table not in CONTRACTS:
        key = contract["key"]
        if key:
            dup = df[key].astype("string").fillna("").agg("|".join, axis=1).duplicated(keep="first")
            checks.append((dup, f"duplicate primary key {key}"))
        for c, (ptab, pcol) in FOREIGN_KEYS.items():
            if c in df.columns and table.startswith("fact_"):
                s = as_text(df, c)
                checks.append((~is_blank(s) & ~s.isin(lookup(ptab, pcol)), f"{c}: not found in {ptab}.{pcol}"))
 
    custom_rules(table, df, lookup, checks)
    return checks
 
 
def collect_failures(df, checks):
    """Turn the list of (mask, reason) into one row per bad source row."""
    if not checks:
        return pd.DataFrame(columns=["_rid", "failed_checks", "reason"])
    masks = pd.DataFrame({reason: as_bool(m).values for m, reason in checks}, index=df.index)
    bad = masks.any(axis=1)
    out = pd.DataFrame({"_rid": df.loc[bad, "_rid"].values})
    sub = masks[bad]
    out["failed_checks"] = sub.sum(axis=1).values
    out["reason"] = ["; ".join(sub.columns[row]) for row in sub.values]
    return out
 
 
# ----------------------------------------------------------------------------
# 4. DATABASE PART
# ----------------------------------------------------------------------------
def make_lookup(con):
    cache = {}
 
    def lookup(table, column, where=None, value_col=None, as_map=False):
        key = (table, column, where, value_col, as_map)
        if key not in cache:
            sql_where = f"WHERE {where}" if where else ""
            if as_map:
                q = f'SELECT CAST("{column}" AS VARCHAR), CAST("{value_col}" AS VARCHAR) FROM raw.{table} {sql_where}'
                cache[key] = dict(con.execute(q).fetchall())
            else:
                q = f'SELECT DISTINCT CAST("{column}" AS VARCHAR) FROM raw.{table} {sql_where}'
                cache[key] = {r[0] for r in con.execute(q).fetchall() if r[0] is not None}
        return cache[key]
 
    return lookup
 
 
def read_raw_as_text(con, table):
    """Every column cast to text, plus DuckDB's rowid as _rid (the row's identity)."""
    cols = [r[0] for r in con.execute(f"DESCRIBE raw.{table}").fetchall()]
    select = ", ".join(f'CAST("{c}" AS VARCHAR) AS "{c}"' for c in cols)
    return con.execute(f"SELECT rowid AS _rid, {select} FROM raw.{table}").df()
 
 
def main():
    started = datetime.now()
    con = duckdb.connect(DB_FILE)
    tables = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw' ORDER BY table_name").fetchall()]
    if not tables:
        raise SystemExit("No tables in schema raw. Run:  python load_to_duckdb.py  first.")
 
    dictionary = con.execute("SELECT * FROM raw.data_dictionary").df()
    for schema in ("clean", "etl"):
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    lookup = make_lookup(con)
 
    quarantine_parts, summary_rows = [], []
    print(f"Validating {len(tables)} tables ...\n")
    for table in tables:
        df = read_raw_as_text(con, table)
        if table in CONTRACTS:
            contract, source = CONTRACTS[table], "data_contracts"
        else:
            contract = contract_from_dictionary(table, dictionary)
            source = "data_dictionary" if table.startswith("fact_") else "data_dictionary (types only)"
 
        checks = validate(table, df, contract, lookup)
        bad = collect_failures(df, checks)
 
        if len(bad):
            data_cols = [c for c in df.columns if c != "_rid"]
            by_rid = df.set_index("_rid")
            keys = contract["key"]
            bad["source_table"] = table
            bad["row_key"] = [
                "|".join(str(by_rid.at[r, k]) for k in keys) if keys else str(r) for r in bad["_rid"]]
            bad["row_data"] = [
                json.dumps({c: (None if pd.isna(by_rid.at[r, c]) else str(by_rid.at[r, c])) for c in data_cols})
                for r in bad["_rid"]]
            quarantine_parts.append(bad)
 
        rows_in, quarantined = len(df), len(bad)
        summary_rows.append({"table_name": table, "checked_against": source, "rows_in": rows_in,
                             "rows_passed": rows_in - quarantined, "rows_quarantined": quarantined})
        print(f"  {table:<28} in={rows_in:>6}  passed={rows_in - quarantined:>6}  quarantined={quarantined:>4}")
 
    run_at = started.strftime("%Y-%m-%d %H:%M:%S")
 
    # ---- write everything in ONE transaction: all or nothing, always rebuilt from raw
    qdf = (pd.concat(quarantine_parts, ignore_index=True) if quarantine_parts else
           pd.DataFrame(columns=["source_table", "_rid", "row_key", "failed_checks", "reason", "row_data"]))
    qdf = qdf.rename(columns={"_rid": "row_id"})
    qdf["run_at"] = run_at
    qdf = qdf[["source_table", "row_id", "row_key", "failed_checks", "reason", "row_data", "run_at"]]
 
    sdf = pd.DataFrame(summary_rows)
    sdf["rows_balanced"] = (sdf["rows_in"] == sdf["rows_passed"] + sdf["rows_quarantined"]).map({True: "YES", False: "NO"})
    sdf["run_at"] = run_at
 
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute("DROP TABLE IF EXISTS etl.quarantine")
        con.execute("""CREATE TABLE etl.quarantine (
            source_table VARCHAR, row_id BIGINT, row_key VARCHAR, failed_checks INTEGER,
            reason VARCHAR, row_data VARCHAR, run_at VARCHAR)""")
        if len(qdf):
            con.register("qdf_view", qdf)
            con.execute("INSERT INTO etl.quarantine SELECT * FROM qdf_view")
            con.unregister("qdf_view")
 
        con.execute("DROP TABLE IF EXISTS etl.summary")
        con.execute("""CREATE TABLE etl.summary (
            table_name VARCHAR, checked_against VARCHAR, rows_in BIGINT, rows_passed BIGINT,
            rows_quarantined BIGINT, rows_balanced VARCHAR, run_at VARCHAR)""")
        con.register("sdf_view", sdf)
        con.execute("""INSERT INTO etl.summary SELECT table_name, checked_against, rows_in, rows_passed,
                       rows_quarantined, rows_balanced, run_at FROM sdf_view""")
        con.unregister("sdf_view")
 
        for table in tables:
            con.execute(f"""CREATE OR REPLACE TABLE clean.{table} AS
                SELECT * FROM raw.{table}
                WHERE rowid NOT IN (SELECT row_id FROM etl.quarantine WHERE source_table = '{table}')""")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
 
    # ---- final proof printed on screen
    total_in, total_pass, total_q = sdf["rows_in"].sum(), sdf["rows_passed"].sum(), sdf["rows_quarantined"].sum()
    q_in_db = con.execute("SELECT COUNT(*) FROM etl.quarantine").fetchone()[0]
    unbalanced = sdf[sdf["rows_balanced"] == "NO"]["table_name"].tolist()
    clean_total = sum(con.execute(f"SELECT COUNT(*) FROM clean.{t}").fetchone()[0] for t in tables)
 
    fingerprint_source = (sdf.drop(columns="run_at").to_csv(index=False)
                          + qdf.drop(columns="run_at").sort_values(["source_table", "row_id"]).to_csv(index=False))
    fingerprint = hashlib.md5(fingerprint_source.encode()).hexdigest()[:12]
 
    print("\n================ SUMMARY (etl.summary) ================")
    print(f"tables checked        : {len(tables)}")
    print(f"rows in               : {total_in}")
    print(f"rows passed (clean.*) : {total_pass}   (counted in the clean tables: {clean_total})")
    print(f"rows quarantined      : {total_q}   (counted in etl.quarantine: {q_in_db})")
    print(f"in = passed + quarantined for every table: {'YES' if not unbalanced else 'NO -> ' + str(unbalanced)}")
    print(f"run fingerprint       : {fingerprint}   (identical on every re-run of unchanged data)")
    print("=======================================================")
 
    if unbalanced or clean_total != total_pass or q_in_db != total_q:
        sys.exit("COUNT MISMATCH: a row went missing. Do not trust this run.")
    con.close()
 
 
if __name__ == "__main__":
    main()
 


