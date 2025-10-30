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
    """Return all dataset.table paths."""
    return sorted(set(re.findall(r"([\w\-]+\.[\w\-]+\.[\w\-_]+)", text)))


def extract_column_hints(mapping_text: str) -> str:
    """Extract 'column: description' pairs for model grounding."""
    lines = []
    for line in mapping_text.splitlines():
        if line.strip().startswith("-") and ":" in line:
            col, desc = line.strip("- ").split(":", 1)
            lines.append(f"{col.strip()}: {desc.strip()}")
    return "\n".join(lines)


def extract_join_relationships(mapping_text: str) -> list:
    """Extract JOIN and ON relationships dynamically."""
    joins = []
    for line in mapping_text.splitlines():
        if "JOIN" in line and "ON" in line:
            # capture typical pattern: table1.col = table2.col
            on_parts = re.findall(r"([\w\.`]+\.[\w_]+)\s*=\s*([\w\.`]+\.[\w_]+)", line)
            for left, right in on_parts:
                joins.append(f"{left} = {right}")
    return sorted(set(joins))


def generate_aliases(tables: list) -> dict:
    """Generate short, unique aliases based on last word of table name."""
    alias_map = {}
    for t in tables:
        alias = re.sub(r'[^a-zA-Z]', '', t.split(".")[-1])[:4].lower()  # short unique alias
        if alias in alias_map.values():
            alias += str(len(alias_map))
        alias_map[t] = alias
    return alias_map
