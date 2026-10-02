import json
import logging
from typing import List
from app.llm.client import LLMClient

logger = logging.getLogger(__name__)

class EntityExtractor:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        
    def extract(self, question: str) -> List[str]:
        """
        Extracts entities (tables, columns, values, conditions) from the user question.
        Returns a list of extracted entities as strings.
        """
        prompt = f"""Extract all important entities, values, conditions, and table/column references from the following question.
Return ONLY a valid JSON object in this format:
{{
  "entities": ["entity1", "entity2"]
}}

Question: "{question}"
"""
        logger.info(f"Extracting entities for question: {question}")
        response_text = self.llm_client.generate(prompt, require_json=True)
        try:
            data = json.loads(response_text)
            entities = data.get("entities", [])
            logger.info(f"Extracted entities: {entities}")
            return entities
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse entities JSON: {e}")
            return []
