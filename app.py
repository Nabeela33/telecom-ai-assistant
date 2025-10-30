import streamlit as st
from utils import load_mapping
from vertex_client import VertexAgent
from bigquery_client import BigQueryAgent
import pandas as pd
import re
import altair as alt

# ---------------- CONFIG ----------------
PROJECT_ID = "telecom-data-lake"
REGION = "europe-west2"
BUCKET_NAME = "stage_data1"
SIEBEL_FILE = "Mapping files/siebel_mapping.txt"
ANTILLIA_FILE = "Mapping files/antillia_mapping.txt"

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Configuration")
st.sidebar.info("Mappings guide SQL generation across systems.")
st.sidebar.caption("Powered by Gemini 2.5 Flash + BigQuery")

# ---------------- INIT ----------------
vertex_agent = VertexAgent(PROJECT_ID, REGION)
bq_agent = BigQueryAgent(PROJECT_ID)

# ---------------- FUNCTION: Extract Clean Dataset References ----------------
def extract_mapping_lines(text):
    """
    Extracts dataset and table mappings and returns them in a structured format
    for better prompt clarity.
    """
    if not text:
        return ""

    dataset_refs = []
    lines = text.splitlines()
    for line in lines:
        # Capture explicit BigQuery table references
        match = re.search(r'([\w\-]+\.[\w\-]+\.[\w\-_]+)', line)
        if match:
            dataset_refs.append(match.group(1))
        elif "=" in line and "telecom-data-lake" in line:
            key, val = line.split("=", 1)
            dataset_refs.append(f"{key.strip()} = {val.strip()}")

    if not dataset_refs:
        return "No dataset references found."

    # Format cleanly for Vertex AI
    formatted = "\n".join([
        f"- {ref}" for ref in sorted(set(dataset_refs))
    ])

    return (
        "The following BigQuery tables are available for querying:\n"
        f"{formatted}\n\n"
        "Use these real table names when writing SQL."
    )

# ---------------- LOAD MAPPINGS ----------------
with st.spinner("📥 Loading mapping files from GCS..."):
    siebel_raw = load_mapping(BUCKET_NAME, SIEBEL_FILE)
    antillia_raw = load_mapping(BUCKET_NAME, ANTILLIA_FILE)

siebel_mapping = extract_mapping_lines(siebel_raw)
antillia_mapping = extract_mapping_lines(antillia_raw)

# ---------------- STREAMLIT STATE ----------------
if "df" not in st.session_state:
    st.session_state.df = None
if "sql_query" not in st.session_state:
    st.session_state.sql_query = None
if "table_name" not in st.session_state:
    st.session_state.table_name = None

# ---------------- MAIN UI ----------------
st.title("📊 Telecom Data Assistant")
st.markdown("Hello 👋! Ask me about your telecom data — I’ll write SQL, run it in BigQuery, and show results!")

prompt = st.text_area("💬 Your question (e.g., 'Show all active billing accounts with suspended products'): ")

# Show parsed mappings for transparency
with st.expander("🗺️ Preview Parsed Mappings"):
    st.subheader("Siebel Mappings (Detected)")
    st.text(siebel_mapping)
    st.subheader("Antillia Mappings (Detected)")
    st.text(antillia_mapping)

# ---------------- QUERY EXECUTION ----------------
if st.button("🚀 Run Query"):
    if not prompt.strip():
        st.warning("Please enter a question or query prompt!")
    else:
        try:
            with st.spinner("🧠 Generating SQL using Gemini..."):
                sql_query = vertex_agent.prompt_to_sql(prompt, siebel_mapping, antillia_mapping)
                st.session_state.sql_query = sql_query

            if "sample_dataset" in sql_query.lower():
                raise RuntimeError("Gemini returned a placeholder dataset. Check mapping context.")

            st.subheader("🪄 Generated SQL")
            st.code(sql_query, language="sql")

            # Extract table name
            match = re.search(r'`([\w\-]+\.[\w\-]+\.[\w\-_]+)`', sql_query)
            if match:
                st.session_state.table_name = match.group(1)
                st.info(f"📂 Target Table: `{st.session_state.table_name}`")

            with st.spinner("📡 Running SQL in BigQuery..."):
                df = bq_agent.execute(sql_query)
                st.session_state.df = df

            st.success(f"✅ Query executed successfully! {len(df)} rows returned.")
            st.dataframe(st.session_state.df)

            # CSV Download
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv_data,
                file_name="query_results.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")

# ---------------- FOLLOW-UP ACTIONS ----------------
if st.session_state.sql_query and st.session_state.df is not None:
    st.markdown("---")
    st.markdown("🤖 **What would you like to do next?**")

    next_action = st.radio(
        "Choose an action:",
        ["Nothing, thanks", "Filter this data", "Visualize something", "Summarize these results"],
        key="next_action"
    )

    df_full = st.session_state.df

    if next_action == "Filter this data":
        st.subheader("🔎 Filter Data")
        columns = df_full.columns.tolist()
        selected_col = st.selectbox("Select a column:", columns)
        unique_vals = df_full[selected_col].dropna().unique().tolist()

        if len(unique_vals) > 100:
            st.info("Too many unique values. Showing first 100.")
            unique_vals = unique_vals[:100]

        selected_val = st.selectbox("Select a value:", unique_vals)
        filtered_df = df_full[df_full[selected_col] == selected_val]
        st.dataframe(filtered_df)

        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Filtered Data",
            data=csv_data,
            file_name="filtered_results.csv",
            mime="text/csv"
        )

    elif next_action == "Visualize something":
        st.subheader("📊 Visualize Data")
        numeric_cols = df_full.select_dtypes(include="number").columns.tolist()
        if not numeric_cols:
            st.warning("No numeric columns found for visualization.")
        else:
            selected_col = st.selectbox("Select a numeric column to visualize:", numeric_cols)
            chart = alt.Chart(df_full).mark_bar().encode(
                x=alt.X(df_full.index, title="Row Index"),
                y=alt.Y(selected_col, title=selected_col)
            ).interactive()
            st.altair_chart(chart, use_container_width=True)

    elif next_action == "Summarize these results":
        st.subheader("🧠 Summary by Gemini")
        with st.spinner("✨ Generating summary..."):
            df_preview = df_full.head(20).to_string()
            summary_prompt = f"Summarize key insights from this telecom dataset:\n\n{df_preview}"
            summary = vertex_agent.summarize_text(summary_prompt)
        st.write(summary)
