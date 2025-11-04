from vertexai import init
from vertexai.generative_models import GenerativeModel

class VertexAgent:
    """
    VertexAgent is a lightweight wrapper around Gemini (Vertex AI Generative Models)
    for generating BigQuery SQL queries from natural language prompts.
    """

    def __init__(self, project_id: str, region: str):
        """Initialize the Gemini model client."""
        init(project=project_id, location=region)
        # Use a fast, cost-efficient model variant — adjust if needed.
        self.model = GenerativeModel("gemini-2.5-flash")

    def prompt_to_sql(self, user_prompt: str) -> str:
        """
        Converts a natural language question or instruction into a valid BigQuery SQL query.
        The model returns SQL only — no explanations or markdown.
        """
        system_instruction = (
            "You are an expert BigQuery SQL generator. "
            "Your task is to write syntactically correct, efficient SQL queries "
            "based on the user's request. "
            "Do not include any explanations, markdown, or text — output only SQL."
        )

        full_prompt = f"{system_instruction}\n\nUSER REQUEST:\n{user_prompt}"

        try:
            response = self.model.generate_content(full_prompt)
            sql = response.text.strip()
            # Safety: remove any accidental markdown formatting
            sql = sql.replace("```sql", "").replace("```", "").strip()
            return sql
        except Exception as e:
            raise RuntimeError(f"Vertex AI generation failed: {e}")
