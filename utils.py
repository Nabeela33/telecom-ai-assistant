from google.cloud import storage

def load_mapping(bucket_name: str, file_name: str) -> str:
    """
    Load a mapping file from a GCS bucket and return as string.
    Raises a RuntimeError if the file cannot be found.
    """
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        data = blob.download_as_text()
        return data
    except Exception as e:
        raise RuntimeError(f"Failed to load mapping {file_name}: {e}")
