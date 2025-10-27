import pandas as pd
from google.cloud import storage
import streamlit as st

def load_mapping(bucket_name, blob_path):
    """
    Load a mapping file from Google Cloud Storage or local path.
    Returns a list of lines (non-empty, stripped).
    """

    try:
        # Initialize GCS client
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        # Download text content
        data = blob.download_as_text()
        lines = [line.strip() for line in data.splitlines() if line.strip()]

        st.sidebar.write(f"📄 Loaded `{blob_path}` ({len(lines)} lines)")
        return lines

    except Exception as e:
        st.sidebar.error(f"❌ Error loading mapping file `{blob_path}`: {e}")
        raise RuntimeError(f"Failed to load mapping {blob_path}: {e}")
