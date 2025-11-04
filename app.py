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
import pandas as pd

# ---------------- CONFIG ----------------
PROJECT_ID = "telecom-data-lake"
REGION = "europe-west1"
BUCKET_NAME = "stage_data1"
SIEBEL_FILE = "Mapping files/siebel_mapping.txt"
ANTILLIA_FILE = "Mapping files/antillia_mapping.txt"

# ---------------- LOAD MAPPINGS ----------------
st.sidebar.title("⚙️ Configuration")
st.sidebar.caption("Gemini-powered dynamic SQL generation using Siebel & Antillia metadata.")

siebel_raw = load_mapping(BUCKET_NAME, SIEBEL_FILE)
antillia_raw = load_mapping(BUCKET_NAME, ANTILLIA_FILE)

tables = extract_mapping_lines(siebel_raw + "\n" + antillia_raw)
joins = extract_join_relationships(siebel_raw + "\n" + antillia_raw)
column_context = extract_column_hints(siebel_raw + "\n" + antillia_raw)
alias_map = generate_aliases(tables)

vertex_agent = VertexAgent(PROJECT_ID, REGION, tables, tables, column_context, joins, alias_map)
bq_agent = BigQueryAgent(PROJECT_ID)

# ---------------- STREAMLIT STATE ----------------
if "df" not in st.session_state:
    st.session_state.df = None
if "last_sql" not in st.session_state:
    st.session_state.last_sql = None
if "conversation_mode" not in st.session_state:
    st.session_state.conversation_mode = False

# ---------------- MAIN UI ----------------
st.title("📊 Telecom Data Assistant (Dynamic Context)")
st.markdown("Ask me anything about your telecom data — I’ll write, run, and explain SQL for you!")

prompt = st.text_area("💬 Ask a question (e.g., 'Show all active billing products with account details'):")

# --- Buttons ---
col1, col2 = st.columns([1, 1])
run_btn = col1.button("🚀 Run Query")
follow_btn = col2.button("💬 Continue Conversation", disabled=st.session_state.df is None)

# ---------------- RUN QUERY ----------------
if run_btn:
    try:
        sql = vertex_agent.prompt_to_sql(prompt)
        st.session_state.last_sql = sql
        st.code(sql, language="sql")

        with st.spinner("📡 Running SQL in BigQuery..."):
            df = bq_agent.execute(sql)
            st.session_state.df = df

        st.success(f"✅ Query executed successfully! {len(df)} rows returned.")
        st.dataframe(df, use_container_width=True)

        # CSV Download
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name="query_results.csv",
            mime="text/csv",
        )

        st.session_state.conversation_mode = True

    except Exception as e:
        st.error(f"❌ Error: {e}")

# ---------------- FOLLOW-UP CONVERSATION ----------------
if follow_btn and st.session_state.df is not None:
    st.markdown("---")
    st.subheader("🧠 Follow-up Question Mode")
    st.info("You can ask me something related to your previous results!")

    follow_prompt = st.text_area("💬 Continue (e.g., 'show only active accounts' or 'top 5 by charge_amount'):")

    if st.button("▶️ Run Follow-up"):
        try:
            context = (
                f"Previous SQL:\n{st.session_state.last_sql}\n\n"
                f"Sample Data:\n{st.session_state.df.head(10).to_string(index=False)}"
            )
            full_prompt = f"{context}\n\nFollow-up Question:\n{follow_prompt}\n\nGenerate an updated SQL query."
            sql = vertex_agent.prompt_to_sql(full_prompt)
            st.session_state.last_sql = sql

            st.code(sql, language="sql")

            with st.spinner("📡 Running refined SQL in BigQuery..."):
                df = bq_agent.execute(sql)
                st.session_state.df = df

            st.success(f"✅ Follow-up executed successfully! {len(df)} rows returned.")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Updated Results",
                data=csv,
                file_name="followup_results.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")

# ---------------- DEBUG PANEL ----------------
with st.expander("🧩 Debug Info (for demo explanation)"):
    st.markdown("**Detected Tables:**")
    st.write(tables)
    st.markdown("**Extracted Joins:**")
    st.write(joins)
    st.markdown("**Generated Aliases:**")
    st.json(alias_map)
