"""
Tests for Phase 8: Target Checking
"""
import pytest
from unittest.mock import MagicMock, patch

from app.refinement.target_checker import TargetChecker
from app.llm.schemas import SQLGenerationResponse


def _make_generator(sql: str, confidence: float = 0.9) -> MagicMock:
    """Returns a mock SQLGenerator whose generate_target_checked_sql returns `sql`."""
    gen = MagicMock()
    gen.generate_target_checked_sql.return_value = SQLGenerationResponse(sql=sql, confidence=confidence)
    return gen


class TestTargetChecker:
    def test_target_checking_no_change(self):
        """If target checking makes no changes, return original result with target_checked=False."""
        original_sql = "SELECT name FROM students"
        generator = _make_generator(original_sql)

        with patch(
            "app.refinement.target_checker.execute_query",
            return_value={"sql": original_sql, "status": "SUCCESS_WITH_ROWS",
                          "rows": [{"name": "Alice"}], "columns": ["name"],
                          "row_count": 1, "error": None}
        ):
            checker = TargetChecker(sql_generator=generator)
            result = checker.check_and_refine_target("Who are the students?", original_sql)

        assert result["target_checked"] is False
        assert result["sql"] == original_sql
        assert result["columns"] == ["name"]

    def test_target_checking_success(self):
        """If target checking changes the SQL successfully, return the refined result."""
        original_sql = "SELECT name, department, cgpa FROM students WHERE department='CSE'"
        refined_sql = "SELECT name FROM students WHERE department='CSE'"
        generator = _make_generator(refined_sql)

        call_count = 0

        def fake_execute(sql, params=()):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"sql": sql, "status": "SUCCESS_WITH_ROWS",
                        "rows": [{"name": "Alice", "department": "CSE", "cgpa": 9.0}], 
                        "columns": ["name", "department", "cgpa"],
                        "row_count": 1, "error": None}
            return {"sql": sql, "status": "SUCCESS_WITH_ROWS", 
                    "rows": [{"name": "Alice"}], 
                    "columns": ["name"], 
                    "row_count": 1, "error": None}

        with patch("app.refinement.target_checker.execute_query", side_effect=fake_execute):
            checker = TargetChecker(sql_generator=generator)
            result = checker.check_and_refine_target("Give me the names of CSE students.", original_sql)

        assert result["target_checked"] is True
        assert result["sql"] == refined_sql
        assert result["original_sql"] == original_sql
        assert result["columns"] == ["name"]

    def test_target_checking_fallback_on_error(self):
        """If the refined SQL fails, it should fallback to the original SQL result."""
        original_sql = "SELECT name, department FROM students"
        refined_sql = "SELECT misspelled_name FROM students"
        generator = _make_generator(refined_sql)

        call_count = 0

        def fake_execute(sql, params=()):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"sql": sql, "status": "SUCCESS_WITH_ROWS",
                        "rows": [{"name": "Alice", "department": "CSE"}], 
                        "columns": ["name", "department"],
                        "row_count": 1, "error": None}
            # Refined query fails
            return {"sql": sql, "status": "SCHEMA_ERROR", "rows": [], 
                    "columns": [], "row_count": 0, "error": "no such column"}

        with patch("app.refinement.target_checker.execute_query", side_effect=fake_execute):
            checker = TargetChecker(sql_generator=generator)
            result = checker.check_and_refine_target("Give me the names.", original_sql)

        assert result["target_checked"] is False
        assert result["sql"] == original_sql
        assert result["columns"] == ["name", "department"]
