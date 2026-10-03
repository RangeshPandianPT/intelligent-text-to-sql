from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Probe(BaseModel):
    purpose: str = Field(..., description="The purpose of this probe")
    sql: str = Field(..., description="The SQL query to execute")

class ProbeList(BaseModel):
    probes: List[Probe]

class ProbeResult(BaseModel):
    probe: Probe
    status: str
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    error: Optional[str] = None
