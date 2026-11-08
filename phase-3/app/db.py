from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB = Path(__file__).resolve().parent.parent / "05_Starter" / "pulseiq.duckdb"


@st.cache_data
def query(sql: str) -> pd.DataFrame:
    low = sql.lower()
    for banned in ("raw.", "clean.", "wh.", "etl.", "dq."):
        if banned in low:
            raise ValueError(f"The app may only read metrics views, not {banned}")
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute(sql).fetchdf()
    finally:
        con.close()