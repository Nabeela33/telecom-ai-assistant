from google.cloud import storage

def load_mapping(bucket_name, file_name):
    """Load text file mapping from GCS."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    data = blob.download_as_text()
    return data
