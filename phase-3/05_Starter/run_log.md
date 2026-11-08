

| Run | Rows in | Rows passed | Rows quarantined | Run fingerprint |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |

Result: the fingerprint and counts are identical on both runs, so the pipeline is safe to re-run.

================ SUMMARY (etl.summary) ================
tables checked        : 29
rows in               : 62770
rows passed (clean.*) : 62743   (counted in the clean tables: 62743)
rows quarantined      : 27   (counted in etl.quarantine: 27)
in = passed + quarantined for every table: YES
run fingerprint       : d98263eda563   (identical on every re-run of unchanged data)

================ SUMMARY (etl.summary) ================
tables checked        : 29
rows in               : 62770
rows passed (clean.*) : 62743   (counted in the clean tables: 62743)
rows quarantined      : 27   (counted in etl.quarantine: 27)
in = passed + quarantined for every table: YES
run fingerprint       : d98263eda563   (identical on every re-run of unchanged data)