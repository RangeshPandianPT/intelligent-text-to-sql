from pydantic import BaseModel, Field
from typing import List, Dict

class ExtractedEntities(BaseModel):
    entities: List[str] = Field(description="List of entities extracted from the question")
    
class LinkedColumn(BaseModel):
    name: str = Field(description="Column name")
    type: str = Field(description="Column type")
    description: str = Field(default="", description="Description of the column")
    example_values: List[str] = Field(default_factory=list, description="Example values relevant to the question")

class LinkedTable(BaseModel):
    name: str = Field(description="Table name")
    selected_columns: List[LinkedColumn] = Field(default_factory=list, description="Columns explicitly selected for linking")
    unselected_columns: List[Dict[str, str]] = Field(default_factory=list, description="Columns not explicitly selected (name and type)")

class LinkedSchema(BaseModel):
    tables: List[LinkedTable] = Field(default_factory=list, description="Linked tables based on the question")
