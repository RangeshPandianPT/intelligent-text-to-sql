"""
Fast Rule-Based Schema Linker (No LLM)
=======================================
Replaces the LLM-based EntityExtractor + SchemaLinker with deterministic
keyword/token matching against the database schema and live column values.

This reduces schema linking from ~2 LLM calls to 0, giving a large speedup
while maintaining accuracy for common queries.
"""

import re
import logging
from typing import Dict, Any, List

from app.database.schema import get_database_schema
from app.database.executor import execute_query
from app.schema_linking.schemas import LinkedSchema, LinkedTable, LinkedColumn

logger = logging.getLogger(__name__)

# Stop-words to ignore during keyword matching
_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "of", "in", "on", "at", "to",
    "for", "from", "by", "with", "about", "into", "through", "than",
    "more", "most", "and", "or", "not", "no", "me", "my", "we", "our",
    "you", "your", "what", "which", "who", "whom", "all", "any", "each",
    "every", "both", "few", "how", "many", "much", "per", "show", "list",
    "give", "find", "get", "fetch", "display", "tell", "name", "names",
    "i", "need", "want", "their", "there", "where", "when",
}


def _tokenize(text: str) -> List[str]:
    """Lower-case, split on non-alphanumeric, remove stop-words."""
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def _token_overlap(a: str, b: str) -> int:
    """Count shared tokens between two strings."""
    return len(set(_tokenize(a)) & set(_tokenize(b)))


def fast_link(question: str) -> LinkedSchema:
    """
    Perform rule-based schema linking without any LLM call.

    Strategy
    --------
    1. Tokenize the question.
    2. Score every table and column by token overlap with the question tokens.
    3. Mark columns with overlap >= 1 as 'selected'; rest as 'unselected'.
    4. Do a fast LIKE search on text columns to surface candidate values.
    """
    schema = get_database_schema()
    q_tokens = set(_tokenize(question))

    linked_tables: List[LinkedTable] = []

    for table in schema.get("tables", []):
        table_name: str = table["name"]
        table_tokens = set(_tokenize(table_name))
        table_score = len(q_tokens & table_tokens)

        selected_cols: List[LinkedColumn] = []
        unselected_cols: List[Dict] = []

        for col in table["columns"]:
            col_name: str = col["name"]
            col_tokens = set(_tokenize(col_name))
            score = len(q_tokens & col_tokens) + table_score

            if score >= 1:
                # Try to pull candidate values from the DB for text columns
                example_vals: List[str] = []
                if "TEXT" in col["type"].upper() or "VARCHAR" in col["type"].upper():
                    example_vals = _get_candidate_values(
                        table_name, col_name, q_tokens
                    )

                selected_cols.append(
                    LinkedColumn(
                        name=col_name,
                        type=col["type"],
                        description=f"{table_name}.{col_name}",
                        example_values=example_vals,
                    )
                )
            else:
                unselected_cols.append({"name": col_name, "type": col["type"]})

        # Always include a table if at least one column matched, or if the
        # table name itself matched
        if selected_cols or table_score >= 1:
            linked_tables.append(
                LinkedTable(
                    name=table_name,
                    selected_columns=selected_cols,
                    unselected_columns=unselected_cols,
                )
            )
        else:
            # Include the table as fully unselected so the LLM can still
            # reference it if needed
            linked_tables.append(
                LinkedTable(
                    name=table_name,
                    selected_columns=[],
                    unselected_columns=[
                        {"name": c["name"], "type": c["type"]}
                        for c in table["columns"]
                    ],
                )
            )

    return LinkedSchema(tables=linked_tables)


def _get_candidate_values(
    table_name: str, col_name: str, q_tokens: set, limit: int = 5
) -> List[str]:
    """
    Run a fast LIKE query for each question token against a text column.
    Returns distinct matching values (up to `limit`).
    """
    found: List[str] = []
    for token in q_tokens:
        if len(token) < 2:
            continue
        sql = (
            f"SELECT DISTINCT {col_name} FROM {table_name} "
            f"WHERE {col_name} LIKE ? LIMIT {limit}"
        )
        try:
            result = execute_query(sql, (f"%{token}%",))
            for row in result.get("rows", []):
                val = str(row.get(col_name, ""))
                if val and val not in found:
                    found.append(val)
                    if len(found) >= limit:
                        return found
        except Exception:
            pass
    return found

