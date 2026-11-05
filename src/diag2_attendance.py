import duckdb, pandas as pd
REF_PATH = r"C:\Users\shaikh naved\OneDrive\Desktop\ipl\unlock_PQ-13_reference_summary_dept_month.csv"
ref = pd.read_csv(REF_PATH)
ref["month"] = pd.to_datetime(ref["month"].astype(str)).dt.strftime("%Y-%m")
ref = ref[["department_id", "month", "attendance_rate"]].rename(columns={"attendance_rate": "ref_rate"})

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

print("=== How is the employee-level attendance_rate in the warehouse built? (share of rows that agree) ===")
print(con.execute("""
SELECT count(*) AS employee_rows,
  sum(CASE WHEN abs(attendance_rate - present_days*1.0/nullif(scheduled_days,0)) < 0.00051 THEN 1 ELSE 0 END) AS equals_present_over_sched,
  sum(CASE WHEN abs(attendance_rate - (present_days + 0.5*half_days_unpaid)/nullif(scheduled_days,0)) < 0.00051 THEN 1 ELSE 0 END) AS equals_half_credit,
  sum(CASE WHEN abs(attendance_rate - (present_days + wfh_days)*1.0/nullif(scheduled_days,0)) < 0.00051 THEN 1 ELSE 0 END) AS equals_with_wfh,
  sum(CASE WHEN scheduled_days = 0 OR scheduled_days IS NULL THEN 1 ELSE 0 END) AS zero_scheduled_rows,
  sum(CASE WHEN attendance_rate IS NULL THEN 1 ELSE 0 END) AS null_rate_rows
FROM wh.fact_attendance_monthly""").fetchdf().to_string(index=False))

df = con.execute("""
SELECT department_id, strftime(period_end_date, '%Y-%m') AS month,
  count(*) AS emp_rows, sum(scheduled_days) AS sched, sum(present_days) AS present, sum(wfh_days) AS wfh,
  sum(half_days_unpaid) AS half, sum(paid_leave_days) AS paid_leave, sum(unpaid_absence_days) AS unpaid,
  sum(present_days)*1.0/nullif(sum(scheduled_days),0)                                      AS c0_current,
  (sum(present_days) + 0.5*sum(half_days_unpaid))/nullif(sum(scheduled_days),0)           AS c1_half_credit,
  sum(attendance_rate*scheduled_days)/nullif(sum(scheduled_days),0)                       AS c2_rate_weighted,
  avg(attendance_rate)                                                                    AS c3_mean_rate,
  avg((present_days + 0.5*half_days_unpaid)*1.0/nullif(scheduled_days,0))                 AS c4_mean_half_credit,
  1 - (sum(unpaid_absence_days) + 0.5*sum(half_days_unpaid))/nullif(sum(scheduled_days),0) AS c5_one_minus_unpaid
FROM wh.fact_attendance_monthly GROUP BY 1, 2""").fetchdf()

m = df.merge(ref, on=["department_id", "month"])
print("\n=== Rows within 0.0002 of the reference, per definition (198 = perfect) ===")
for c in [c for c in m.columns if c.startswith("c") and c[1].isdigit()]:
    d = (m[c] - m["ref_rate"]).abs()
    print(f"{c:22} {(d <= 0.0002).sum():3} of {len(m)} | max diff {d.max():.4f}")

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print("\n=== Sample: D06 (Customer Support), first 6 months ===")
print(m[m.department_id == "D06"].head(6)[["month", "emp_rows", "sched", "present", "half", "paid_leave", "unpaid",
                                          "c0_current", "c1_half_credit", "ref_rate"]].round(4).to_string(index=False))