from google.cloud import storage
import re

def load_mapping(bucket_name: str, file_path: str) -> str:
    """
    Load a text file from GCS. `file_path` can include spaces (e.g., 'Mapping files/siebel_mapping.txt').
    """
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        if not blob.exists():
            raise RuntimeError(f"GCS object not found: gs://{bucket_name}/{file_path}")
        return blob.download_as_text()
    except Exception as e:
        raise RuntimeError(f"Failed to load mapping {file_path}: {e}")

# fully-qualified table: project.dataset.table
FQ_TABLE_RE = re.compile(r"\b([\w\-]+)\.([\w\-]+)\.([\w\-_]+)\b")

def parse_allowed_tables(mapping_text: str) -> set:
    """
    Parse mapping text and return a set of fully-qualified table names found.
    Accepts lines like:
      telecom-data-lake.o_siebel.siebel_accounts
      accounts = telecom-data-lake.o_siebel.siebel_accounts
    """
    tables = set()

    for line in mapping_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # key = value form
        if "=" in line:
            _, val = line.split("=", 1)
            m = FQ_TABLE_RE.search(val.strip())
            if m:
                tables.add(".".join(m.groups()))
            continue

        # bare FQ table name in line
        m = FQ_TABLE_RE.search(line)
        if m:
            tables.add(".".join(m.groups()))

    return tables
