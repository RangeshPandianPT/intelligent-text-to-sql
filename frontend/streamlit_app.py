import streamlit as st
import requests
import os

# Read configuration securely from env or defaults
API_HOST = os.getenv("API_HOST", "http://localhost:8000")

st.set_page_config(
    page_title="SDE-SQL Demo",
    page_icon="🔍",
    layout="wide",
)

st.title("SDE-SQL: Self-Driven Database Exploration")
st.markdown("### Accurate Text-to-SQL via LLM Database Exploration")

# Sidebar
st.sidebar.header("System Settings")

# Check backend health
try:
    health_res = requests.get(f"{API_HOST}/health", timeout=2)
    if health_res.status_code == 200:
        health_data = health_res.json()
        st.sidebar.success("Backend: Online ✅")
        st.sidebar.json(health_data)
    else:
        st.sidebar.warning(f"Backend: Returned status {health_res.status_code} ⚠️")
except requests.exceptions.RequestException:
    st.sidebar.error("Backend: Offline ❌")
    st.sidebar.info("Ensure the FastAPI backend is running on port 8000.")

st.sidebar.markdown("---")
st.sidebar.markdown("**About**")
st.sidebar.markdown("This is a prototype implementation inspired by the SDE-SQL research paper.")

st.markdown("---")
st.write("Welcome to the SDE-SQL frontend.")
st.info("Currently supporting Baseline (Phase 2), Schema Linking (Phase 3), and Two-Stage Exploration (Phase 5).")

question = st.text_input("Ask a question about the college database (e.g., 'Which students are from CSE?'):")
col1, col2, col3 = st.columns(3)
run_baseline = col1.button("Run Baseline Pipeline")
run_phase3 = col2.button("Run Phase 3 Pipeline")
run_phase5 = col3.button("Run Phase 5 Pipeline")

if run_baseline:
    if not question:
        st.warning("Please enter a question.")
    else:
        with st.spinner("Generating and executing SQL via LLM..."):
            try:
                res = requests.post(f"{API_HOST}/query/baseline", json={"question": question}, timeout=60)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") in ("success_with_rows", "success_truncated", "success_empty"):
                        st.success(f"Execution Status: {data.get('status')}")
                        st.code(data.get("sql", ""), language="sql")
                        if "rows" in data and data["rows"]:
                            st.table(data["rows"])
                        else:
                            st.write("0 rows returned.")
                    else:
                        st.error(f"Pipeline Error: {data.get('status')}")
                        st.code(data.get("sql", ""), language="sql")
                        st.write(data.get("error", ""))
                        st.json(data)
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Request failed: {e}")

if run_phase3:
    if not question:
        st.warning("Please enter a question.")
    else:
        with st.spinner("Linking Schema and Generating SQL via LLM..."):
            try:
                res = requests.post(f"{API_HOST}/query/phase3", json={"question": question}, timeout=120)
                if res.status_code == 200:
                    data = res.json()
                    
                    if "linked_schema" in data:
                        with st.expander("View Linked Schema"):
                            st.json(data["linked_schema"])
                            
                    if data.get("status") in ("success_with_rows", "success_truncated", "success_empty"):
                        st.success(f"Execution Status: {data.get('status')}")
                        st.code(data.get("sql", ""), language="sql")
                        if "rows" in data and data["rows"]:
                            st.table(data["rows"])
                        else:
                            st.write("0 rows returned.")
                    else:
                        st.error(f"Pipeline Error: {data.get('status')}")
                        st.code(data.get("sql", ""), language="sql")
                        st.write(data.get("error", ""))
                        st.json(data)
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Request failed: {e}")

if run_phase5:
    if not question:
        st.warning("Please enter a question.")
    else:
        with st.spinner("Running Phase 5: Linking Schema, Exploring DB, and Generating SQL..."):
            try:
                res = requests.post(f"{API_HOST}/query/phase5", json={"question": question}, timeout=180)
                if res.status_code == 200:
                    data = res.json()
                    
                    if "linked_schema" in data:
                        with st.expander("View Linked Schema"):
                            st.json(data["linked_schema"])
                            
                    if "exploration" in data:
                        exp = data["exploration"]
                        with st.expander("View Exploration Probes & Results"):
                            st.markdown("**Stage A: Base Probes**")
                            st.json(exp.get("stage_a_results", []))
                            st.markdown("**Stage B: Condition Probes**")
                            st.json(exp.get("stage_b_results", []))
                            st.markdown("**Rejected Combinations**")
                            st.json(exp.get("rejected_combinations", []))
                            
                    if data.get("status") in ("success_with_rows", "success_truncated", "success_empty"):
                        st.success(f"Execution Status: {data.get('status')}")
                        st.code(data.get("sql", ""), language="sql")
                        if "rows" in data and data["rows"]:
                            st.table(data["rows"])
                        else:
                            st.write("0 rows returned.")
                    else:
                        st.error(f"Pipeline Error: {data.get('status')}")
                        st.code(data.get("sql", ""), language="sql")
                        st.write(data.get("error", ""))
                        st.json(data)
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Request failed: {e}")
