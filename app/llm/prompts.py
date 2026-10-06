import json

def build_sql_generation_prompt(question: str, schema: dict) -> str:
    """
    Builds the prompt for the baseline Text-to-SQL generation.
    """
    schema_str = json.dumps(schema, indent=2)
    
    return f"""You are an expert SQLite SQL developer. 
Generate a SQLite-compatible SQL query to answer the user's question based strictly on the provided database schema.

RULES:
1. Use ONLY the provided schema. Do not invent tables or columns.
2. Return a valid JSON object matching this schema exactly:
{{
  "sql": "SELECT ...",
  "confidence": 0.9
}}
3. Do not include markdown formatting like ```json or anything else. Just the raw JSON object.
4. Only generate a SELECT query. Do not attempt to modify the database.

SCHEMA:
{schema_str}

QUESTION:
{question}
"""

def build_linked_sql_generation_prompt(question: str, linked_schema: dict) -> str:
    """
    Builds the prompt for Text-to-SQL generation using a LinkedSchema.
    """
    schema_str = json.dumps(linked_schema, indent=2)
    
    return f"""You are an expert SQLite SQL developer. 
Generate a SQLite-compatible SQL query to answer the user's question based strictly on the provided linked database schema.
The schema includes selected columns (which are likely relevant based on entity matching) and unselected columns. You may use any columns needed, but prioritize selected ones.

RULES:
1. Use ONLY the provided schema tables and columns. Do not invent tables or columns.
2. Return a valid JSON object matching this schema exactly:
{{
  "sql": "SELECT ...",
  "confidence": 0.9
}}
3. Do not include markdown formatting like ```json or anything else. Just the raw JSON object.
4. Only generate a SELECT query. Do not attempt to modify the database.

LINKED SCHEMA:
{schema_str}

QUESTION:
{question}
"""

def build_explored_sql_generation_prompt(question: str, linked_schema: dict, successful_combinations: list, rejected_combinations: list) -> str:
    """
    Builds the prompt for Phase 5 Text-to-SQL generation using LinkedSchema and exploration results.
    """
    schema_str = json.dumps(linked_schema, indent=2)
    
    successful_str = ""
    for r in successful_combinations:
        successful_str += f"Probe: {r.probe.sql}\nStatus: {r.status}\nRow Count: {r.row_count}\n"
        if r.rows:
            successful_str += f"Sample rows: {r.rows[:2]}\n"
        successful_str += "\n"
        
    rejected_str = ""
    for r in rejected_combinations:
        rejected_str += f"Probe: {r.probe.sql}\nStatus: {r.status}\nRow Count: {r.row_count} (Rejected due to empty/error)\n\n"
    
    return f"""You are an expert SQLite SQL developer. 
Generate a SQLite-compatible SQL query to answer the user's question based strictly on the provided linked database schema AND the results of exploratory database probes.
The schema includes selected columns (which are likely relevant based on entity matching) and unselected columns.
The exploratory probes show actual data in the database. Use this data to construct the correct WHERE clauses and JOINs. Pay special attention to rejected combinations, which yield no rows.

RULES:
1. Use ONLY the provided schema tables and columns. Do not invent tables or columns.
2. Return a valid JSON object matching this schema exactly:
{{
  "sql": "SELECT ...",
  "confidence": 0.9
}}
3. Do not include markdown formatting like ```json or anything else. Just the raw JSON object.
4. Only generate a SELECT query. Do not attempt to modify the database.

LINKED SCHEMA:
{schema_str}

SUCCESSFUL EXPLORATION RESULTS (Use these values in your query):
{successful_str}

REJECTED COMBINATIONS (Do NOT use these conditions, they result in empty data):
{rejected_str}

QUESTION:
{question}
"""


def build_refinement_prompt(
    question: str,
    linked_schema: dict,
    prior_attempts: list,
    probe_hints: list,
) -> str:
    """
    Builds the prompt for Phase 7 iterative SQL refinement.

    Parameters
    ----------
    question        : The original user question.
    linked_schema   : The LinkedSchema dict.
    prior_attempts  : List of dicts with keys: attempt, sql, status, error.
    probe_hints     : List of ProbeResult-like objects (or dicts) whose rows
                      provide concrete DB values the LLM can use.
    """
    schema_str = json.dumps(linked_schema, indent=2)

    # Format prior attempts as a numbered list
    attempts_str = ""
    for a in prior_attempts:
        attempts_str += f"Attempt #{a['attempt']}:\n"
        attempts_str += f"  SQL    : {a['sql']}\n"
        attempts_str += f"  Status : {a['status']}\n"
        if a.get("error"):
            attempts_str += f"  Error  : {a['error']}\n"
        else:
            attempts_str += f"  Result : Query returned 0 rows (empty result — incorrect WHERE/JOIN conditions)\n"
        attempts_str += "\n"

    # Format probe value hints
    hints_str = ""
    if probe_hints:
        for hint in probe_hints:
            # Support both ProbeResult objects and plain dicts
            if hasattr(hint, "probe"):
                sql = hint.probe.sql
                rows = hint.rows[:2]
            else:
                sql = hint.get("probe", {}).get("sql", "")
                rows = hint.get("rows", [])[:2]
            hints_str += f"Probe: {sql}\n"
            if rows:
                hints_str += f"Sample rows: {rows}\n"
            hints_str += "\n"

    probe_section = (
        f"DATABASE VALUE HINTS (real data from exploration probes — use exact values in WHERE clauses):\n{hints_str}"
        if hints_str
        else ""
    )

    return f"""You are an expert SQLite SQL developer tasked with FIXING a previously generated SQL query.
The prior SQL attempts below all failed — either with a syntax/schema error, or by returning zero rows.
Carefully analyze each failure, understand why it went wrong, and produce a corrected SQL query.

RULES:
1. Use ONLY the tables and columns present in the LINKED SCHEMA below.
2. Return a valid JSON object matching this schema exactly:
{{
  "sql": "SELECT ...",
  "confidence": 0.9
}}
3. Do not include markdown formatting like ```json or anything else. Just the raw JSON object.
4. Only generate a SELECT query. Do not attempt to modify the database.
5. If previous errors mention unknown table/column names, double-check the schema carefully.
6. If previous results were empty, reconsider your JOIN conditions, WHERE filters, and value literals.

LINKED SCHEMA:
{schema_str}

{probe_section}
FAILED ATTEMPTS (analyse these to avoid repeating the same mistakes):
{attempts_str}
QUESTION:
{question}
"""
