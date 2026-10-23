import duckdb, glob

# 1. Look inside the database
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
rows = con.execute("""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_name ILIKE '%dq%' OR table_name ILIKE '%catalog%'
""").fetchall()
print("Tables found in database:", rows)

# 2. Look for files
files = glob.glob("**/*dq_checks*", recursive=True)
print("Files found:", files)