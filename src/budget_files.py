import os
import pandas as pd

keywords = ["budget", "kpi", "target"]

for root, dirs, files in os.walk("."):
    # skip folders that only hold libraries or old copies
    dirs[:] = [d for d in dirs if d not in ("venv", ".venv", ".git", "_scratch", "__pycache__")]
    for f in files:
        path = os.path.join(root, f)
        if any(k in f.lower() for k in keywords):
            print("FILE:", path)
        if f.lower().endswith((".xlsx", ".xls")) and not f.startswith("~$"):
            try:
                sheets = pd.ExcelFile(path).sheet_names
                hits = [s for s in sheets if any(k in s.lower() for k in keywords)]
                if hits:
                    print("SHEET(S) in", path, "->", hits)
            except Exception as e:
                print("Could not read", path, "-", e)