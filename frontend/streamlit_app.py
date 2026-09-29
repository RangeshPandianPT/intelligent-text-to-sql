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
st.write("Welcome to the SDE-SQL frontend. The system is currently in Phase 0 (Foundation) setup.")
st.info("Full UI capabilities will be integrated in Phase 10 as per the implementation plan.")
