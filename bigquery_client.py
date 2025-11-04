from google.cloud import bigquery

class BigQueryAgent:
    def __init__(self, project_id: str):
        self.client = bigquery.Client(project=project_id)

    def execute(self, query: str):
        """Run a query and return a pandas DataFrame."""
        try:
            job = self.client.query(query)
            df = job.result().to_dataframe()  # safer across versions
            return df
        except Exception as e:
            raise RuntimeError(f"BigQuery execution failed: {e}")
