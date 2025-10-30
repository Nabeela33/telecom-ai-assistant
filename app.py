import streamlit as st
from utils import load_mapping
from vertex_client import VertexAgent
from bigquery_client import BigQueryAgent
import pandas as pd
import altair as alt
import re

# ---------------- CONFIG ----------------
PROJECT_ID = "telecom-data-lake"
REGION = "europe-west2"
BUCKET_NAME = "stage_data1"

# ---------------- HELPER: Clean mapping text ----------------
def extract_mapping_lines(text):
    """
    Extracts only valid key=value mappings from a descriptive mapping file.
    Example: 'accounts = telecom-data-lake.o_siebel.siebel_accounts'
    """
    if not text:
        return ""
    lines = text.splitlines()
    mappings = []
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            key, val = line.split("=", 1)
            mappings.append(f"{key.strip()} = {val.strip()}")
    return "\n".join(mappings)

# ---------------- LOAD MAPPINGS ----------------
st.sidebar.title("⚙️ Configuration")
st.sidebar.info("Mappings from Siebel & Antillia guide Gemini SQL generation.")

with st.spinner("📥 Loading mapping files from GCS..."):
    raw_siebel = load_mapping(BUCKET_NAME, "Mapping files/siebel_mapping.txt")
    raw_antillia = load_mapping(BUCKET_NAME, "Mapping files/antillia_mapping.txt")

# Extract only clean mapping pairs
siebel_mapping = extract_mapping_lines(raw_siebel)
antillia_mapping = extract_mapping_lines(raw_antillia)

with st.expander("🗺️ Preview Mappings"):
    st.subheader("Siebel Mapping (Parsed)")
    st.text(siebel_mapping)
    st.subheader("Antillia Mapping (Parsed)")
    st.text(antillia_mapping)

# ---------------- INIT AGENTS ----------------
vertex_agent = VertexAgent(PROJECT_ID, REGION)
bq_agent = BigQueryAgent(PROJECT_ID)

# ---------------- STREAMLIT UI ----------------
st.title("📊 Telecom Data Query Agent")
st.markdown("Ask questions about your telecom data — Gemini will generate SQL and run it in BigQuery.")

prompt = st.text_area("💬 Enter your query:")

if st.button("🚀 Run Query"):
    if not prompt.strip():
        st.warning("Please enter a question or query prompt!")
    else:
        try:
            # Generate SQL
            with st.spinner("🧠 Generating SQL using Gemini..."):
                sql_query = vertex_agent.prompt_to_sql(prompt, siebel_mapping, antillia_mapping)
            st.subheader("🪄 Generated SQL")
            st.code(sql_query, language="sql")

            # Execute SQL
            with st.spinner("📡 Executing SQL in BigQuery..."):
                df = bq_agent.execute(sql_query)

            st.success(f"✅ Query executed successfully! {len(df)} rows returned.")

            # Collapsible data view
            with st.expander("📋 View Query Results"):
                st.dataframe(df)

            # Interactive chart
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            if numeric_cols:
                st.subheader("📈 Charts")
                col_to_plot = st.selectbox("Select numeric column to visualize:", numeric_cols)
                chart = alt.Chart(df.reset_index()).mark_bar().encode(
                    x=alt.X("index", title="Row"),
                    y=alt.Y(col_to_plot, title=col_to_plot)
                ).interactive()
                st.altair_chart(chart, use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error: {e}")
