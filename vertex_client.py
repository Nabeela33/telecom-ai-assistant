import re
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

class VertexAgent:
    def __init__(
        self,
        project_id: str,
        region: str,
        siebel_mapping: list,
        antillia_mapping: list,
        column_context: str,
        joins: list | None = None,
        alias_map: dict | None = None,
    ):
        vertexai.init(project=project_id, location=region)
        self.model = GenerativeModel("gemini-2.5-flash")
        self.generation_config = GenerationConfig(temperature=0.2, max_output_tokens=2048)

        # Context
        self.siebel_mapping = siebel_mapping or []
        self.antillia_mapping = antillia_mapping or []
        self.column_context = column_context or ""
        self.joins = joins or []
        self.alias_map = alias_map or {}

        # Flatten allowed tables
        self.allowed_tables = list({*self.siebel_mapping, *self.antillia_mapping})

    def prompt_to_sql(self, user_prompt: str) -> str:
        """Generate BigQuery SQL from natural language using dynamic context."""
        dataset_list = "\n".join(f"- {t}" for t in self.allowed_tables) or "- (no tables detected)"
        join_info = "\n".join(f"- {j}" for j in self.joins) or "- (no explicit joins detected)"
        alias_info = "\n".join(f"- {t} → {a}" for t, a in self.alias_map.items()) or "- (no aliases)"

        system_prompt = f"""
You are an expert telecom data engineer.
Generate **BigQuery Standard SQL** based only on the available datasets.

### Datasets
{dataset_list}

### Column Semantics
{self.column_context}

### Join Relationships (learned from mappings)
{join_info}

### Recommended Aliases
{alias_info}

### Rules
- Always prefix columns with their table alias when using multiple tables.
- Always use explicit JOINs with ON conditions.
- Use correct columns based on context (e.g., status = 'Active' in the relevant table).
- Do not invent tables or columns.
- Add LIMIT 200 if not specified.
- Output valid SQL only (no markdown, no explanations).
"""
        full_prompt = f"{system_prompt}\n\nUser question:\n{user_prompt}\n\nSQL:"

        resp = self.model.generate_content(full_prompt, generation_config=self.generation_config)
        text = (resp.text or "").strip()

        # Extract SQL if model used code fences; otherwise take as-is
        sql_match = re.search(r"```sql(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
        sql = sql_match.group(1).strip() if sql_match else text

        if not sql.lower().lstrip().startswith("select"):
            raise RuntimeError("Generated SQL is not a SELECT query.")
        if "limit" not in sql.lower():
            sql += "\nLIMIT 200"

        return sql

    def summarize_text(self, text: str) -> str:
        prompt = f"Summarize this dataset:\n{text}"
        resp = self.model.generate_content(prompt, generation_config=self.generation_config)
        return resp.text or "No summary available."
