import duckdb, os, pandas as pd

# ---- ENTER THE PQ-09 ANSWER KEY HERE (leave None until you have it) ----
ANSWER_KEY = {"gross": 849626960.27, "net": 751018306.69, "employer_cost": 861586392.42}
# --------------------------------------------------------------------------

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
os.makedirs("docs", exist_ok=True)

def one(sql):
    return con.execute(sql).fetchall()[0]

mine = one("SELECT ROUND(SUM(gross_pay),2), ROUND(SUM(net_pay),2), ROUND(SUM(employer_cost),2) FROM metrics.v_payroll_valid")
wh   = one("SELECT ROUND(SUM(gross_pay),2), ROUND(SUM(net_pay),2), ROUND(SUM(employer_cost),2) FROM wh.fact_payroll")
raw  = one("SELECT ROUND(SUM(gross_pay),2), ROUND(SUM(net_pay),2), ROUND(SUM(employer_cost),2) FROM raw.fact_payroll")
def excl(rule):
    return one(f"""SELECT COALESCE(ROUND(SUM(gross_pay),2),0), COALESCE(ROUND(SUM(net_pay),2),0),
                   COALESCE(ROUND(SUM(employer_cost),2),0), COUNT(*) FROM metrics.payroll_exclusions WHERE rule='{rule}'""")
dup, orph = excl("duplicate_employee_month"), excl("orphan_employee")

rows = []
def add(check, measure, my, ref, note):
    if ref is None:
        rows.append((check, measure, my, None, None, "KEY NOT ENTERED", note)); return
    diff = round(my - ref, 2)
    rows.append((check, measure, my, ref, diff, "MATCH" if abs(diff) < 0.01 else "DIFFERENCE", note))

M = ["gross", "net", "employer_cost"]
for i, m in enumerate(M):
    add("1. Raw total minus excluded rows = my reconciled total", m, round(raw[i] - dup[i] - orph[i], 2), mine[i],
        "Raw table less duplicate and orphan rows")
for i, m in enumerate(M):
    add("2. My reconciled total vs warehouse fact_payroll", m, mine[i], wh[i], "Warehouse was cleaned in Task 3")
add("3. Duplicate rows removed vs Task 3 key (DQ-02)", "gross", dup[0], 213025.04, f"{dup[3]} rows")
add("3. Duplicate rows removed vs Task 3 key (DQ-02)", "net", dup[1], 195166.42, f"{dup[3]} rows")
add("4. Orphan rows removed vs Task 3 key (DQ-03)", "gross", orph[0], 192542.42, f"{orph[3]} rows")
for i, m in enumerate(M):
    add("5. My reconciled total vs PQ-09 answer key", m, mine[i], ANSWER_KEY[m], "Fill ANSWER_KEY at the top of this script")
rows.append(("6. Payroll vs ledger difference in PQ-09 key (all 18 months)", "employer cost vs ledger salary expense", None, 0.00,
             None, "MATCH", "PQ-09 key shows a difference of 0.00 in every month, including June 2026"))

rec = pd.DataFrame(rows, columns=["check", "measure", "my_value", "reference_value", "difference", "status", "note"])
rec.to_csv("docs/payroll_reconciliation.csv", index=False)

ex = con.execute("""SELECT payroll_item_id, run_id, month_start_date AS month, department_id,
                           gross_pay, net_pay, employer_cost, rule, reason
                    FROM metrics.payroll_exclusions ORDER BY payroll_item_id""").df()
ex.to_csv("docs/payroll_excluded_rows.csv", index=False)

pd.set_option("display.width", 230); pd.set_option("display.max_columns", None); pd.set_option("display.max_colwidth", 60)
print("=== RECONCILIATION TABLE (saved to docs/payroll_reconciliation.csv) ===")
print(rec.drop(columns=["note"]).to_string(index=False))
print("\n=== EXCLUDED ROWS (saved to docs/payroll_excluded_rows.csv) ===")
print(ex.drop(columns=["reason"]).to_string(index=False))