# Metric -> how to compute it. Only keys listed here can ever reach SQL.
DIMENSIONS = {"department": "department", "team": "team", "city_tier": "city_tier",
              "work_mode": "work_mode", "gender": "gender"}

METRICS = {
    "headcount": dict(
        label="Headcount (active employees)", min_group=5, pay=False,
        join="", agg="COUNT(DISTINCT p.employee_id)",
        params=[], fmt="{:,.0f}"),
    "avg_gross_pay": dict(
        label="Average monthly gross pay (INR)", min_group=5, pay=True,
        join="JOIN wh.fact_payroll f ON f.employee_id = p.employee_id AND f.period_end_date = ?",
        agg="AVG(f.gross_pay)", params=["month_end"], fmt="₹{:,.0f}"),
    "attendance_rate": dict(
        label="Attendance rate (%)", min_group=5, pay=False,
        join="JOIN wh.fact_attendance_monthly f ON f.employee_id = p.employee_id AND f.period_end_date = ?",
        agg="100.0 * (SUM(f.present_days) + 0.5 * SUM(f.half_days_unpaid)) / NULLIF(SUM(f.scheduled_days), 0)",
        params=["month_end"], fmt="{:.1f}%"),
    "leave_days": dict(
        label="Approved leave days per person", min_group=5, pay=False,
        join=("LEFT JOIN (SELECT employee_id, SUM(days) AS d FROM wh.fact_leave "
              "WHERE status = 'Approved' AND start_date BETWEEN ? AND ? GROUP BY 1) f "
              "ON f.employee_id = p.employee_id"),
        agg="1.0 * SUM(COALESCE(f.d, 0)) / COUNT(DISTINCT p.employee_id)",
        params=["month_start", "month_end"], fmt="{:.2f}"),
}

ALL_METRICS = list(METRICS)
ALL_DIMS = list(DIMENSIONS)
ALL_LEVELS = ["Company", "Department", "Team"]

ROLE_RULES = {
    "ADMIN": dict(metrics=ALL_METRICS, dims=ALL_DIMS, levels=ALL_LEVELS),
    "HR": dict(metrics=ALL_METRICS, dims=ALL_DIMS, levels=ALL_LEVELS,
               pay_own_dept="Human Resources"),
    "MANAGER": dict(metrics=["headcount", "attendance_rate", "leave_days"],
                    dims=["work_mode", "city_tier"], levels=["Team"],
                    forced_scope={"department": "Product & Design", "team": "Design Systems"}),
    "EXECUTIVE": dict(metrics=["headcount", "attendance_rate", "leave_days"],
                      dims=["work_mode", "city_tier"], levels=["Company"]),
}

def access_error(role, metric, dim, level, scope):
    """Server-side re-check. The page only OFFERS allowed choices, but we never trust that."""
    r = ROLE_RULES[role]
    if metric not in r["metrics"]:
        return "Your role cannot see this metric."
    if dim not in r["dims"]:
        return "Your role cannot break data down by this dimension."
    if level not in r["levels"]:
        return "Your role cannot drill to this level."
    if role == "HR" and METRICS[metric]["pay"]:
        own = r["pay_own_dept"]
        company_wide_ok = (level == "Company" and dim in ("work_mode", "city_tier"))
        if scope.get("department") != own and not company_wide_ok:
            return f"HR can see salary detail only for {own}, or company-wide by work mode and city tier."
    return None