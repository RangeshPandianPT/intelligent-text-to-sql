import json
from pydantic import ValidationError
from app.llm.client import LLMClient
from app.llm.prompts import build_sql_generation_prompt, build_linked_sql_generation_prompt
from app.llm.schemas import SQLGenerationResponse
from app.database.schema import get_database_schema

class SQLGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        
    def generate_baseline_sql(self, question: str) -> SQLGenerationResponse:
        """
        Generates SQL for a question using the baseline approach (Schema + Question -> SQL).
        """
        schema = get_database_schema()
        prompt = build_sql_generation_prompt(question, schema)
        
        response_text = self.llm.generate(prompt, require_json=True)
        
        try:
            # Parse the JSON response
            data = json.loads(response_text)
            return SQLGenerationResponse(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Failed to parse LLM response into SQL: {e}. Raw response: {response_text}")

    def generate_linked_sql(self, question: str, linked_schema) -> SQLGenerationResponse:
        """
        Generates SQL for a question using the Phase 3 approach (LinkedSchema + Question -> SQL).
        """
        prompt = build_linked_sql_generation_prompt(question, linked_schema.dict())
        
        response_text = self.llm.generate(prompt, require_json=True)
        
        try:
            data = json.loads(response_text)
            return SQLGenerationResponse(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Failed to parse LLM response into SQL: {e}. Raw response: {response_text}")
