import duckdb, os

# find the database that actually contains the warehouse
candidates = ["05_Starter/pulseiq.duckdb", "pulseiq.duckdb"]
con = None
for path in candidates:
    if os.path.exists(path):
        c = duckdb.connect(path, read_only=True)
        n = c.execute("select count(*) from information_schema.tables where table_name='dim_account'").fetchone()[0]
        if n > 0:
            con = c
            print("Using database:", path)
            break
        c.close()

if con is None:
    raise SystemExit("dim_account not found in either database")

# 1. where dim_account lives, and other money-related tables
print("\n--- money related tables ---")
rows = con.execute("""
    select table_schema, table_name from information_schema.tables
    where lower(table_name) similar to '.*(account|gl|ledger|revenue|expense|vendor|invoice|journal|pnl|finance|budget).*'
    order by 1, 2
""").fetchall()
for r in rows:
    print(r)

# 2. columns of dim_account
print("\n--- dim_account columns ---")
cols = con.execute("select table_schema, column_name, data_type from information_schema.columns where table_name='dim_account' order by ordinal_position").fetchall()
for c in cols:
    print(c)

# 3. the rows themselves
schema = cols[0][0]
df = con.execute(f"select * from {schema}.dim_account").df()
print("\n--- dim_account rows:", len(df), "---")
import pandas as pd
pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 100)
print(df.head(60))