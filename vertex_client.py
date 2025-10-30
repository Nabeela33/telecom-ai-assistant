from vertexai.preview.generative_models import GenerativeModel
import vertexai

class VertexAgent:
    def __init__(self, project_id: str, region: str):
        """Initialize VertexAI client with Gemini 2.5 Flash."""
        vertexai.init(project=project_id, location=region)
        self.client = GenerativeModel("gemini-2.5-flash")

    def prompt_to_sql(self, prompt: str, siebel_mapping: str, antillia_mapping: str) -> str:
        """
        Converts a natural language question into SQL using Gemini.
        Takes mapping context from Siebel and Antillia mappings.
        """
        system_prompt = f"""
        You are a Telecom Data SQL expert.
        Use the following database mappings and examples to generate
        a BigQuery-compatible SQL query based on the user's request.

        -----------------
        Siebel Mapping:
        {siebel_mapping}
        -----------------
        Antillia Mapping:
        {antillia_mapping}
        -----------------
        Rules:
        - Use correct project and dataset names exactly as provided.
        - Use fully qualified table names (e.g. `telecom-data-lake.gibantillia.billing_products`)
        - Only return SQL. Do NOT include explanations or markdown.
        - Limit results to 50 rows unless the user specifies otherwise.
        -----------------

        User prompt: {prompt}
        """

        response = self.client.generate_content(system_prompt)
        sql_query = response.text.strip()

        # Fallback if Gemini returns something weird
        if not sql_query.lower().startswith("select"):
            sql_query = "SELECT * FROM `telecom-data-lake.sample_dataset.sample_table` LIMIT 10"

        return sql_query

    def summarize_text(self, text_prompt: str) -> str:
        """Summarizes plain text or dataset output."""
        try:
            response = self.client.generate_content(text_prompt)
            return response.text.strip()
        except Exception as e:
            return f"Failed to summarize: {e}"
