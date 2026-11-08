import pathlib, duckdb, pandas as pd

REF_PATH = r"C:\Users\shaikh naved\OneDrive\Desktop\ipl\unlock_PQ-13_reference_summary_dept_month.csv"
ref_file = pathlib.Path(REF_PATH)
if not ref_file.exists():
    raise SystemExit("Reference file not found. Check REF_PATH at the top of this script.")
ref = pd.read_csv(ref_file) if ref_file.suffix.lower() == ".csv" else pd.read_excel(ref_file)
print("Reference file:", ref_file, "|", len(ref), "rows")

# (my column, reference column, tolerance). Several of mine are tested against the SAME reference column,
# so the ones that match show which definition the reference uses.
MAP = [
    ("headcount",                    "headcount_end",              0.5),
    ("headcount_m01",                "headcount_end",              0.5),
    ("payroll_cost",                 "employer_cost",              0.5),
    ("payroll_cost_incl_excluded",   "employer_cost",              0.5),
    ("gross_pay",                    "gross_pay",                  0.5),
    ("overtime_cost",                "overtime_pay",               0.5),
    ("overtime_cost_incl_excluded",  "overtime_pay",               0.5),
    ("overtime_pct_of_cost",         "overtime_share_pct",         0.01),
    ("overtime_hours",               "overtime_hours",             0.05),
    ("attendance_rate",              "attendance_rate",            0.0002),
    ("attendance_rate_present_only", "attendance_rate",            0.0002),
    ("exits",                        "exits",                      0.5),
    ("attrition_pct",                "attrition_rate_monthly_pct", 0.02),
]

ref["month"] = pd.to_datetime(ref["month"].astype(str)).dt.strftime("%Y-%m")
dups = int(ref.duplicated(["department_id", "month"]).sum())
if dups: print(f"WARNING: reference has {dups} duplicate department-month rows")

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
mine = con.execute("SELECT * FROM metrics.v_dept_month_impact").fetchdf()
# the reference stores attendance as a ratio (0.95); my view stores a percentage (95.0)
mine["attendance_rate"] = mine["attendance_rate_pct"] / 100.0                              # half days count as half a day
mine["attendance_rate_present_only"] = mine["attendance_rate_present_only_pct"] / 100.0    # first (wrong) formula, kept as a test column
# no exits in a month means 0% attrition (the metric view leaves it blank)
mine.loc[(mine["exits"] == 0) & mine["attrition_pct"].isna(), "attrition_pct"] = 0.0

refm = ref[["department_id", "month"]].copy()
for _, rc, _ in MAP:
    refm[rc] = ref[rc].values
refm = refm.drop_duplicates(["department_id", "month"])
refm = refm.loc[:, ~refm.columns.duplicated()]
refm = refm.rename(columns={rc: f"{rc}__ref" for rc in {r for _, r, _ in MAP}})

m = mine.merge(refm, on=["department_id", "month"], how="outer", indicator=True)
only_mine = int((m["_merge"] == "left_only").sum())
only_ref = int((m["_merge"] == "right_only").sum())
both = m[m["_merge"] == "both"]

out = both[["department_id", "month"]].copy()
summary, bad_flags = [], []
for mc, rc, tol in MAP:
    a, b = both[mc].astype(float), both[f"{rc}__ref"].astype(float)
    diff = (a - b).round(4)
    missing = a.isna() != b.isna()              # one side blank, the other has a value
    bad = (diff.abs() > tol) | missing
    out[f"{mc}_mine"], out[f"{mc}_ref"], out[f"{mc}_diff"] = a, b, diff
    bad_flags.append(bad)
    summary.append({"my_column": mc, "reference_column": rc, "rows_compared": len(both),
                    "rows_matching": int((~bad).sum()), "rows_different": int(bad.sum()),
                    "max_abs_diff": float(diff.abs().max()), "total_diff": float(diff.sum())})
summary.append({"my_column": "department-months only in mine", "rows_different": only_mine})
summary.append({"my_column": "department-months only in reference", "rows_different": only_ref})

summ = pd.DataFrame(summary)
out.to_csv("docs/pq13_comparison.csv", index=False)
summ.to_csv("docs/pq13_comparison_summary.csv", index=False)
bad_any = pd.concat(bad_flags, axis=1).any(axis=1)
out[bad_any].to_csv("docs/pq13_differences.csv", index=False)

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print("\n=== COMPARISON SUMMARY ===")
print(summ.to_string(index=False))
print(f"\nReference total employer_cost:        {ref['employer_cost'].sum():>18,.2f}")
print(f"Mine, clean (payroll_cost):             {mine['payroll_cost'].sum():>18,.2f}")
print(f"Mine, incl. the 4 bad rows:             {mine['payroll_cost_incl_excluded'].sum():>18,.2f}")
print("\n=== Department-months where payroll_cost differs from the reference ===")
pc = out[(out["payroll_cost_diff"].abs() > 0.5)]
print(pc[["department_id", "month", "payroll_cost_mine", "payroll_cost_ref", "payroll_cost_diff"]].to_string(index=False) if len(pc) else "none")
print("\n=== Department-months where payroll_cost_incl_excluded differs from the reference ===")
pi = out[(out["payroll_cost_incl_excluded_diff"].abs() > 0.5)]
print(pi[["department_id", "month", "payroll_cost_incl_excluded_mine", "payroll_cost_incl_excluded_ref", "payroll_cost_incl_excluded_diff"]].to_string(index=False) if len(pi) else "none")