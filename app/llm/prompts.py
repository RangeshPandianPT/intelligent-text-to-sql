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
