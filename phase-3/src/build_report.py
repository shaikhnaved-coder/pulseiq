"""Build the monthly PulseIQ report pack.
Usage:  python src/build_report.py --month 2026-03
"""
import argparse
import os
from datetime import date

import duckdb
import pandas as pd
from openpyxl import load_workbook
from openpyxl.chart import BarChart, LineChart, Reference

DB_PATH = "05_Starter/pulseiq.duckdb"

# name, chart type, SQL.  {from_d} and {to_d} are dates, {from_m} and {to_m} are like 2026-03
REPORTS = [
    ("Headcount", "line", """
        SELECT month_start_date AS month, SUM(headcount) AS headcount
        FROM metrics.m01_headcount
        WHERE month_start_date BETWEEN '{from_d}' AND '{to_d}'
        GROUP BY 1 ORDER BY 1"""),

    ("Attrition", "line", """
        SELECT month_start_date AS month,
               ROUND(SUM(attrition_pct * group_size) / SUM(group_size), 2) AS attrition_pct
        FROM metrics.m04_attrition_monthly
        WHERE month_start_date BETWEEN '{from_d}' AND '{to_d}'
        GROUP BY 1 ORDER BY 1"""),

    ("Payroll cost", "line", """
        SELECT month_start_date AS month, ROUND(SUM(employer_cost), 0) AS employer_cost
        FROM metrics.m09_payroll_cost
        WHERE month_start_date BETWEEN '{from_d}' AND '{to_d}'
        GROUP BY 1 ORDER BY 1"""),

    ("Profit and loss", "bar", """
        SELECT month, revenue, expenses, net_profit
        FROM metrics.v_pl_monthly
        WHERE month BETWEEN '{from_m}' AND '{to_m}'
        ORDER BY month"""),

    ("Attendance", "line", """
        SELECT month_start_date AS month,
               ROUND(SUM(attendance_rate * group_size) / SUM(group_size), 4) AS attendance_rate
        FROM metrics.m13_attendance_rate
        WHERE month_start_date BETWEEN '{from_d}' AND '{to_d}'
        GROUP BY 1 ORDER BY 1"""),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--month", required=True, help="for example 2026-03")
    args = p.parse_args()

    period = pd.Period(args.month, freq="M")
    to_d = period.start_time.date()
    from_d = (period - 11).start_time.date()
    fmt = dict(from_d=from_d, to_d=to_d,
               from_m=str(period - 11), to_m=str(period))

    con = duckdb.connect(DB_PATH, read_only=True)

    # Data cut-off = latest month that really exists in the data
    latest = con.sql("SELECT MAX(month_start_date) AS d FROM metrics.m01_headcount").df()["d"][0]
    if pd.Timestamp(to_d) > pd.Timestamp(latest):
        print(f"WARNING: data only goes up to {latest}. Month {args.month} will be empty.")

    os.makedirs("reports", exist_ok=True)
    out = f"reports/PulseIQ_report_{args.month}.xlsx"

    with pd.ExcelWriter(out, engine="openpyxl") as xl:
        cover = pd.DataFrame({
            "Item": ["Report", "Month", "Date range shown", "Data cut-off", "Generated on"],
            "Value": ["PulseIQ monthly report", args.month,
                      f"{from_d} to {period.end_time.date()}",
                      str(latest)[:7] + " (latest month in the data)", str(date.today())],
        })
        cover.to_excel(xl, sheet_name="Cover", index=False)

        for name, _, sql in REPORTS:
            df = con.sql(sql.format(**fmt)).df()
            first = df.columns[0]
            df[first] = df[first].astype(str).str[:7]
            df.to_excel(xl, sheet_name=name, index=False)

    # Add charts
    wb = load_workbook(out)
    for name, kind, _ in REPORTS:
        ws = wb[name]
        if ws.max_row < 2:
            continue
        ch = LineChart() if kind == "line" else BarChart()
        ch.title = name
        ch.width, ch.height = 20, 9
        data = Reference(ws, min_col=2, max_col=ws.max_column, min_row=1, max_row=ws.max_row)
        cats = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
        ch.add_data(data, titles_from_data=True)
        ch.set_categories(cats)
        for s in ch.series:
            s.smooth = False
        ws.add_chart(ch, "G2")
        for col in "ABCD":
            ws.column_dimensions[col].width = 18
    wb["Cover"].column_dimensions["A"].width = 20
    wb["Cover"].column_dimensions["B"].width = 34
    wb.save(out)
    print("Created", out)


if __name__ == "__main__":
    main()