import duckdb
import polars as pl
import os
import numpy as np
import pandas as pd
import datetime

start = datetime.datetime.now() 
print(start)


con = duckdb.connect()
parquet_path = "~/Downloads/medicaid-provider-spending.parquet"
con.execute(f"CREATE VIEW medicaid AS SELECT * FROM read_parquet('{parquet_path}')")

# summary_stats = con.execute(
#     """
#     SELECT
#         COUNT(*) AS total_rows,
#         SUM(TOTAL_PAID) AS total_spend,
#         SUM(TOTAL_CLAIMS) AS total_claims,
#         COUNT(DISTINCT BILLING_PROVIDER_NPI_NUM) AS distinct_billing_npi,
#         COUNT(DISTINCT SERVICING_PROVIDER_NPI_NUM) AS distinct_servicing_npi,
#         COUNT(DISTINCT HCPCS_CODE) AS unique_services
#     FROM medicaid
#     """
# ).df()
# print("Summary stats done")
# summary_stats.to_csv("data/summary_stats.csv")


# hcpcs = con.execute(
#         """
#         SELECT
#             HCPCS_CODE,
#             SUM(TOTAL_CLAIMS) AS total_claims,
#             SUM(TOTAL_PAID) AS total_paid
#         FROM medicaid
#         WHERE HCPCS_CODE IS NOT NULL
#         GROUP BY HCPCS_CODE
#         """
#     ).df()


# hcpcs.to_csv("data/hcpcs.csv")
# print("HCPCS done")



# con.execute(
#     """
#     SELECT
#         SUM(TOTAL_PAID) AS total_paid,
#         SUM(TOTAL_CLAIMS) AS total_claims,
#         CLAIM_FROM_MONTH
#     FROM medicaid
#     GROUP BY CLAIM_FROM_MONTH
#     ORDER BY CLAIM_FROM_MONTH
#     """
# ).df().to_csv("data/per_month.csv")

con.execute(
    """
    SELECT
        SUBSTR(CAST(CLAIM_FROM_MONTH AS VARCHAR), 1, 4) AS year,
        SUM(TOTAL_PAID) AS total_paid,
        COUNT(DISTINCT BILLING_PROVIDER_NPI_NUM) AS distinct_billing_npi,
        COUNT(DISTINCT SERVICING_PROVIDER_NPI_NUM) AS distinct_servicing_npi
    FROM medicaid
    GROUP BY 1
    ORDER BY 1
    """
).df().to_csv("data/agg_year.csv")
print("Year aggregation done")

con.execute(
    "SELECT column_name FROM (DESCRIBE SELECT * FROM medicaid) ORDER BY column_name"
).df().to_csv("data/columns.csv")
print("Columns done")





    
    
    


print(datetime.datetime.now())
print(datetime.datetime.now() - start)

