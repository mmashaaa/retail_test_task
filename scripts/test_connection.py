"""Manual BigQuery connectivity smoke check (not a pytest test).

Run directly:  python scripts/test_connection.py
"""
import os
from dotenv import load_dotenv
from google.cloud import bigquery


def main():
    load_dotenv()
    client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID"))
    query = "SELECT COUNT(*) as cnt FROM `bigquery-public-data.thelook_ecommerce.orders`"
    for row in client.query(query).result():
        print(f"BigQuery connection OK. Orders count: {row.cnt}")


if __name__ == "__main__":
    main()
