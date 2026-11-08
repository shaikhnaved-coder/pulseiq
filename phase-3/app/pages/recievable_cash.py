import duckdb, pandas as pd, streamlit as st
st.set_page_config(page_title="Receivables & Cash", layout="wide")
con = duckdb.connect("05_Starter/pulseiq.duckdb", read_only=True)
q = lambda sql: con.execute(sql).fetchdf()

st.title("Receivables and Cash Flow")
st.info("**Open invoice rule:** only SENT, OVERDUE and PARTIALLY_PAID are open. "
        "DRAFT, CANCELLED and PAID are not open. Open amount = balance due. "
        "Ageing = days past due at the data cutoff, in buckets 0-30, 31-60, 61-90 and 90+ "
        "(invoices not yet due sit in 0-30).")

order = ["0-30", "31-60", "61-90", "90+"]
ageing = q("SELECT bucket, invoices, open_amount FROM metrics.v_ar_ageing")
ageing["bucket"] = pd.Categorical(ageing["bucket"], order, ordered=True)
ageing = ageing.sort_values("bucket")
total = int(ageing["open_amount"].sum())
direct = int(q("SELECT sum(open_amount) s FROM metrics.v_ar_open")["s"][0])

c1, c2, c3 = st.columns(3)
c1.metric("Total open receivables", f"{total:,}")
c2.metric("Open invoices", int(ageing["invoices"].sum()))
c3.metric("Bucket check", "TIES" if total == direct else "DOES NOT TIE")

st.subheader("1. Receivables ageing")
st.bar_chart(ageing.set_index("bucket")["open_amount"])
st.dataframe(ageing, use_container_width=True, hide_index=True)

st.subheader("2. Average days to pay by client")
d = q("SELECT client, paid_invoices, avg_days_to_pay FROM metrics.v_days_to_pay ORDER BY avg_days_to_pay DESC")
st.bar_chart(d.set_index("client")["avg_days_to_pay"])
st.dataframe(d, use_container_width=True, hide_index=True)

st.subheader("3. Cash in vs cash out by month")
st.caption("Cash in = payments received. Cash out = monthly expenses from the P&L views.")
cash = q("SELECT * FROM metrics.v_cash_monthly")
st.line_chart(cash.set_index("month")[["cash_in", "cash_out"]])
st.dataframe(cash, use_container_width=True, hide_index=True)

st.subheader("4. Clients with the most overdue money")
o = q("SELECT * FROM metrics.v_overdue_by_client LIMIT 10")
st.bar_chart(o, x="client", y="overdue_amount", sort="-overdue_amount")
st.dataframe(o.style.format({"overdue_amount": "{:,.0f}"})
               .background_gradient(subset=["overdue_amount"], cmap="Reds"),
             use_container_width=True, hide_index=True)

st.subheader("5. Checked totals")
st.dataframe(pd.read_csv("docs/ar_bucket_check.csv"), use_container_width=True, hide_index=True)