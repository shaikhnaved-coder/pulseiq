import duckdb, itertools

DB_PATH = "05_Starter/pulseiq.duckdb"
SCHEMA = "clean"
con = duckdb.connect(DB_PATH, read_only=True)

tables = [r[0] for r in con.sql(f"""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = '{SCHEMA}' AND (table_name LIKE 'dim\\_%' ESCAPE '\\' OR table_name LIKE 'fact\\_%' ESCAPE '\\')
    ORDER BY table_name""").fetchall()]

for name in tables:
    full = f'"{SCHEMA}"."{name}"'
    n = con.sql(f"SELECT COUNT(*) FROM {full}").fetchone()[0]
    cols = [r[0] for r in con.sql(f"""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = '{SCHEMA}' AND table_name = '{name}'
        ORDER BY ordinal_position""").fetchall()]

    singles = [c for c in cols
               if con.sql(f'SELECT COUNT(DISTINCT "{c}") FROM {full}').fetchone()[0] == n]
    if singles:
        print(f"{name} ({n} rows): one-column key candidates -> {singles}")
        continue

    pair = None
    for a, b in itertools.combinations(cols, 2):
        d = con.sql(f"""SELECT COUNT(DISTINCT CAST("{a}" AS VARCHAR) || '|' || CAST("{b}" AS VARCHAR))
                        FROM {full}""").fetchone()[0]
        if d == n:
            pair = (a, b)
            break
    if pair:
        print(f"{name} ({n} rows): two-column key -> {list(pair)}")
    else:
        print(f"{name} ({n} rows): NO unique key in 1 or 2 columns (duplicate rows?)")