import streamlit as st
import requests
import os
import pandas as pd

# Read configuration securely from env or defaults
API_HOST = os.getenv("API_HOST", "http://localhost:8000")

st.set_page_config(
    page_title="SDE-SQL Demo",
    page_icon="🔍",
    layout="wide",
)

st.title("SDE-SQL")
st.markdown("### Self-Driven Database Exploration for Text-to-SQL")

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

question = st.text_input("Ask a question about the database (e.g., 'Find students from the computer science department with CGPA above 8.5.'):")

if st.button("Generate SQL"):
    if not question:
        st.warning("Please enter a question.")
    else:
        with st.spinner("Running Full SDE-SQL Pipeline..."):
            try:
                res = requests.post(f"{API_HOST}/api/query", json={"question": question}, timeout=180)
                if res.status_code == 200:
                    data = res.json()
                    trace = data.get("trace", {})
                    
                    st.header("Section 1: Schema")
                    linked_schema = trace.get("schema_linking", {})
                    if linked_schema:
                        st.json(linked_schema)
                    else:
                        st.write("No schema linking data found.")
                        
                    st.header("Section 2: Exploration")
                    probes = trace.get("probes", [])
                    if probes:
                        for idx, p in enumerate(probes):
                            with st.expander(f"Probe {idx+1}: {p.get('purpose', 'Exploration')}"):
                                st.code(p.get("sql", ""), language="sql")
                                st.write("Execution Success:", p.get("execution_success", True))
                                if p.get("rows"):
                                    st.dataframe(pd.DataFrame(p["rows"]))
                                else:
                                    st.write(p.get("error", "0 rows returned."))
                    else:
                        st.write("No probes were executed.")

                    st.header("Section 3: Generated SQL")
                    st.code(data.get("sql", ""), language="sql")
                    status = data.get("status", "Unknown")
                    if status in ("SUCCESS_WITH_ROWS", "SUCCESS_EMPTY"):
                        st.success(f"Status: {status}")
                    else:
                        st.error(f"Status: {status}")
                        
                    refinements = trace.get("refinement", [])
                    if refinements:
                        st.header("Section 4: Refinement")
                        for idx, r in enumerate(refinements):
                            with st.expander(f"Refinement Iteration {idx+1}"):
                                st.write("**Diagnostics:**")
                                for d in r.get("diagnostic_results", []):
                                    st.code(d.get("sql", ""), language="sql")
                                    st.write(f"Row Count: {d.get('row_count', 0)}")
                                st.write("**Refined SQL:**")
                                st.code(r.get("refined_sql", ""), language="sql")
                                st.write(f"Execution Status: {r.get('execution_status', 'Unknown')}")
                                
                    st.header("Section 5: Final Results")
                    st.write(f"**Row Count:** {data.get('row_count', 0)}")
                    st.write(f"**Execution Time:** {data.get('execution_time_ms', 0)} ms")
                    
                    if data.get("rows"):
                        st.dataframe(pd.DataFrame(data["rows"]))
                    else:
                        st.write("No rows to display.")

                else:
                    st.error(f"API Error {res.status_code}: {res.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Request failed: {e}")
