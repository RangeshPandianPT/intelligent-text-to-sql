import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from app.database.schema import get_database_schema

class SQLValidationError(Exception):
    pass

class SQLSafetyError(SQLValidationError):
    pass

class SQLSchemaError(SQLValidationError):
    pass

class SQLSyntaxError(SQLValidationError):
    pass

def validate_sql(sql: str) -> None:
    """
    Validates a SQL query for safety and schema correctness.
    Raises specific subclasses of SQLValidationError if invalid.
    """
    if not sql or not sql.strip():
        raise SQLSyntaxError("SQL query is empty.")

    try:
        statements = sqlglot.parse(sql, read="sqlite")
    except sqlglot.errors.ParseError as e:
        raise SQLSyntaxError(f"SQL syntax error: {e}")

    if not statements:
        raise SQLSyntaxError("Could not parse SQL query.")
        
    if len(statements) > 1:
        raise SQLSafetyError("Multiple SQL statements are not allowed.")
        
    statement = statements[0]
    
    if not statement:
        raise SQLSyntaxError("Parsed statement is None.")

    # Ensure the root statement is a SELECT
    if not isinstance(statement, exp.Select):
        raise SQLSafetyError("Only SELECT queries are permitted.")
        
    # Check for dangerous nodes
    disallowed_types = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.Pragma,
        exp.Command 
    )
    
    for d_type in disallowed_types:
        if statement.find(d_type):
            raise SQLSafetyError(f"Dangerous SQL operation detected: {d_type.__name__}")

    # Schema Validation
    schema_info = get_database_schema()
    schema_dict = {
        table["name"].lower(): {
            col["name"].lower(): col["type"] for col in table["columns"]
        } for table in schema_info["tables"]
    }
    
    # We must operate on a copy if we want to avoid modifying the AST we parsed, 
    # but since we just throw it away, it's fine to modify `statement` in place.
    try:
        qualify(statement, schema=schema_dict, dialect="sqlite")
    except sqlglot.errors.OptimizeError as e:
        raise SQLSchemaError(f"Schema validation error: {e}")
