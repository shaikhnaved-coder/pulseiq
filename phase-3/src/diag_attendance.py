import duckdb, pandas as pd
REF_PATH = r"C:\Users\shaikh naved\OneDrive\Desktop\ipl\unlock_PQ-13_reference_summary_dept_month.csv"
ref = pd.read_csv(REF_PATH)
ref["month"] = pd.to_datetime(ref["month"].astype(str)).dt.strftime("%Y-%m")
ref = ref[["department_id", "month", "attendance_rate"]].rename(columns={"attendance_rate": "ref_rate"})

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
lo, hi = con.execute("SELECT min(attendance_rate), max(attendance_rate) FROM wh.fact_attendance_monthly").fetchone()
print(f"employee-level attendance_rate in the warehouse ranges from {lo} to {hi} (1 = ratio, 100 = percent)")
scale = 100.0 if hi > 1.5 else 1.0

df = con.execute("""
SELECT department_id, strftime(period_end_date, '%Y-%m') AS month,
       sum(present_days) * 1.0 / nullif(sum(scheduled_days), 0)                        AS dept_weighted_ratio,
       avg(attendance_rate)                                                            AS mean_of_employee_rate,
       avg(present_days * 1.0 / nullif(scheduled_days, 0))                             AS mean_of_present_over_scheduled,
       (sum(present_days) + sum(wfh_days)) * 1.0 / nullif(sum(scheduled_days), 0)      AS incl_wfh_days
FROM wh.fact_attendance_monthly GROUP BY 1, 2""").fetchdf()
df["mean_of_employee_rate"] = df["mean_of_employee_rate"] / scale

m = df.merge(ref, on=["department_id", "month"])
for c in ["dept_weighted_ratio", "mean_of_employee_rate", "mean_of_present_over_scheduled", "incl_wfh_days"]:
    d = (m[c] - m["ref_rate"]).abs()
    print(f"{c:32} rows within 0.0002 of the reference: {(d <= 0.0002).sum():3} of {len(m)} | max diff {d.max():.4f}")