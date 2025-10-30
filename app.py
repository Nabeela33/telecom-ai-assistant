import streamlit as st
import re
import altair as alt
import pandas as pd
from utils import load_mapping, extract_mapping_lines, extract_column_hints
from vertex_client import VertexAgent
from bigquery_client import BigQueryAgent

# ---------------- CONFIG ----------------
PROJECT_ID = "telecom-data-lake"
REGION = "europe-west1"   # ✅ Gemini available here
BUCKET_NAME = "stage_data1"
SIEBEL_FILE = "Mapping files/siebel_mapping.txt"
ANTILLIA_FILE = "Mapping files/antillia_mapping.txt"

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Configuration")
st.sidebar.info("Mappings guide SQL generation across systems.")
st.sidebar.caption("Powered by Gemini 1.5 Flash + BigQuery")

# ---------------- LOAD MAPPINGS ----------------
with st.spinner("📥 Loading mapping files from GCS..."):
    siebel_raw = load_mapping(BUCKET_NAME, SIEBEL_FILE)
    antillia_raw = load_mapping(BUCKET_NAME, ANTILLIA_FILE)

siebel_mapping = extract_mapping_lines(siebel_raw)
antillia_mapping = extract_mapping_lines(antillia_raw)
column_context = extract_column_hints(siebel_raw + "\n" + antillia_raw)

# ---------------- INIT ----------------
vertex_agent = VertexAgent(PROJECT_ID, REGION, siebel_mapping, antillia_mapping, column_context)
bq_agent = BigQueryAgent(PROJECT_ID)

# ---------------- STREAMLIT STATE ----------------
if "df" not in st.session_state:
    st.session_state.df = None
if "sql_query" not in st.session_state:
    st.session_state.sql_query = None
if "table_name" not in st.session_state:
    st.session_state.table_name = None

# ---------------- MAIN UI ----------------
st.title("📊 Telecom Data Assistant")
st.markdown("Ask questions in plain English — I’ll generate SQL, run it on BigQuery, and show results!")

prompt = st.text_area("💬 Ask about your telecom data:")

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
                sql_query = vertex_agent.prompt_to_sql(prompt)
                st.session_state.sql_query = sql_query

            st.subheader("🪄 Generated SQL")
            st.code(sql_query, language="sql")

            # Extract table name for future context
            match = re.search(r'`([\w\-]+\.[\w\-]+\.[\w\-_]+)`', sql_query)
            if match:
                st.session_state.table_name = match.group(1)
                st.info(f"📂 Target Table: `{st.session_state.table_name}`")

            with st.spinner("📡 Executing SQL in BigQuery..."):
                df = bq_agent.execute(sql_query)
                st.session_state.df = df

            st.success(f"✅ Query executed successfully! {len(df)} rows returned.")
            st.dataframe(st.session_state.df)

            # CSV download
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

    table_name = st.session_state.table_name

    if next_action == "Filter this data":
        df_full = st.session_state.df
        st.subheader(f"🔎 Filter Data from `{table_name}`")

        columns = df_full.columns.tolist()
        selected_col = st.selectbox("Select a column to filter:", columns)
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
        df_full = st.session_state.df
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
            df_preview = st.session_state.df.head(20).to_string()
            summary_prompt = f"Summarize key insights from this dataset:\n\n{df_preview}"
            summary = vertex_agent.summarize_text(summary_prompt)
        st.write(summary)
