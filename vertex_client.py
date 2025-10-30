from vertexai.generative_models import GenerativeModel, Part
import vertexai
import re

class VertexAgent:
    def __init__(self, project_id, region):
        vertexai.init(project=project_id, location=region)
        self.model = GenerativeModel("gemini-1.5-flash")

    def prompt_to_sql(self, user_prompt, siebel_mapping, antillia_mapping):
        """
        Generates a BigQuery SQL query from a user prompt and mapping context.
        """
        context = f"""
You are a data engineer for a telecom company.

Use these dataset mappings to generate valid BigQuery SQL:

Siebel Datasets:
{siebel_mapping}

Antillia Datasets:
{antillia_mapping}

Rules:
- Always use real BigQuery datasets (telecom-data-lake.*).
- Do NOT use placeholders like sample_dataset or sample_table.
- Generate complete, valid SQL queries.
- Never invent table names that are not listed above.
"""

        full_prompt = f"{context}\n\nUser question:\n{user_prompt}\n\nSQL Query:"
        response = self.model.generate_content(full_prompt)

        sql = response.text.strip()

        # Safety check
        if "sample_dataset" in sql.lower():
            raise RuntimeError("Gemini returned a placeholder dataset. Please verify your mapping context.")
        if not re.search(r"FROM `telecom-data-lake\.", sql):
            raise RuntimeError("Gemini did not use the correct dataset name in the query.")

        return sql

    def summarize_text(self, text):
        """
        Generates a concise summary of text (used for summarizing dataset results).
        """
        prompt = f"Summarize this dataset insightfully and briefly:\n\n{text}"
        response = self.model.generate_content(prompt)
        return response.text.strip()
