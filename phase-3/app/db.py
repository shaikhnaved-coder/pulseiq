from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB = Path(__file__).resolve().parent.parent / "05_Starter" / "pulseiq_metrics.duckdb"


def get_connection():
    return duckdb.connect(str(DB), read_only=True)


@st.cache_data
def query(sql: str) -> pd.DataFrame:
    con = get_connection()
    try:
        return con.execute(sql).fetchdf()
    finally:
        con.close()
