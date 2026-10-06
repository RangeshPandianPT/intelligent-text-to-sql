from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class RefinementAttempt(BaseModel):
    """
    Records the context and outcome of a single refinement attempt.
    """
    attempt_number: int = Field(..., description="1-indexed attempt number")
    sql: str = Field(..., description="The SQL that was tried in this attempt")
    status: str = Field(..., description="Execution status returned by the executor")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    row_count: int = Field(0, description="Number of rows returned (0 if error/empty)")


class RefinementResult(BaseModel):
    """
    The full output of the refinement engine after all attempts.
    """
    final_sql: str = Field(..., description="The SQL that produced the best result")
    final_status: str = Field(..., description="Execution status of the final SQL")
    final_rows: List[Dict[str, Any]] = Field(default_factory=list)
    final_columns: List[str] = Field(default_factory=list)
    final_row_count: int = Field(0)
    final_execution_time_ms: float = Field(0.0)
    total_attempts: int = Field(..., description="Total number of SQL attempts made")
    refinement_attempts: List[RefinementAttempt] = Field(
        default_factory=list,
        description="Log of every attempt before the final one"
    )
    error: Optional[str] = Field(None, description="Error on the final attempt, if any")
    refined: bool = Field(
        False,
        description="True if at least one refinement iteration was needed"
    )
