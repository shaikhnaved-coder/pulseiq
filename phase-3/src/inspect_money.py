import duckdb, pandas as pd
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 200, "display.max_colwidth", 70)

con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)

print("=== dim_account check ===")
print(con.execute("select is_group, statement, account_type, count(*) n from wh.dim_account group by all order by 2,3,1").df())

for t in ["fact_ledger", "fact_expense", "fact_invoice", "dim_vendor"]:
    n = con.execute(f"select count(*) from wh.{t}").fetchone()[0]
    print(f"\n=== wh.{t}  ({n} rows) ===")
    print(con.execute(f"select column_name, data_type from information_schema.columns where table_schema='wh' and table_name='{t}' order by ordinal_position").df().to_string(index=False))
    print(con.execute(f"select * from wh.{t} limit 5").df())

print("\n=== metrics.m16_revenue ===")
try:
    print(con.execute("select sql from duckdb_views() where schema_name='metrics' and view_name='m16_revenue'").fetchall())
    print(con.execute("select * from metrics.m16_revenue limit 5").df())
except Exception as e:
    print("could not read:", e)

print("\n=== README sheet ===")
xl = pd.ExcelFile("03_Data/PulseIQ_Dataset.xlsx")
print("sheets:", xl.sheet_names)
for s in xl.sheet_names:
    if "readme" in s.lower():
        print(pd.read_excel(xl, sheet_name=s, header=None).to_string())