import json
from pydantic import ValidationError
from app.llm.client import LLMClient
from app.llm.prompts import (
    build_sql_generation_prompt,
    build_linked_sql_generation_prompt,
    build_explored_sql_generation_prompt,
    build_refinement_prompt,
)
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

    def generate_explored_sql(self, question: str, linked_schema: dict, successful_combinations: list, rejected_combinations: list) -> SQLGenerationResponse:
        """
        Generates SQL for a question using the Phase 5 approach (LinkedSchema + Exploration + Question -> SQL).
        """
        prompt = build_explored_sql_generation_prompt(
            question, 
            linked_schema.dict() if hasattr(linked_schema, "dict") else linked_schema, 
            successful_combinations, 
            rejected_combinations
        )
        
        response_text = self.llm.generate(prompt, require_json=True)
        
        try:
            data = json.loads(response_text)
            return SQLGenerationResponse(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Failed to parse LLM response into SQL: {e}. Raw response: {response_text}")

    def generate_refined_sql(
        self,
        question: str,
        linked_schema: dict,
        prior_attempts: list,
        probe_hints: list = None,
    ) -> SQLGenerationResponse:
        """
        Generates a corrected SQL query using the Phase 7 refinement approach.
        The LLM receives the full history of prior failed attempts together with
        any concrete database value hints from the exploration phase.
        """
        prompt = build_refinement_prompt(
            question=question,
            linked_schema=linked_schema if isinstance(linked_schema, dict) else linked_schema.dict(),
            prior_attempts=prior_attempts,
            probe_hints=probe_hints or [],
        )

        response_text = self.llm.generate(prompt, require_json=True)

        try:
            data = json.loads(response_text)
            return SQLGenerationResponse(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(
                f"Failed to parse LLM refinement response into SQL: {e}. "
                f"Raw response: {response_text}"
            )
