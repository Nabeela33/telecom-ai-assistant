# Telecom Data Assistant

Natural language → Gemini → BigQuery SQL → Results in Streamlit.

## Prereqs

- GCP project with billing enabled
- Create / confirm these resources:
  - BigQuery tables:
    - `telecom-data-lake.o_siebel.siebel_accounts`
    - `telecom-data-lake.o_siebel.siebel_assets`
    - `telecom-data-lake.o_siebel.siebel_orders`
    - `telecom-data-lake.gibantillia.billing_accounts`
    - `telecom-data-lake.gibantillia.billing_products`
  - GCS bucket: `gs://stage_data1`
    - Upload mapping files:
      - `Mapping files/siebel_mapping.txt`
      - `Mapping files/antillia_mapping.txt`

## Local run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
streamlit run app.py
