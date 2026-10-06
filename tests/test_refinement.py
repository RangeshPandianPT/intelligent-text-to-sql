"""
Tests for Phase 7: Refinement Engine
"""
import pytest
from unittest.mock import MagicMock, patch

from app.refinement.engine import RefinementEngine
from app.refinement.schemas import RefinementResult, RefinementAttempt
from app.llm.schemas import SQLGenerationResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_generator(sql: str, confidence: float = 0.9) -> MagicMock:
    """Returns a mock SQLGenerator whose generate_refined_sql returns `sql`."""
    gen = MagicMock()
    gen.generate_refined_sql.return_value = SQLGenerationResponse(sql=sql, confidence=confidence)
    return gen


# ---------------------------------------------------------------------------
# Unit tests — RefinementEngine with mocked executor
# ---------------------------------------------------------------------------

class TestRefinementEngine:
    """Tests that exercise the refinement loop in isolation."""

    def test_no_refinement_needed_when_initial_sql_succeeds(self):
        """If the first SQL returns rows, no LLM call should be made."""
        generator = _make_generator("SELECT 1 AS n")

        with patch(
            "app.refinement.engine.execute_query",
            return_value={"sql": "SELECT 1 AS n", "status": "SUCCESS_WITH_ROWS",
                          "rows": [{"n": 1}], "columns": ["n"],
                          "row_count": 1, "execution_time_ms": 0.5, "error": None}
        ):
            engine = RefinementEngine(sql_generator=generator, max_attempts=3)
            result = engine.refine(
                initial_sql="SELECT 1 AS n",
                question="What is 1?",
                linked_schema={"tables": []},
            )

        assert result.final_status == "SUCCESS_WITH_ROWS"
        assert result.final_row_count == 1
        assert result.refined is False
        assert result.total_attempts == 1
        generator.generate_refined_sql.assert_not_called()

    def test_refinement_triggers_on_empty_result(self):
        """An empty initial result should trigger one LLM refinement call."""
        generator = _make_generator("SELECT 2 AS n")

        call_count = 0

        def fake_execute(sql, params=()):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"sql": sql, "status": "SUCCESS_EMPTY", "rows": [],
                        "columns": [], "row_count": 0,
                        "execution_time_ms": 1.0, "error": None}
            return {"sql": sql, "status": "SUCCESS_WITH_ROWS", "rows": [{"n": 2}],
                    "columns": ["n"], "row_count": 1,
                    "execution_time_ms": 0.8, "error": None}

        with patch("app.refinement.engine.execute_query", side_effect=fake_execute):
            engine = RefinementEngine(sql_generator=generator, max_attempts=3)
            result = engine.refine(
                initial_sql="SELECT 2 AS n",
                question="What is 2?",
                linked_schema={"tables": []},
            )

        assert result.refined is True
        assert result.total_attempts == 2
        assert result.final_status == "SUCCESS_WITH_ROWS"
        generator.generate_refined_sql.assert_called_once()

    def test_refinement_triggers_on_syntax_error(self):
        """A SYNTAX_ERROR should trigger a refinement attempt."""
        generator = _make_generator("SELECT * FROM students LIMIT 1")

        call_count = 0

        def fake_execute(sql, params=()):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"sql": sql, "status": "SYNTAX_ERROR", "rows": [],
                        "columns": [], "row_count": 0,
                        "execution_time_ms": 0.2, "error": "syntax error"}
            return {"sql": sql, "status": "SUCCESS_WITH_ROWS",
                    "rows": [{"id": 1}], "columns": ["id"],
                    "row_count": 1, "execution_time_ms": 1.0, "error": None}

        with patch("app.refinement.engine.execute_query", side_effect=fake_execute):
            engine = RefinementEngine(sql_generator=generator, max_attempts=3)
            result = engine.refine(
                initial_sql="SELEC * FROM students",
                question="Show all students",
                linked_schema={"tables": [{"name": "students", "columns": [{"name": "id", "type": "INTEGER"}]}]},
            )

        assert result.refined is True
        assert result.total_attempts == 2
        assert result.final_status == "SUCCESS_WITH_ROWS"

    def test_budget_exhaustion_returns_last_result(self):
        """When all attempts fail, the last result is returned."""
        generator = _make_generator("SELECT bad FROM nowhere")

        with patch(
            "app.refinement.engine.execute_query",
            return_value={"sql": "SELECT bad FROM nowhere", "status": "SCHEMA_ERROR",
                          "rows": [], "columns": [], "row_count": 0,
                          "execution_time_ms": 0.3, "error": "no such table"}
        ):
            engine = RefinementEngine(sql_generator=generator, max_attempts=2)
            result = engine.refine(
                initial_sql="SELECT bad FROM nowhere",
                question="something",
                linked_schema={"tables": []},
            )

        # All 2 attempts used, last status returned
        assert result.total_attempts == 2
        assert result.final_status == "SCHEMA_ERROR"
        assert result.refined is True  # more than 1 attempt was made
        # LLM called exactly (max_attempts - 1) times = 1 time
        assert generator.generate_refined_sql.call_count == 1

    def test_refinement_attempt_log_is_complete(self):
        """Every attempt should be logged in refinement_attempts."""
        generator = _make_generator("SELECT 1")

        responses = [
            {"sql": "SELECT 1", "status": "SUCCESS_EMPTY", "rows": [], "columns": [],
             "row_count": 0, "execution_time_ms": 0.1, "error": None},
            {"sql": "SELECT 1", "status": "SUCCESS_EMPTY", "rows": [], "columns": [],
             "row_count": 0, "execution_time_ms": 0.1, "error": None},
            {"sql": "SELECT 1", "status": "SUCCESS_WITH_ROWS", "rows": [{"x": 1}],
             "columns": ["x"], "row_count": 1, "execution_time_ms": 0.1, "error": None},
        ]

        with patch("app.refinement.engine.execute_query", side_effect=responses):
            engine = RefinementEngine(sql_generator=generator, max_attempts=3)
            result = engine.refine(
                initial_sql="SELECT 1",
                question="q",
                linked_schema={"tables": []},
            )

        assert result.total_attempts == 3
        assert len(result.refinement_attempts) == 3
        assert result.refinement_attempts[0].status == "SUCCESS_EMPTY"
        assert result.refinement_attempts[2].status == "SUCCESS_WITH_ROWS"

    def test_llm_failure_aborts_gracefully(self):
        """If the LLM throws on refinement, the engine should abort cleanly."""
        generator = MagicMock()
        generator.generate_refined_sql.side_effect = RuntimeError("LLM offline")

        with patch(
            "app.refinement.engine.execute_query",
            return_value={"sql": "SELECT 1", "status": "SUCCESS_EMPTY",
                          "rows": [], "columns": [], "row_count": 0,
                          "execution_time_ms": 0.1, "error": None}
        ):
            engine = RefinementEngine(sql_generator=generator, max_attempts=3)
            result = engine.refine(
                initial_sql="SELECT 1",
                question="q",
                linked_schema={"tables": []},
            )

        # Should not raise; the engine records the LLM error and returns
        assert "REFINEMENT_LLM_ERROR" in result.final_status or result.final_status == "REFINEMENT_LLM_ERROR"
        assert "LLM offline" in (result.error or "")


# ---------------------------------------------------------------------------
# Integration test — prompt builder
# ---------------------------------------------------------------------------

class TestRefinementPrompt:
    """Lightweight checks on the refinement prompt content."""

    def test_prompt_contains_prior_attempt_info(self):
        from app.llm.prompts import build_refinement_prompt

        prior = [
            {"attempt": 1, "sql": "SELECT * FROM foo", "status": "SCHEMA_ERROR",
             "error": "no such table: foo"},
        ]
        prompt = build_refinement_prompt(
            question="How many students?",
            linked_schema={"tables": [{"name": "students", "columns": []}]},
            prior_attempts=prior,
            probe_hints=[],
        )

        assert "no such table: foo" in prompt
        assert "How many students?" in prompt
        assert "FAILED ATTEMPTS" in prompt

    def test_prompt_contains_probe_hints_when_provided(self):
        from app.llm.prompts import build_refinement_prompt

        # Simulate a probe hint as a plain dict (as serialised for the pipeline)
        hint = {
            "probe": {"sql": "SELECT name FROM students LIMIT 1", "purpose": "test"},
            "rows": [{"name": "Alice"}],
            "row_count": 1,
        }
        prompt = build_refinement_prompt(
            question="List all students",
            linked_schema={"tables": []},
            prior_attempts=[{"attempt": 1, "sql": "SELECT ...", "status": "SUCCESS_EMPTY", "error": None}],
            probe_hints=[hint],
        )

        assert "DATABASE VALUE HINTS" in prompt
        assert "Alice" in prompt
