# PQ-13 difference notes

Compared metrics.v_dept_month_impact (198 department-months) with the reference summary (198 rows). No department-month exists on only one side.

**Result:** headcount, payroll cost, gross pay, overtime pay, overtime % of cost, overtime hours, exits, attrition and attendance rate match the reference on all 198 department-months. Total payroll is identical: 861,586,392.42.

| Metric | Rows different | Size | Cause | Can it be removed? |
|---|---|---|---|---|
| Attendance rate, first version (present days / scheduled days) | 149 of 198 | up to 0.0264 (about -0.0026 per row on average) | My first formula ignored half days. The reference, like the warehouse's own employee-level attendance_rate (all 7,339 rows), counts a half day as half a day present: (present + 0.5 x half days) / scheduled days. Example: D06 2025-07 has 987 present days and 3 half days, so (987 + 1.5) / 1030 = 0.9597, as in the reference. | Yes - removed. attendance_rate_pct now uses half credit and matches all 198 rows; the old formula is kept as attendance_rate_present_only_pct |
| Payroll test column: payroll_cost_incl_excluded | 4 | 410,967.46 | Test column that adds back the 4 rows removed as invalid: D02 2026-02 (154,811.89) and D08 2025-05 (61,813.15), the same employee paid twice in one run; D01 2026-04 (96,015.00) and D09 2025-12 (98,327.42), employee ids that do not exist in dim_employee. The reference matches the clean payroll, so these rows do not belong. They carry no overtime pay. | No - the rows are invalid |
| Headcount test column: headcount_m01 | 18 | 1 per row | metrics.m01_headcount hides the Executive Office (1 person) because its group size is under 5. The warehouse month-end headcount keeps it and matches the reference. | Yes - the view uses the warehouse headcount |
| leave_days, leave_days_per_head | not compared | - | The reference has no leave columns. Leave days (7,342) tie to wh.v_leave_monthly in the check script. The view counts pending leave (66 days) and assigns each request to the month it starts (174 requests span two months). | Not applicable |
| present_days, scheduled_days, paid_leave_days, unpaid_absence_days | not compared | - | Not in the reference. Present days (141,139) tie to the source in the check script. | Not applicable |

**Overall:** every reference metric matches on all 198 department-months. The remaining gaps are in the two test columns and are explained above.