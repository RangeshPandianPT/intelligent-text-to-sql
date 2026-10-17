"""
Unit tests for Phase 14 Ablation Study configuration flags.
"""
import pytest
import json
from app.pipeline.orchestrator import run_pipeline
from app.llm.client import LLMClient

class MultiStepMockLLM(LLMClient):
    """
    Mock LLM that returns appropriate structured JSON for each pipeline phase:
    schema linking, probe generation, SQL generation, refinement, and target checking.
    """
    def __init__(self, initial_sql: str = "SELECT * FROM students WHERE department = 'CSE'"):
        self.initial_sql = initial_sql
        self.refinement_called = False
        self.target_checking_called = False
        self.probes_called = False
        self.schema_linking_called = False

    def generate(self, prompt: str, require_json: bool = False) -> str:
        prompt_lower = prompt.lower()

        # Schema Linking / Entity Extraction prompt
        if "extract all important entities" in prompt_lower or "entities" in prompt_lower and "format:" in prompt_lower:
            self.schema_linking_called = True
            return json.dumps({
                "entities": ["students", "department", "CSE"]
            })

        # Exploration Probes prompt (Stage A or Stage B generation)
        if "stage a: candidate exploration" in prompt_lower or "stage b: combination exploration" in prompt_lower or "base sql probes" in prompt_lower:
            self.probes_called = True
            return json.dumps({
                "probes": [
                    {
                        "purpose": "Check departments",
                        "sql": "SELECT DISTINCT department FROM students LIMIT 5;"
                    }
                ]
            })

        # Refinement prompt
        if "fixing a previously generated sql query" in prompt_lower or "failed attempts" in prompt_lower:
            self.refinement_called = True
            return json.dumps({
                "sql": "SELECT name FROM students WHERE department = 'CSE';",
                "confidence": 0.95
            })

        # Target checking prompt
        if "target checking" in prompt_lower:
            self.target_checking_called = True
            return json.dumps({
                "sql": "SELECT name FROM students WHERE department = 'CSE';",
                "confidence": 0.98
            })

        # Default: SQL Generation (Baseline, Linked, Explored)
        return json.dumps({
            "sql": self.initial_sql,
            "confidence": 0.90
        })


def test_ablation_baseline():
    """Baseline: all ablation flags disabled (pure LLM -> SQL)."""
    mock_llm = MultiStepMockLLM("SELECT * FROM students WHERE department = 'CSE';")
    result = run_pipeline(
        question="Which students are from CSE?",
        llm_client=mock_llm,
        enable_schema_linking=False,
        enable_generation_exploration=False,
        enable_refinement=False,
        enable_refinement_exploration=False,
        enable_target_checking=False,
    )

    assert result["status"] == "SUCCESS_WITH_ROWS"
    assert result["row_count"] > 0
    assert result["trace"]["schema_linking"] is None
    assert result["trace"]["probes"] == []
    assert result["trace"]["refinement"] == []
    assert not mock_llm.schema_linking_called
    assert not mock_llm.probes_called
    assert not mock_llm.refinement_called
    assert not mock_llm.target_checking_called


def test_ablation_with_schema_linking_only():
    """Experiment 1: Baseline + Schema Linking."""
    mock_llm = MultiStepMockLLM("SELECT * FROM students WHERE department = 'CSE';")
    result = run_pipeline(
        question="Which students are from CSE?",
        llm_client=mock_llm,
        enable_schema_linking=True,
        enable_generation_exploration=False,
        enable_refinement=False,
        enable_refinement_exploration=False,
        enable_target_checking=False,
    )

    assert result["status"] == "SUCCESS_WITH_ROWS"
    assert result["trace"]["schema_linking"] is not None
    assert result["trace"]["probes"] == []
    assert result["trace"]["refinement"] == []
    assert mock_llm.schema_linking_called
    assert not mock_llm.probes_called


def test_ablation_refinement_flag_triggers_when_empty():
    """Experiment 3: Refinement enabled, triggers on empty result."""
    # Initial SQL returns 0 rows, triggering refinement
    mock_llm = MultiStepMockLLM("SELECT * FROM students WHERE department = 'NONEXISTENT_DEPT';")
    result = run_pipeline(
        question="Which students are from CSE?",
        llm_client=mock_llm,
        enable_schema_linking=True,
        enable_generation_exploration=False,
        enable_refinement=True,
        enable_refinement_exploration=False,
        enable_target_checking=False,
    )

    assert mock_llm.refinement_called
    assert len(result["trace"]["refinement"]) > 0
    assert result["status"] == "SUCCESS_WITH_ROWS"


def test_ablation_refinement_disabled_leaves_empty():
    """When refinement is disabled, empty query is returned as SUCCESS_EMPTY without refinement."""
    mock_llm = MultiStepMockLLM("SELECT * FROM students WHERE department = 'NONEXISTENT_DEPT';")
    result = run_pipeline(
        question="Which students are from CSE?",
        llm_client=mock_llm,
        enable_schema_linking=True,
        enable_generation_exploration=False,
        enable_refinement=False,
        enable_refinement_exploration=False,
        enable_target_checking=False,
    )

    assert not mock_llm.refinement_called
    assert result["status"] == "SUCCESS_EMPTY"
    assert result["row_count"] == 0
    assert result["trace"]["refinement"] == []


def test_ablation_full_pipeline():
    """Full pipeline: all components enabled."""
    mock_llm = MultiStepMockLLM("SELECT * FROM students WHERE department = 'CSE';")
    result = run_pipeline(
        question="Which students are from CSE?",
        llm_client=mock_llm,
        enable_schema_linking=True,
        enable_generation_exploration=True,
        enable_refinement=True,
        enable_refinement_exploration=True,
        enable_target_checking=True,
    )

    assert mock_llm.target_checking_called


def test_run_ablation_study_execution(tmp_path):
    """Verify that run_ablation_study runs across configurations and saves JSON summary."""
    from run_ablation import run_ablation_study
    test_output = tmp_path / "test_ablation_out.json"
    mock_llm = MultiStepMockLLM("SELECT * FROM students WHERE department = 'CSE';")

    results = run_ablation_study(
        data_path="data/evaluation.json",
        output_path=str(test_output),
        limit=2,
        llm_client=mock_llm
    )

    assert "configurations" in results
    assert "table" in results
    assert len(results["table"]) == 6
    assert test_output.exists()
