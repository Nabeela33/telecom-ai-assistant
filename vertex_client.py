import re
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

class VertexAgent:
    def __init__(self, project_id, region, siebel_mapping, antillia_mapping, column_context=""):
        vertexai.init(project=project_id, location=region)
        self.model = GenerativeModel("gemini-2.5-flash")
        self.generation_config = GenerationConfig(temperature=0.3, max_output_tokens=2048)

        self.siebel_mapping = siebel_mapping
        self.antillia_mapping = antillia_mapping
        self.column_context = column_context

        # Collect allowed table names for grounding
        self.allowed_tables = re.findall(r"([\w\-]+\.[\w\-]+\.[\w\-_]+)", siebel_mapping + antillia_mapping)

    def is_select_only(self, sql: str) -> bool:
        return bool(re.match(r"(?is)^\s*select\b", sql))

    def prompt_to_sql(self, user_prompt: str) -> str:
        """Generate BigQuery SQL from natural language using Gemini."""
        context_hints = "\n".join(f"- {t}" for t in sorted(self.allowed_tables))

        system_prompt = f"""
You are a senior telecom data engineer. Generate **BigQuery Standard SQL** based only on the datasets below.
If the user mentions 'active', 'suspended', or similar, map it to the 'status' column if it exists.
Infer logical meanings from column descriptions.

### Allowed Tables
{context_hints}

### Column Semantics
{self.column_context}

Rules:
- Use only SELECT queries.
- Use backticks around table names.
- Add LIMIT 200 if not specified.
- Never invent columns.
- Prefer logical mapping (e.g., "active" → status='Active').
- Output SQL only.
        """

        full_prompt = f"{system_prompt}\n\nUser question:\n{user_prompt}\n\nSQL:"

        resp = self.model.generate_content(full_prompt, generation_config=self.generation_config)
        text = resp.text or ""

        sql_match = re.search(r"```sql(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
        sql = sql_match.group(1).strip() if sql_match else text.strip()

        if not self.is_select_only(sql):
            raise RuntimeError("Generated SQL is not a SELECT query.")

        if not re.search(r"\bLIMIT\s+\d+\b", sql, flags=re.IGNORECASE):
            sql += "\nLIMIT 200"

        return sql

    def summarize_text(self, text: str) -> str:
        """Summarize text or dataset insightfully."""
        prompt = f"Summarize the following dataset or query result:\n{text}"
        resp = self.model.generate_content(prompt, generation_config=self.generation_config)
        return resp.text or "No summary generated."
