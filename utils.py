from google.cloud import storage

def load_mapping(bucket_name: str, file_path: str) -> str:
    """Load mapping text file from GCS."""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        return blob.download_as_text()
    except Exception as e:
        raise RuntimeError(f"Failed to load mapping {file_path}: {e}")

def extract_mapping_lines(text: str) -> str:
    """Extract clean dataset references for display."""
    import re
    lines = []
    for line in text.splitlines():
        match = re.search(r'([\w\-]+\.[\w\-]+\.[\w\-_]+)', line)
        if match:
            lines.append(match.group(1))
    return "\n".join(sorted(set(lines)))

def extract_column_hints(mapping_text: str) -> str:
    """Extract column name: description pairs for model context."""
    lines = []
    for line in mapping_text.splitlines():
        if line.strip().startswith("-") and ":" in line:
            parts = line.strip("- ").split(":", 1)
            if len(parts) == 2:
                lines.append(f"{parts[0].strip()}: {parts[1].strip()}")
    return "\n".join(lines)
