import pytest
import json
from app.pipeline.orchestrator import run_baseline_pipeline
from app.llm.client import LLMClient

class MockLLMClient(LLMClient):
    def __init__(self, response_sql: str):
        self.response_sql = response_sql
        
    def generate(self, prompt: str, require_json: bool = False) -> str:
        response_data = {
            "sql": self.response_sql,
            "confidence": 0.95
        }
        return json.dumps(response_data)

def test_baseline_pipeline_success():
    client = MockLLMClient("SELECT * FROM students WHERE department = 'CSE'")
    result = run_baseline_pipeline("Which students are from CSE?", llm_client=client)
    
    assert result["status"] == "success_with_rows"
    assert result["sql"] == "SELECT * FROM students WHERE department = 'CSE'"
    assert result["row_count"] > 0

def test_baseline_pipeline_safety_rejection():
    client = MockLLMClient("DROP TABLE students")
    result = run_baseline_pipeline("Delete all students", llm_client=client)
    
    assert result["status"] == "safety_rejection"
    assert "Only SELECT queries are permitted" in result["error"]

def test_baseline_pipeline_syntax_error():
    client = MockLLMClient("SELECT * FROM")
    result = run_baseline_pipeline("Get everything", llm_client=client)
    
    # Since safety validation parses the SQL, it catches syntax errors
    assert result["status"] == "safety_rejection"
    assert "SQL syntax error" in result["error"]
