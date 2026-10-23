import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

# Look at how valid_to is stored
print(con.execute("""
    SELECT COUNT(*) AS total,
           SUM(CASE WHEN valid_to IS NULL THEN 1 ELSE 0 END) AS empty_valid_to,
           MIN(valid_to) AS min_valid_to,
           MAX(valid_to) AS max_valid_to
    FROM wh.dim_employee
""").df().to_string())

checks = {
"DQ-C11 AI feeds are fresh": """
    SELECT prediction_id FROM {s}.fact_attrition_risk
    WHERE as_of_date < (SELECT MAX(as_of_date) FROM {s}.fact_attrition_risk) - 7
""",
"DQ-C12 History does not overlap": """
    SELECT a.employee_key
    FROM {s}.dim_employee a
    JOIN {s}.dim_employee b
      ON a.employee_id = b.employee_id
     AND a.valid_from < b.valid_from
    WHERE COALESCE(a.valid_to, DATE '9999-12-31') >= b.valid_from
""",
}

print()
print(f"{'check':35} {'raw':>8} {'wh':>8}")
for name, sql in checks.items():
    counts = []
    for s in ["raw", "wh"]:
        try:
            n = con.execute(f"SELECT COUNT(*) FROM ({sql.format(s=s)})").fetchone()[0]
        except Exception as e:
            n = "ERR"
            print("  error on", s, ":", str(e)[:150])
        counts.append(n)
    print(f"{name:35} {counts[0]:>8} {counts[1]:>8}")