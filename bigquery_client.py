from google.cloud import bigquery

class BigQueryAgent:
    def __init__(self, project_id):
        self.client = bigquery.Client(project=project_id)

    def execute(self, query: str):
        try:
            df = self.client.query(query).to_dataframe()
            return df
        except Exception as e:
            raise RuntimeError(f"BigQuery execution failed: {e}")
