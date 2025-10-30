import streamlit as st
from utils import load_mapping, parse_allowed_tables
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

st.set_page_config(page_title="Telecom Data Assistant", layout="wide")
st.title("📊 Telecom Data Assistant")
st.caption("Ask in natural language → Gemini generates SQL → BigQuery runs it → Results here.")

# ---------------- LOAD MAPPINGS ----------------
with st.spinner("📥 Loading mapping files from GCS..."):
    siebel_raw = load_mapping(BUCKET_NAME, SIEBEL_FILE)
    antillia_raw = load_mapping(BUCKET_NAME, ANTILLIA_FILE)

allowed_tables = parse_allowed_tables(siebel_raw) | parse_allowed_tables(antillia_raw)
if not allowed_tables:
    st.error("No fully-qualified table names found in mapping files. Please include lines like:\n"
             "`telecom-data-lake.o_siebel.siebel_accounts`")
    st.stop()

# Show what we parsed (optional)
with st.expander("🔎 Detected Tables from Mapping Files"):
    for t in sorted(allowed_tables):
        st.code(t)

# ---------------- INIT CLIENTS ----------------
vertex_agent = VertexAgent(PROJECT_ID, REGION, allowed_tables=sorted(allowed_tables))
bq_agent = BigQueryAgent(PROJECT_ID)

# ---------------- STATE ----------------
if "df" not in st.session_state: st.session_state.df = None
if "sql" not in st.session_state: st.session_state.sql = None

# ---------------- MAIN UI ----------------
prompt = st.text_area("💬 Your question:", height=120,
                      placeholder="e.g., Show active Siebel accounts with related Antillia billing products and amounts.")

if st.button("🚀 Generate & Run"):
    if not prompt.strip():
        st.warning("Please enter a question.")
        st.stop()

    try:
        with st.spinner("🧠 Asking Gemini to generate BigQuery SQL..."):
            sql = vertex_agent.prompt_to_sql(prompt)
        st.subheader("🪄 Generated SQL")
        st.code(sql, language="sql")

        # Validate SQL uses only allowed tables and is read-only
        bad_tables = vertex_agent.find_disallowed_tables(sql)
        if bad_tables:
            st.error("SQL references tables not present in mapping files:\n" + "\n".join(bad_tables))
            st.stop()

        if not vertex_agent.is_select_only(sql):
            st.error("Only SELECT queries are allowed.")
            st.stop()

        with st.spinner("📡 Executing SQL in BigQuery..."):
            df = bq_agent.execute(sql)

        st.session_state.sql = sql
        st.session_state.df = df

        st.success(f"✅ Query executed. {len(df):,} rows.")
        st.dataframe(df)

        # Download
        st.download_button(
            "📥 Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="query_results.csv",
            mime="text/csv"
        )

        # Simple viz
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            st.subheader("📈 Quick Chart")
            col = st.selectbox("Numeric column", numeric_cols)
            st.altair_chart(
                alt.Chart(df.reset_index()).mark_bar().encode(
                    x=alt.X("index:Q", title="Row"),
                    y=alt.Y(f"{col}:Q", title=col)
                ).interactive(),
                use_container_width=True
            )

    except Exception as e:
        st.error(f"❌ Error: {e}")

# Follow-ups
if st.session_state.df is not None:
    st.markdown("---")
    st.subheader("🤖 What next?")
    action = st.radio("Choose:", ["Nothing", "Filter", "Summarize"], horizontal=True)

    if action == "Filter":
        df = st.session_state.df
        col = st.selectbox("Column to filter", df.columns.tolist())
        vals = df[col].dropna().unique().tolist()
        if len(vals) > 100:
            st.info("Too many unique values, showing first 100.")
            vals = vals[:100]
        val = st.selectbox("Value", vals)
        st.dataframe(df[df[col] == val])

    elif action == "Summarize":
        df = st.session_state.df
        preview = df.head(30).to_csv(index=False)
        with st.spinner("Summarizing…"):
            summary = vertex_agent.summarize_text(
                f"Summarize key insights from this dataset (CSV sample):\n{preview}"
            )
        st.write(summary)
