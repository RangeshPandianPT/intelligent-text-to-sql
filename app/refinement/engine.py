"""
Phase 7: Refinement Engine

Implements an iterative feedback loop that detects failed / empty SQL results and
asks the LLM to produce a corrected query, feeding the previous error (or
"empty result" signal) back as context on each attempt.
"""

import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.database.executor import execute_query
from app.refinement.schemas import RefinementAttempt, RefinementResult

logger = logging.getLogger(__name__)

# Statuses that are considered a successful, useful execution
_SUCCESS_STATUSES = {"SUCCESS_WITH_ROWS"}

# Statuses that warrant a refinement retry
_REFINEMENT_STATUSES = {
    "SUCCESS_EMPTY",
    "SYNTAX_ERROR",
    "SCHEMA_ERROR",
    "EXECUTION_ERROR",
    "SAFETY_REJECTION",
}


def _needs_refinement(status: str) -> bool:
    """Returns True when the SQL result should trigger a refinement attempt."""
    return status in _REFINEMENT_STATUSES


class RefinementEngine:
    """
    Iteratively refines a SQL query until it yields rows or the attempt budget
    is exhausted.

    Refinement strategy
    -------------------
    1. Execute the candidate SQL.
    2. If the result is successful (SUCCESS_WITH_ROWS), stop immediately.
    3. Otherwise, build a refinement prompt that includes:
       - The original user question
       - The linked schema
       - All prior attempts with their error / empty-result signals
       - Optionally, successful probe results from exploration as value hints
    4. Ask the LLM for a corrected SQL and repeat from step 1.
    5. After `max_attempts` total tries, return the best result seen so far.
    """

    def __init__(self, sql_generator, max_attempts: int = None):
        """
        Parameters
        ----------
        sql_generator : SQLGenerator
            The generator whose `generate_refined_sql` will be called.
        max_attempts : int, optional
            Total number of SQL executions allowed (initial + refinements).
            Defaults to `settings.max_refinement_attempts`.
        """
        self.generator = sql_generator
        self.max_attempts = max_attempts if max_attempts is not None else settings.max_refinement_attempts

    def refine(
        self,
        initial_sql: str,
        question: str,
        linked_schema: Dict[str, Any],
        exploration_data: Optional[Dict[str, Any]] = None,
    ) -> RefinementResult:
        """
        Runs the refinement loop starting from `initial_sql`.

        Parameters
        ----------
        initial_sql     : The first SQL to try (produced by Phase 5 or earlier).
        question        : The original user question.
        linked_schema   : The LinkedSchema dict (from Phase 3 / 5).
        exploration_data: Optional exploration results from Phase 5, used to
                          supply the LLM with concrete value hints during
                          refinement.

        Returns
        -------
        RefinementResult with full attempt history.
        """
        attempts: List[RefinementAttempt] = []
        current_sql = initial_sql

        # Gather probe hints once (successful combinations from Phase 5)
        probe_hints: List[Any] = []
        if exploration_data:
            probe_hints = exploration_data.get("successful_combinations", [])

        best_result: Dict[str, Any] = {}

        for attempt_num in range(1, self.max_attempts + 1):
            logger.info(
                "Refinement attempt %d/%d — executing SQL: %.120s…",
                attempt_num,
                self.max_attempts,
                current_sql.replace("\n", " "),
            )

            exec_result = execute_query(current_sql)
            status = exec_result.get("status", "EXECUTION_ERROR")
            error = exec_result.get("error")
            row_count = exec_result.get("row_count", 0)

            # Record this attempt
            attempts.append(
                RefinementAttempt(
                    attempt_number=attempt_num,
                    sql=current_sql,
                    status=status,
                    error=error,
                    row_count=row_count,
                )
            )

            # Keep track of the last executed result
            best_result = exec_result

            if not _needs_refinement(status):
                # We have rows — success, stop the loop
                logger.info("Refinement succeeded on attempt %d.", attempt_num)
                break

            if attempt_num == self.max_attempts:
                # Budget exhausted
                logger.warning(
                    "Refinement budget exhausted after %d attempts. "
                    "Returning last result (status=%s).",
                    self.max_attempts,
                    status,
                )
                break

            # Build prior-attempt context for the LLM
            prior_attempts_for_prompt = [
                {"attempt": a.attempt_number, "sql": a.sql, "status": a.status, "error": a.error}
                for a in attempts
            ]

            # Ask LLM for a refined SQL
            try:
                response = self.generator.generate_refined_sql(
                    question=question,
                    linked_schema=linked_schema,
                    prior_attempts=prior_attempts_for_prompt,
                    probe_hints=probe_hints,
                )
                current_sql = response.sql
            except Exception as e:
                logger.error("LLM refinement generation failed: %s", e)
                # Cannot generate a new SQL, abort early
                best_result["status"] = "REFINEMENT_LLM_ERROR"
                best_result["error"] = str(e)
                break

        # Build the consolidated result
        refined = len(attempts) > 1
        final_status = best_result.get("status", "EXECUTION_ERROR")

        return RefinementResult(
            final_sql=best_result.get("sql", current_sql),
            final_status=final_status,
            final_rows=best_result.get("rows", []),
            final_columns=best_result.get("columns", []),
            final_row_count=best_result.get("row_count", 0),
            final_execution_time_ms=best_result.get("execution_time_ms", 0.0),
            total_attempts=len(attempts),
            refinement_attempts=attempts,
            error=best_result.get("error"),
            refined=refined,
        )
