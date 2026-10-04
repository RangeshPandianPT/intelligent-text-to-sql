import json
import logging
from typing import List, Dict, Any
from app.llm.client import OllamaClient
from app.exploration.schemas import Probe, ProbeResult

logger = logging.getLogger(__name__)

STAGE_A_PROMPT = """
You are an expert SQL database explorer. Your task is Stage A: Candidate Exploration.
Question: {question}

Linked Database Schema:
{schema}

Generate up to {max_probes} Base SQL Probes to determine candidates for:
1. Target columns (what the user is asking for).
2. Condition columns (columns used for filtering).
3. Condition values (possible values for filtering).

Do NOT generate the final SQL. Generate simple queries like `SELECT DISTINCT col FROM table LIMIT 50` or `SELECT col FROM table WHERE condition LIMIT 50`.
Always include a LIMIT clause (e.g., LIMIT 50) to prevent large result sets.

Return the result strictly as a JSON object with a 'probes' array. Each object must have 'purpose' and 'sql'.
"""

STAGE_B_PROMPT = """
You are an expert SQL database explorer. Your task is Stage B: Combination Exploration.
Question: {question}

Linked Database Schema:
{schema}

Stage A Exploration Results:
{stage_a_results}

Generate up to {max_probes} Condition SQL Probes to combine candidate conditions identified in Stage A.
If a combination returns no rows, we will mark it as unsuitable. Try combining filtering conditions to see if data exists.
Generate queries like `SELECT * FROM table WHERE condition1 AND condition2 LIMIT 1`.

Return the result strictly as a JSON object with a 'probes' array. Each object must have 'purpose' and 'sql'.
"""

PROBE_GENERATION_PROMPT = """
You are an expert SQL database explorer. Your task is to generate SQL probe queries to help understand the database schema and values before writing a final query.

Question: {question}

Database Schema:
{schema}

Generate up to {max_probes} exploratory SQL queries to:
1. Find candidate columns.
2. Find candidate values for filtering.
3. Check distinct values for relevant columns.
4. Verify relationships between tables.

Do NOT generate the final SQL query to answer the question. Only generate simple, fast exploratory queries.
Always include a LIMIT clause (e.g., LIMIT 50) to prevent large result sets.

Return the result strictly as a JSON object with a 'probes' array. Each object in the array must have a 'purpose' string and a 'sql' string.
Example:
{{
  "probes": [
    {{"purpose": "Check available departments", "sql": "SELECT DISTINCT department FROM students LIMIT 50;"}}
  ]
}}
"""

class ProbeGenerator:
    def __init__(self, llm_client: OllamaClient = None):
        self.llm_client = llm_client or OllamaClient()

    def generate_probes(self, question: str, linked_schema: Dict[str, Any], max_probes: int = 5) -> List[Probe]:
        schema_str = json.dumps(linked_schema, indent=2)
        prompt = PROBE_GENERATION_PROMPT.format(
            question=question, 
            schema=schema_str, 
            max_probes=max_probes
        )
        
        try:
            response_text = self.llm_client.generate(prompt, require_json=True)
            
            # Ollama might return Markdown wrapped JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].strip()
                
            data = json.loads(response_text)
            
            probes = []
            for p in data.get("probes", [])[:max_probes]:
                probes.append(Probe(purpose=p.get("purpose", ""), sql=p.get("sql", "")))
            return probes
        except Exception as e:
            logger.error(f"Failed to generate probes: {e}")
            return []

    def generate_stage_a_probes(self, question: str, linked_schema: Dict[str, Any], max_probes: int = 5) -> List[Probe]:
        schema_str = json.dumps(linked_schema, indent=2)
        prompt = STAGE_A_PROMPT.format(question=question, schema=schema_str, max_probes=max_probes)
        return self._generate(prompt, max_probes)

    def generate_stage_b_probes(self, question: str, linked_schema: Dict[str, Any], stage_a_results: List[ProbeResult], max_probes: int = 5) -> List[Probe]:
        schema_str = json.dumps(linked_schema, indent=2)
        
        # Format stage_a_results securely
        results_str = ""
        for r in stage_a_results:
            results_str += f"Probe: {r.probe.sql}\nStatus: {r.status}\nRow Count: {r.row_count}\n"
            if r.rows:
                results_str += f"Sample rows: {r.rows[:2]}\n"
            results_str += "\n"
            
        prompt = STAGE_B_PROMPT.format(question=question, schema=schema_str, stage_a_results=results_str, max_probes=max_probes)
        return self._generate(prompt, max_probes)

    def _generate(self, prompt: str, max_probes: int) -> List[Probe]:
        try:
            response_text = self.llm_client.generate(prompt, require_json=True)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].strip()
                
            data = json.loads(response_text)
            probes = []
            for p in data.get("probes", [])[:max_probes]:
                probes.append(Probe(purpose=p.get("purpose", ""), sql=p.get("sql", "")))
            return probes
        except Exception as e:
            logger.error(f"Failed to generate probes: {e}")
            return []
