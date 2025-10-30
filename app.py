from utils import (
    load_mapping,
    extract_mapping_lines,
    extract_column_hints,
    extract_join_relationships,
    generate_aliases,
)
from vertex_client import VertexAgent
from bigquery_client import BigQueryAgent
import streamlit as st

PROJECT_ID = "telecom-data-lake"
REGION = "europe-west1"
BUCKET_NAME = "stage_data1"
SIEBEL_FILE = "Mapping files/siebel_mapping.txt"
ANTILLIA_FILE = "Mapping files/antillia_mapping.txt"

# ---------------- LOAD MAPPINGS ----------------
siebel_raw = load_mapping(BUCKET_NAME, SIEBEL_FILE)
antillia_raw = load_mapping(BUCKET_NAME, ANTILLIA_FILE)

tables = extract_mapping_lines(siebel_raw + "\n" + antillia_raw)
joins = extract_join_relationships(siebel_raw + "\n" + antillia_raw)
column_context = extract_column_hints(siebel_raw + "\n" + antillia_raw)
alias_map = generate_aliases(tables)

vertex_agent = VertexAgent(PROJECT_ID, REGION, tables, tables, column_context, joins, alias_map)
bq_agent = BigQueryAgent(PROJECT_ID)

st.title("📊 Telecom Data Assistant (Dynamic Context)")
prompt = st.text_area("💬 Ask a question:")

if st.button("🚀 Run Query"):
    try:
        sql = vertex_agent.prompt_to_sql(prompt)
        st.code(sql, language="sql")
        df = bq_agent.execute(sql)
        st.dataframe(df)
    except Exception as e:
        st.error(f"❌ Error: {e}")
