import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from app.database.schema import get_database_schema
from app.database.safety import (
    SQLSafetyError,
    validate_sql_safety,
    enforce_query_limits
)

class SQLValidationError(Exception):
    pass

class SQLSchemaError(SQLValidationError):
    pass

class SQLSyntaxError(SQLValidationError):
    pass

def validate_sql(sql: str) -> None:
    """
    Validates a SQL query for multi-layer safety and schema correctness.
    Raises SQLSafetyError, SQLSyntaxError, or SQLSchemaError if invalid.
    """
    if not sql or not sql.strip():
        raise SQLSyntaxError("SQL query is empty.")

    # 1. Multi-layer AST safety checks (SELECT-only, DDL/DML, exploits, tautologies)
    validate_sql_safety(sql)

    # 2. Schema Validation via SQLGlot qualify
    try:
        statement = sqlglot.parse_one(sql, read="sqlite")
    except Exception as e:
        raise SQLSyntaxError(f"SQL syntax error: {e}")

    schema_info = get_database_schema()
    schema_dict = {
        table["name"].lower(): {
            col["name"].lower(): col["type"] for col in table["columns"]
        } for table in schema_info["tables"]
    }

    try:
        qualify(statement, schema=schema_dict, dialect="sqlite")
    except sqlglot.errors.OptimizeError as e:
        raise SQLSchemaError(f"Schema validation error: {e}")
