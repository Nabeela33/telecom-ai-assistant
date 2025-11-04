from google.cloud import storage
import re

def load_mapping(bucket_name: str, file_path: str) -> str:
    """Load mapping text file from GCS."""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        return blob.download_as_text()
    except Exception as e:
        raise RuntimeError(f"Failed to load mapping {file_path}: {e}")

def extract_mapping_lines(text: str) -> list:
    """
    Return dataset paths found in mapping text.
    Matches: project.dataset.table or dataset.table (with/without backticks).
    """
    # capture backticked or plain identifiers with 1 or 2 dots
    pattern = r"`?([\w\-]+\.[\w\-]+(?:\.[\w\-_]+)?)`?"
    hits = re.findall(pattern, text)
    # normalize duplicates and return sorted unique list
    return sorted(set(hits))

def extract_column_hints(mapping_text: str) -> str:
    """Extract 'column: description' pairs for model grounding (very loose heuristic)."""
    lines = []
    for line in mapping_text.splitlines():
        line = line.strip()
        if (line.startswith("-") or line.startswith("*")) and ":" in line:
            col, desc = line.lstrip("-* ").split(":", 1)
            lines.append(f"{col.strip()}: {desc.strip()}")
    return "\n".join(lines)

def extract_join_relationships(mapping_text: str) -> list:
    """Extract JOIN and ON relationships dynamically (case-insensitive heuristic)."""
    joins = []
    for line in mapping_text.splitlines():
        if "join" in line.lower() and "on" in line.lower():
            on_parts = re.findall(r"([\w\.`]+\.[\w_]+)\s*=\s*([\w\.`]+\.[\w_]+)", line, flags=re.IGNORECASE)
            for left, right in on_parts:
                joins.append(f"{left} = {right}")
    return sorted(set(joins))

def generate_aliases(tables: list) -> dict:
    """Generate short, unique aliases based on last part of table name."""
    alias_map = {}
    seen = set()
    for t in tables:
        last = t.split(".")[-1]
        base = re.sub(r"[^a-zA-Z]", "", last)[:4].lower() or "t"
        alias = base
        i = 1
        while alias in seen:
            alias = f"{base}{i}"
            i += 1
        alias_map[t] = alias
        seen.add(alias)
    return alias_map
