import re
from typing import Iterable, List, Set

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

SQL_MODEL = "gemini-2.5-flash"  # or gemini-2.0-flash-exp if enabled #gemini-2.0-flash-lite #gemini-1.5-flash

SELECT_ONLY_PATTERN = re.compile(r"^\s*SELECT\b", re.IGNORECASE | re.DOTALL)
FQ_TABLE_PATTERN = re.compile(r"([`\"]?[\w\-]+[`\"]?\.[`\"]?[\w\-]+[`\"]?\.[`\"]?[\w\-_]+[`\"]?)")

class VertexAgent:
    def __init__(self, project_id: str, region: str, allowed_tables: Iterable[str]):
        self.project_id = project_id
        self.region = region
        self.allowed_tables = set([self._strip_quotes(t) for t in allowed_tables])

        vertexai.init(project=project_id, location=region)
        self.model = GenerativeModel(SQL_MODEL)
        self.generation_config = GenerationConfig(
            temperature=0.1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
        )

    @staticmethod
    def _strip_quotes(s: str) -> str:
        return s.replace("`", "").replace('"', "").strip()

    def prompt_to_sql(self, user_prompt: str) -> str:
        """
        Generate BigQuery Standard SQL. Enforce SELECT-only and require tables from allowed list.
        """
        system = f"""
You are a senior data engineer. Write **BigQuery Standard SQL** that answers the user's question.
**Rules:**
- Use ONLY these fully-qualified tables (project.dataset.table):
{chr(10).join(f"- `{t}`" for t in sorted(self.allowed_tables))}
- Use backticks around table names.
- SELECT-only (no INSERT/UPDATE/DELETE/CREATE).
- Prefer explicit column lists if easy; else use SELECT * for brevity.
- If no LIMIT present, add LIMIT 200.
- Do not invent tables or columns not in the list above.
- If the user's request cannot be answered with these tables, return a simple SELECT with LIMIT 0 and a comment explaining why.
        """.strip()

        prompt = f"{system}\n\nUser request:\n{user_prompt}\n\nSQL:"
        resp = self.model.generate_content(prompt, generation_config=self.generation_config)
        text = resp.text or ""

        # Extract SQL code block or fallback to the whole text
        sql_match = re.search(r"```sql(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
        sql = sql_match.group(1).strip() if sql_match else text.strip()

        # Ensure it starts with SELECT
        if not self.is_select_only(sql):
            # Try to trim comments and re-check
            stripped = re.sub(r"^--.*?$", "", sql, flags=re.MULTILINE).strip()
            if not self.is_select_only(stripped):
                raise RuntimeError("Generated SQL is not SELECT-only. Refusing to run.")
            sql = stripped

        # Add LIMIT if missing
        if not re.search(r"\bLIMIT\s+\d+\b", sql, flags=re.IGNORECASE):
            sql += "\nLIMIT 200"

        return sql

    def find_disallowed_tables(self, sql: str) -> List[str]:
        """
        Return table refs in SQL that are not in allowed_tables.
        """
        found: Set[str] = set()
        for m in FQ_TABLE_PATTERN.finditer(sql):
            t = self._strip_quotes(m.group(1))
            found.add(t)
        return sorted([t for t in found if t not in self.allowed_tables])

    def is_select_only(self, sql: str) -> bool:
        return bool(SELECT_ONLY_PATTERN.search(sql))

    def summarize_text(self, text: str) -> str:
        resp = self.model.generate_content(
            f"Summarize the following for a business audience:\n{text}",
            generation_config=self.generation_config
        )
        return resp.text or ""
