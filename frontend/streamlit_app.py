"""
SDE-SQL — Professional Streamlit Frontend
==========================================
Light-themed, card-based layout with a clean pipeline visualization.
"""

import streamlit as st
import requests
import os
import pandas as pd
import time

# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "http://localhost:8000")

st.set_page_config(
    page_title="SDE-SQL - Intelligent Text-to-SQL",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────
# Custom CSS — scoped carefully to avoid breaking Streamlit icons
# ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Hero banner ── */
.hero-box {
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #60a5fa 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    color: white;
}
.hero-box h1 {
    font-size: 2rem;
    font-weight: 700;
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.5px;
    color: white;
}
.hero-box p {
    font-size: 1rem;
    opacity: 0.9;
    margin: 0;
    color: white;
}

/* ── Metric cards ── */
.metrics-row {
    display: flex;
    gap: 1rem;
    margin: 1rem 0 1.5rem;
    flex-wrap: wrap;
}
.m-card {
    flex: 1;
    min-width: 110px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
}
.m-card .m-val {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1e293b;
}
.m-card .m-lbl {
    font-size: 0.72rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 2px;
}

/* ── Pipeline steps bar ── */
.p-bar {
    display: flex;
    gap: 6px;
    margin: 0.75rem 0 1.25rem;
    flex-wrap: wrap;
}
.p-step {
    flex: 1;
    min-width: 90px;
    text-align: center;
    padding: 8px 6px;
    border-radius: 8px;
    font-size: 0.72rem;
    font-weight: 600;
}
.p-on {
    background: #dbeafe;
    color: #1e40af;
    border: 1px solid #93c5fd;
}
.p-ok {
    background: #dcfce7;
    color: #166534;
    border: 1px solid #86efac;
}
.p-off {
    background: #f1f5f9;
    color: #94a3b8;
    border: 1px solid #e2e8f0;
}

/* ── Status badges ── */
.s-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.8rem;
    font-weight: 600;
}
.s-ok { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
.s-warn { background: #fef9c3; color: #854d0e; border: 1px solid #fde047; }
.s-err { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }

/* ── SQL display block ── */
.sql-box {
    background: #1e293b;
    color: #e2e8f0;
    padding: 1rem 1.25rem;
    border-radius: 10px;
    font-family: monospace;
    font-size: 0.85rem;
    line-height: 1.6;
    overflow-x: auto;
    margin: 0.5rem 0;
    border-left: 4px solid #2563eb;
    white-space: pre-wrap;
    word-break: break-word;
}

/* ── Section label ── */
.sec-label {
    font-size: 0.95rem;
    font-weight: 600;
    color: #334155;
    margin: 1rem 0 0.5rem;
    padding-bottom: 0.25rem;
    border-bottom: 2px solid #e2e8f0;
}

/* ── Sidebar backend badge ── */
.sb-online { color: #166534; font-weight: 600; }
.sb-offline { color: #991b1b; font-weight: 600; }

/* ── Footer ── */
.ft-bar {
    text-align: center;
    color: #94a3b8;
    font-size: 0.75rem;
    padding: 1.5rem 0 0.5rem;
    border-top: 1px solid #e2e8f0;
    margin-top: 2rem;
}

/* ── Button styling ── */
div.stButton > button[kind="primary"],
div.stButton > button {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.55rem 1.8rem !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
}
div.stButton > button:hover {
    background: linear-gradient(135deg, #1d4ed8, #1e40af) !important;
}
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# Hero Header
# ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-box">
    <h1>SDE-SQL</h1>
    <p>Self-Driven Database Exploration for Accurate Text-to-SQL &middot; Powered by LLM + SQL Probes</p>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("System Status")

    backend_online = False
    try:
        health_res = requests.get(f"{API_HOST}/health", timeout=2)
        if health_res.status_code == 200:
            health_data = health_res.json()
            backend_online = True
            st.success("Backend: Online")
            with st.expander("Health Details"):
                st.json(health_data)
        else:
            st.warning(f"Backend: Status {health_res.status_code}")
    except requests.exceptions.RequestException:
        st.error("Backend: Offline")
        st.info("Start the FastAPI server: `uvicorn app.main:app`")

    st.divider()
    st.subheader("Pipeline Configuration")

    enable_schema_linking = st.toggle("Schema Linking", value=True)
    enable_generation_exploration = st.toggle("Generation Exploration", value=True)
    enable_refinement = st.toggle("Refinement Engine", value=True)
    enable_refinement_exploration = st.toggle("Refinement Exploration", value=True)
    enable_target_checking = st.toggle("Target Checking", value=True)

    st.divider()
    st.subheader("Example Queries")

    examples = [
        "Which students are in the CSE department?",
        "Find students with CGPA above 8.5",
        "List all courses in the ECE department",
        "Show the average CGPA per department",
        "Which students are enrolled in Database Management Systems?",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex}", use_container_width=True):
            st.session_state["query_input"] = ex

    st.divider()
    st.caption(
        "Implementation inspired by the SDE-SQL research paper. "
        "Built with FastAPI, Streamlit, Ollama."
    )


# ──────────────────────────────────────────────────────────────────────
# Query Input
# ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-label">Ask a Question</div>', unsafe_allow_html=True)

query_default = st.session_state.get("query_input", "")
question = st.text_input(
    "Natural language question:",
    value=query_default,
    placeholder="e.g. Find students from computer science with CGPA above 8.5",
    label_visibility="collapsed",
)

run_clicked = st.button("Generate SQL")


# ──────────────────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────────────────
def status_badge(status: str) -> str:
    s = status.upper()
    if "SUCCESS_WITH_ROWS" in s:
        return f'<span class="s-badge s-ok">{status}</span>'
    elif "EMPTY" in s:
        return f'<span class="s-badge s-warn">{status}</span>'
    else:
        return f'<span class="s-badge s-err">{status}</span>'


def pipeline_bar(steps):
    html = '<div class="p-bar">'
    for s in steps:
        cls = "p-step " + s["cls"]
        html += f'<div class="{cls}">{s["label"]}</div>'
    html += "</div>"
    return html


# ──────────────────────────────────────────────────────────────────────
# Results
# ──────────────────────────────────────────────────────────────────────
if run_clicked:
    if not question.strip():
        st.warning("Please enter a question first.")
    elif not backend_online:
        st.error("Backend is offline. Please start the FastAPI server.")
    else:
        # Pipeline step indicators (active state)
        steps = [
            {"label": "Schema Linking", "cls": "p-on" if enable_schema_linking else "p-off"},
            {"label": "Exploration", "cls": "p-on" if enable_generation_exploration else "p-off"},
            {"label": "SQL Generation", "cls": "p-on"},
            {"label": "Refinement", "cls": "p-on" if enable_refinement else "p-off"},
            {"label": "Target Check", "cls": "p-on" if enable_target_checking else "p-off"},
        ]
        step_placeholder = st.empty()
        step_placeholder.markdown(pipeline_bar(steps), unsafe_allow_html=True)

        start_time = time.time()
        progress = st.progress(0, text="Starting pipeline...")

        try:
            progress.progress(10, text="Sending query to backend...")

            payload = {
                "question": question,
                "enable_schema_linking": enable_schema_linking,
                "enable_generation_exploration": enable_generation_exploration,
                "enable_refinement": enable_refinement,
                "enable_refinement_exploration": enable_refinement_exploration,
                "enable_target_checking": enable_target_checking,
            }
            res = requests.post(f"{API_HOST}/api/query", json=payload, timeout=180)
            elapsed = time.time() - start_time

            progress.progress(100, text="Done!")
            time.sleep(0.3)
            progress.empty()

            if res.status_code != 200:
                st.error(f"API Error {res.status_code}: {res.text}")
            else:
                data = res.json()
                trace = data.get("trace", {})
                status = data.get("status", "Unknown")
                row_count = data.get("row_count", 0)
                exec_time = data.get("execution_time_ms", 0)
                sql = data.get("sql", "")
                probes = trace.get("probes", [])
                refinements = trace.get("refinement", [])

                # Update pipeline bar to "done"
                for s in steps:
                    if s["cls"] == "p-on":
                        s["cls"] = "p-ok"
                step_placeholder.markdown(pipeline_bar(steps), unsafe_allow_html=True)

                # ── Metrics ──
                st.markdown(f"""
                <div class="metrics-row">
                    <div class="m-card">
                        <div class="m-val">{row_count}</div>
                        <div class="m-lbl">Rows</div>
                    </div>
                    <div class="m-card">
                        <div class="m-val">{exec_time:.1f} ms</div>
                        <div class="m-lbl">DB Exec Time</div>
                    </div>
                    <div class="m-card">
                        <div class="m-val">{elapsed:.1f} s</div>
                        <div class="m-lbl">Total Time</div>
                    </div>
                    <div class="m-card">
                        <div class="m-val">{len(probes)}</div>
                        <div class="m-lbl">Probes</div>
                    </div>
                    <div class="m-card">
                        <div class="m-val">{len(refinements)}</div>
                        <div class="m-lbl">Refinements</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # ── Generated SQL ──
                st.markdown('<div class="sec-label">Generated SQL</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="sql-box">{sql}</div>', unsafe_allow_html=True)
                st.markdown(status_badge(status), unsafe_allow_html=True)

                # ── Results Table ──
                if data.get("rows"):
                    st.markdown('<div class="sec-label">Query Results</div>', unsafe_allow_html=True)
                    df = pd.DataFrame(data["rows"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                elif status == "SUCCESS_EMPTY":
                    st.info("The query executed successfully but returned no rows.")

                # ── Schema Linking ──
                linked_schema = trace.get("schema_linking", {})
                if linked_schema and linked_schema.get("tables"):
                    with st.expander("Schema Linking Details"):
                        for t in linked_schema.get("tables", []):
                            tname = t.get("name", "")
                            sel = t.get("selected_columns", [])
                            if sel:
                                col_names = [f"`{c.get('name', '')}` ({c.get('type', '')})" for c in sel]
                                st.markdown(f"**{tname}**: {', '.join(col_names)}")
                                for c in sel:
                                    vals = c.get("example_values", [])
                                    if vals:
                                        st.caption(f"  {c['name']} samples: {vals}")

                # ── Probes ──
                if probes:
                    with st.expander(f"Exploration Probes ({len(probes)})"):
                        for idx, p in enumerate(probes):
                            purpose = p.get("purpose", "Probe") if isinstance(p, dict) else "Probe"
                            probe_data = p.get("probe", p) if isinstance(p, dict) else p
                            probe_sql = probe_data.get("sql", "") if isinstance(probe_data, dict) else ""
                            p_rows = p.get("rows", []) if isinstance(p, dict) else []
                            p_status = p.get("status", "") if isinstance(p, dict) else ""
                            p_count = p.get("row_count", 0) if isinstance(p, dict) else 0

                            st.markdown(f"**Probe {idx + 1}:** {purpose}")
                            if probe_sql:
                                st.code(probe_sql, language="sql")
                            if p_rows:
                                st.dataframe(
                                    pd.DataFrame(p_rows),
                                    use_container_width=True,
                                    hide_index=True,
                                )
                            elif p_status:
                                st.caption(f"Status: {p_status} | Rows: {p_count}")
                            st.divider()

                # ── Refinement ──
                if refinements:
                    with st.expander(f"Refinement History ({len(refinements)})"):
                        for idx, r in enumerate(refinements):
                            r_sql = r.get("sql", "")
                            r_status = r.get("status", "Unknown")
                            r_error = r.get("error", "")
                            r_count = r.get("row_count", 0)

                            st.markdown(f"**Attempt {idx + 1}**")
                            if r_sql:
                                st.code(r_sql, language="sql")
                            st.markdown(
                                f"{status_badge(r_status)} &nbsp; Rows: {r_count}",
                                unsafe_allow_html=True,
                            )
                            if r_error:
                                st.caption(f"Error: {r_error}")
                            st.divider()

        except requests.exceptions.Timeout:
            progress.empty()
            st.error("Request timed out. The LLM may be loading — try again in a moment.")
        except requests.exceptions.RequestException as e:
            progress.empty()
            st.error(f"Connection error: {e}")


# ──────────────────────────────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="ft-bar">
    SDE-SQL &middot; Implementation inspired by
    <em>SDE-SQL: Enhancing Text-to-SQL via Self-Driven Exploration with SQL Probes</em><br>
    Built with FastAPI &middot; Streamlit &middot; Ollama &middot; SQLite
</div>
""", unsafe_allow_html=True)
