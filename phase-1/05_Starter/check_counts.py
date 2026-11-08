import duckdb, glob, os
import pandas as pd

con = duckdb.connect("pulseiq.duckdb")
ok = True
for f in sorted(glob.glob("../03_Data/csv/*.csv")):
    t = os.path.basename(f)[:-4]
    csv_rows = len(pd.read_csv(f))
    db_rows = con.execute(f"SELECT COUNT(*) FROM raw.{t}").fetchone()[0]
    flag = "OK      " if csv_rows == db_rows else "MISMATCH"
    ok = ok and (csv_rows == db_rows)
    print(f"{flag} {t:<30} csv={csv_rows:>6}  db={db_rows:>6}")
print("ALL MATCH" if ok else "CHECK THE MISMATCH LINES ABOVE")