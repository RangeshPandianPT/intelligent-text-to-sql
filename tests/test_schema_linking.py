import pytest
import json
from unittest.mock import MagicMock
from app.schema_linking.entity_extractor import EntityExtractor
from app.schema_linking.linker import SchemaLinker
from app.schema_linking.schemas import LinkedSchema

class MockLLMClient:
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0
        
    def generate(self, prompt: str, require_json: bool = False) -> str:
        response = self.responses[self.call_count]
        self.call_count += 1
        return response

def test_entity_extractor():
    mock_llm = MockLLMClient([
        json.dumps({"entities": ["students", "CSE", "8.5"]})
    ])
    extractor = EntityExtractor(mock_llm)
    entities = extractor.extract("Find students from CSE with CGPA above 8.5")
    assert entities == ["students", "CSE", "8.5"]
    
def test_schema_linker():
    # 1st call: Extract entities
    # 2nd call: Schema Linking
    mock_responses = [
        json.dumps({"entities": ["CSE"]}),
        json.dumps({
            "tables": [
                {
                    "name": "students",
                    "selected_columns": [
                        {
                            "name": "department",
                            "type": "TEXT",
                            "description": "Department of the student",
                            "example_values": ["CSE"]
                        }
                    ],
                    "unselected_columns": []
                }
            ]
        })
    ]
    
    mock_llm = MockLLMClient(mock_responses)
    linker = SchemaLinker(mock_llm)
    
    # We might need to mock execute_query or assume the database is seeded.
    # If the database is seeded with 'CSE', _search_candidate_values will find it.
    
    linked_schema = linker.link("Which students are from CSE?")
    
    assert isinstance(linked_schema, LinkedSchema)
    assert len(linked_schema.tables) == 1
    assert linked_schema.tables[0].name == "students"
    assert len(linked_schema.tables[0].selected_columns) == 1
    assert linked_schema.tables[0].selected_columns[0].name == "department"
