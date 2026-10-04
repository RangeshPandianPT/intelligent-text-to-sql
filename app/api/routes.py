from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.pipeline.orchestrator import run_baseline_pipeline, run_phase3_pipeline, run_phase5_pipeline

router = APIRouter()

class QueryRequest(BaseModel):
    question: str

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
