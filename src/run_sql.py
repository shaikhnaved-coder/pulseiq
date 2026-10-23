import os
import duckdb

con = duckdb.connect("05_Starter/pulseiq.duckdb")
con.execute(open("src/mymetrics.sql", encoding="utf-8").read())

catalog = con.execute("""
    SELECT metric_id, metric_name, business_definition, source_table,
           owner_team, minimum_group_size, metric_view
    FROM metrics.metric_catalog
    ORDER BY metric_id
""").fetchdf()

print(catalog[["metric_id", "metric_name", "source_table", "owner_team", "metric_view"]].to_string())
print()
print("Metrics in catalog:", len(catalog))
print("Metrics with no view:", int(catalog["metric_view"].isna().sum()))

# save the catalog as evidence for your report
os.makedirs("docs", exist_ok=True)
catalog.to_csv("docs/metric_catalog.csv", index=False)
print("Saved docs/metric_catalog.csv")