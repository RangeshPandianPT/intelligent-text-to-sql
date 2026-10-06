# SDE-SQL

**Self-Driven Database Exploration for Accurate Text-to-SQL**

This project is a production-quality prototype inspired by the paper:
*SDE-SQL: Enhancing Text-to-SQL Generation in Large Language Models via Self-Driven Exploration with SQL Probes*

## Overview
Instead of the traditional Text-to-SQL pipeline (User Question → LLM → SQL), this project implements a dynamic, self-driven exploration mechanism where the LLM interacts with the database (via SQL probes) before generating the final SQL query, and iteratively refines queries if they produce empty or error results.

## Setup Instructions

### 1. Create a Virtual Environment
```bash
python -m venv venv
```
Activate it:
- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Copy the `.env.example` to `.env` and adjust the settings as needed (no secrets are stored in version control):
```bash
cp .env.example .env
```

## Running the Application

### Backend (FastAPI)
```bash
uvicorn app.main:app --reload
```
Access the health check at: `http://localhost:8000/health`

### Frontend (Streamlit)
```bash
streamlit run frontend/streamlit_app.py
```

## Project Status

- [x] **Phase 0: Project Foundation**
- [x] **Phase 1: Database Foundation** 
- [x] **Phase 2: Baseline Text-to-SQL**
- [x] **Phase 3: Schema Linking**
- [x] **Phase 4: SQL Probe Engine**
- [x] **Phase 5: Two-Stage Generation Exploration**
- [x] **Phase 6: SQL Validation and Execution**
- [x] **Phase 7: Refinement Engine**

