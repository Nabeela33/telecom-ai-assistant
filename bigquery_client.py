import pandas as pd
from google.cloud import bigquery
import importlib.util

class BigQueryAgent:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = bigquery.Client(project=project_id)

        # Ensure db-dtypes is installed for BigQuery → pandas integration
        if not importlib.util.find_spec("db_dtypes"):
            raise ImportError(
                "BigQuery execution failed: Please install the 'db-dtypes' package.\n"
                "Run: pip install db-dtypes"
            )

    def execute(self, sql_query: str) -> pd.DataFrame:
        try:
            job = self.client.query(sql_query)
            result = job.result()
            df = result.to_dataframe()  # requires db-dtypes
            return df
        except Exception as e:
            raise RuntimeError(f"BigQuery execution failed: {e}")
