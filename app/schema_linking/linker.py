import json
import logging
from typing import List, Dict, Any
from app.database.schema import get_database_schema
from app.database.executor import execute_query
from app.schema_linking.entity_extractor import EntityExtractor
from app.schema_linking.schemas import LinkedSchema, LinkedTable, LinkedColumn
from app.llm.client import LLMClient

logger = logging.getLogger(__name__)

class SchemaLinker:
    def __init__(self, llm_client: LLMClient):
        self.extractor = EntityExtractor(llm_client)
        self.llm_client = llm_client
        
    def _search_candidate_values(self, entity: str) -> List[str]:
        """
        Searches the database for candidate values matching the entity.
        Returns a list of matching string values.
        """
        schema = get_database_schema()
        candidates = []
        
        # Simple exact/fuzzy matching using LIKE in the database across all text columns
        # In a real system, this would use a more sophisticated search index
        for table in schema.get("tables", []):
            table_name = table["name"]
            for col in table["columns"]:
                if "TEXT" in col["type"].upper() or "VARCHAR" in col["type"].upper():
                    col_name = col["name"]
                    sql = f"SELECT DISTINCT {col_name} FROM {table_name} WHERE {col_name} LIKE ? LIMIT 5"
                    # Add wildcards for partial matching
                    params = (f"%{entity}%",)
                    
                    try:
                        result = execute_query(sql, params)
                        if result["status"] in ("success_with_rows", "success_truncated"):
                            for row in result["rows"]:
                                val = row.get(col_name)
                                if val and str(val) not in candidates:
                                    candidates.append(str(val))
                    except Exception as e:
                        logger.error(f"Error searching candidate values in {table_name}.{col_name}: {e}")
                        
        return candidates

    def link(self, question: str) -> LinkedSchema:
        """
        Performs schema linking based on the user question.
        Returns the linked schema.
        """
        logger.info("Starting schema linking process.")
        schema = get_database_schema()
        entities = self.extractor.extract(question)
        
        # Candidate value retrieval
        candidate_values = {}
        for entity in entities:
            matches = self._search_candidate_values(entity)
            if matches:
                candidate_values[entity] = matches
                
        # Ask LLM to do soft schema linking based on schema, entities, and candidate values
        schema_json = json.dumps(schema, indent=2)
        candidates_json = json.dumps(candidate_values, indent=2)
        
        prompt = f"""You are a database schema linker. Given the database schema, a user question, extracted entities, and candidate values found in the database, perform soft schema linking.

Question: {question}
Entities: {json.dumps(entities)}
Candidate Values Found: {candidates_json}

Schema:
{schema_json}

Select ONLY the tables and columns that are relevant for answering the user's question. 
Do not omit any unselected columns; instead list them under 'unselected_columns'.
For selected columns provide: name, type, description (brief), and example_values (from Candidate Values Found or inferred).
For unselected columns retain: name, type.

Return ONLY a valid JSON object representing the linked schema.
Format:
{{
  "tables": [
    {{
      "name": "table_name",
      "selected_columns": [
        {{
          "name": "col_name",
          "type": "col_type",
          "description": "...",
          "example_values": ["..."]
        }}
      ],
      "unselected_columns": [
        {{
          "name": "col_name",
          "type": "col_type"
        }}
      ]
    }}
  ]
}}
"""
        logger.info("Generating linked schema via LLM.")
        response_text = self.llm_client.generate(prompt, require_json=True)
        try:
            data = json.loads(response_text)
            linked_schema = LinkedSchema(**data)
            logger.info("Successfully generated linked schema.")
            return linked_schema
        except Exception as e:
            logger.error(f"Failed to parse or validate linked schema: {e}")
            # Fallback to returning all tables with all columns as unselected if parsing fails
            linked_tables = []
            for t in schema.get("tables", []):
                linked_tables.append(LinkedTable(
                    name=t["name"],
                    selected_columns=[],
                    unselected_columns=[{"name": c["name"], "type": c["type"]} for c in t["columns"]]
                ))
            return LinkedSchema(tables=linked_tables)
