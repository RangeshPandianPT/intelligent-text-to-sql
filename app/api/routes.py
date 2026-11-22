from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.pipeline.orchestrator import run_baseline_pipeline, run_phase3_pipeline, run_phase5_pipeline, run_phase7_pipeline, run_pipeline
from app.database.schema import get_database_schema
from app.database.safety import (
    safety_logger,
    validate_input_prompt_safety,
    validate_sql_safety,
    SQLSafetyError
)

router = APIRouter()

class QueryRequest(BaseModel):
    question: str
    enable_schema_linking: bool = True
    enable_generation_exploration: bool = True
    enable_refinement: bool = True
    enable_refinement_exploration: bool = True
    enable_target_checking: bool = True

@router.post("/query/baseline", tags=["Query"])
async def baseline_query(request: QueryRequest):
    """
    Runs the baseline Text-to-SQL pipeline for the given question.
    """
    try:
        result = run_baseline_pipeline(request.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query/phase3", tags=["Query"])
async def phase3_query(request: QueryRequest):
    """
    Runs the Phase 3 (Schema Linking) Text-to-SQL pipeline for the given question.
    """
    try:
        result = run_phase3_pipeline(request.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query/phase5", tags=["Query"])
async def phase5_query(request: QueryRequest):
    """
    Runs the Phase 5 (Two-Stage Exploration) Text-to-SQL pipeline for the given question.
    """
    try:
        result = run_phase5_pipeline(request.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/phase7", tags=["Query"])
async def phase7_query(request: QueryRequest):
    """
    Runs the Phase 7 (Refinement Engine) Text-to-SQL pipeline for the given question.
    Combines Schema Linking, Two-Stage Exploration, and iterative SQL refinement.
    """
    try:
        result = run_phase7_pipeline(request.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/query", tags=["Query"])
async def full_query(request: QueryRequest):
    """
    Runs the full SDE-SQL pipeline for the given question with optional ablation flags (Phase 9, 11 & 14).
    """
    try:
        result = run_pipeline(
            question=request.question,
            enable_schema_linking=request.enable_schema_linking,
            enable_generation_exploration=request.enable_generation_exploration,
            enable_refinement=request.enable_refinement,
            enable_refinement_exploration=request.enable_refinement_exploration,
            enable_target_checking=request.enable_target_checking,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/schema", tags=["Schema"])
async def get_schema():
    """
    Returns the full database schema (Phase 11).
    """
    try:
        return get_database_schema()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ──────────────────────────────────────────────────────────────────────
# Safe SDE Security & Audit Telemetry Endpoints
# ──────────────────────────────────────────────────────────────────────
@router.get("/api/safety/metrics", tags=["Safety"])
async def get_safety_metrics():
    """
    Returns real-time safety telemetry: total queries scanned, threats blocked, and threat breakdown.
    """
    return safety_logger.get_metrics()

@router.get("/api/safety/events", tags=["Safety"])
async def get_safety_events(limit: int = 15):
    """
    Returns recent security audit events and blocked attacks.
    """
    return safety_logger.get_recent_events(limit=limit)

class SafetyCheckRequest(BaseModel):
    text: str
    is_sql: bool = False

@router.post("/api/safety/check", tags=["Safety"])
async def check_safety(request: SafetyCheckRequest):
    """
    Directly tests a natural language question or SQL query against the Safe SDE security engine.
    """
    try:
        if request.is_sql:
            validate_sql_safety(request.text)
        else:
            validate_input_prompt_safety(request.text)
        return {"status": "PASSED", "message": "Query passed all security checks."}
    except SQLSafetyError as e:
        return {
            "status": "BLOCKED",
            "threat_type": getattr(e, "threat_type", "GENERIC_UNSAFE"),
            "error": str(e)
        }


