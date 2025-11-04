import streamlit as st
from utils import (
    load_mapping,
    extract_mapping_lines,
    extract_column_hints,
    extract_join_relationships,
    generate_aliases,
)
from vertex_client import VertexAgent
from bigquery_client import BigQueryAgent
import pandas as pd

# ---------------- CONFIG ----------------
PROJECT_ID = "telecom-data-lake"
REGION = "europe-west1"
BUCKET_NAME = "stage_data1"
SIEBEL_FILE = "Mapping files/siebel_mapping.txt"
ANTILLIA_FILE = "Mapping files/antillia_mapping.txt"

st.set_page_config(page_title="📊 Telecom Data Assistant", layout="wide")

# ---------------- SIDEBAR CONFIG ----------------
st.sidebar.title("⚙️ Configuration")
st.sidebar.caption("Gemini-powered dynamic SQL generation using Siebel & Antillia metadata.")

# ---------------- LOAD MAPPINGS ----------------
siebel_raw = load_mapping(BUCKET_NAME, SIEBEL_FILE)
antillia_raw = load_mapping(BUCKET_NAME, ANTILLIA_FILE)

tables = extract_mapping_lines(siebel_raw + "\n" + antillia_raw)
joins = extract_join_relationships(siebel_raw + "\n" + antillia_raw)
column_context = extract_column_hints(siebel_raw + "\n" + antillia_raw)
alias_map = generate_aliases(tables)

# ---------------- INIT AGENTS ----------------
# VertexAgent here takes full context (lists/strings) so it can embed it in prompts.
vertex_agent = VertexAgent(
    PROJECT_ID, REGION,
    siebel_mapping=tables,       # using combined tables for both for now
    antillia_mapping=tables,
    column_context=column_context,
    joins=joins,
    alias_map=alias_map
)
bq_agent = BigQueryAgent(PROJECT_ID)

# ---------------- STREAMLIT STATE ----------------
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()
if "last_sql" not in st.session_state:
    st.session_state.last_sql = None
if "conversation_mode" not in st.session_state:
    st.session_state.conversation_mode = False

# ---------------- HEADER ----------------
st.title("📊 Telecom Data Assistant (Dynamic Context)")
st.markdown("Ask me anything about your telecom data — I’ll write, run, and explain SQL for you!")

# ---------------- MAIN INPUT ----------------
prompt = st.text_area(
    "💬 Ask a question (e.g., 'Show all active billing products with account details'):",
    key="main_prompt_box"
)

# --- Buttons ---
col1, col2 = st.columns([1, 1])
run_btn = col1.button("🚀 Run Query", key="run_query_btn")
follow_btn = col2.button(
    "💬 Continue Conversation",
    key="continue_convo_btn",
    disabled=st.session_state.df.empty
)

# ---------------- RUN INITIAL QUERY ----------------
if run_btn:
    try:
        # The VertexAgent already holds mapping context; we pass the user prompt directly.
        sql = vertex_agent.prompt_to_sql(prompt)
        st.session_state.last_sql = sql

        st.code(sql, language="sql", wrap_lines=True)

        with st.spinner("📡 Running SQL in BigQuery..."):
            df = bq_agent.execute(sql)
            st.session_state.df = df

        st.success(f"✅ Query executed successfully! {len(df)} rows returned.")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name="query_results.csv",
            mime="text/csv",
            key="download_initial"
        )

        # Persist conversation mode so the follow-up panel stays open across reruns
        st.session_state.conversation_mode = True

    except Exception as e:
        st.error(f"❌ Error: {e}")

# ---------------- FOLLOW-UP CONVERSATION ----------------
# Enable mode if user clicked "Continue Conversation"
if follow_btn:
    st.session_state.conversation_mode = True

if st.session_state.conversation_mode and not st.session_state.df.empty:
    st.markdown("---")
    st.subheader("🧠 Follow-up Question Mode")
    st.info("You can ask me something related to your previous results!")

    follow_prompt = st.text_area(
        "💬 Continue (e.g., 'show only active accounts' or 'top 5 by charge_amount'):",
        key="follow_prompt_box"
    )

    if st.button("▶️ Run Follow-up", key="follow_run_btn"):
        try:
            context = (
                f"Previous SQL:\n{st.session_state.last_sql}\n\n"
                f"Sample Data (first 10 rows):\n{st.session_state.df.head(10).to_string(index=False)}"
            )
            full_prompt = (
                f"{context}\n\nFollow-up Question:\n{follow_prompt}\n\n"
                "Generate an updated BigQuery Standard SQL query. Output SQL only."
            )

            sql = vertex_agent.prompt_to_sql(full_prompt)
            st.session_state.last_sql = sql

            st.code(sql, language="sql", wrap_lines=True)

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
                key="download_followup"
            )

        except Exception as e:
            st.error(f"❌ Error: {e}")

    # Optional: end conversation / start new query
    if st.button("🔁 New Query", key="new_query_btn"):
        st.session_state.conversation_mode = False
        st.session_state.df = pd.DataFrame()
        st.session_state.last_sql = None
        st.rerun()

# ---------------- DEBUG PANEL ----------------
with st.expander("🧩 Debug Info (for demo explanation)"):
    st.markdown("**Detected Tables:**")
    st.write(tables)
    st.markdown("**Extracted Joins:**")
    st.write(joins)
    st.markdown("**Generated Aliases:**")
    st.json(alias_map)
