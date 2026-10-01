from pydantic import BaseModel, Field

class SQLGenerationResponse(BaseModel):
    sql: str = Field(description="The generated SQLite-compatible SQL query")
    confidence: float = Field(default=0.0, description="Confidence score from 0.0 to 1.0")
