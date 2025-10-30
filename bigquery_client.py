from google.cloud import bigquery
import pandas as pd

class BigQueryAgent:
    def __init__(self, project_id: str):
        self.client = bigquery.Client(project=project_id)

    def execute(self, query: str) -> pd.DataFrame:
        """Runs a SQL query in BigQuery and returns results as a DataFrame."""
        try:
            job = self.client.query(query)
            result = job.result()
            df = result.to_dataframe()
            return df
        except Exception as e:
            raise RuntimeError(f"BigQuery execution failed: {e}")
