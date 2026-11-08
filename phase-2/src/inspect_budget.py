import pandas as pd

for name, rows in [("budget_payroll_dept_month", 12), ("kpi_targets", 40)]:
    df = pd.read_csv(f"03_Data/csv/{name}.csv")
    print("=" * 20, name, "=" * 20)
    print("Shape (rows, columns):", df.shape)
    print("Column types:")
    print(df.dtypes)
    print("First rows:")
    print(df.head(rows).to_string())
    print()