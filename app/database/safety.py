import sqlglot
from sqlglot import exp

class SQLSafetyError(Exception):
    """Raised when a SQL query fails safety checks."""
    pass

def validate_sql_safety(sql: str) -> None:
    """
    Validates a SQL query for safety.
    Ensures it is only a single SELECT statement and contains no dangerous operations.
    Raises SQLSafetyError if invalid.
    """
    if not sql or not sql.strip():
        raise SQLSafetyError("SQL query is empty.")

    try:
        # Check for multiple statements
        statements = sqlglot.parse(sql, read="sqlite")
        
        if not statements:
            raise SQLSafetyError("Could not parse SQL query.")
            
        if len(statements) > 1:
            raise SQLSafetyError("Multiple SQL statements are not allowed.")
            
        statement = statements[0]
        
        if not statement:
            raise SQLSafetyError("Parsed statement is None.")

        # Ensure the root statement is a SELECT
        if not isinstance(statement, exp.Select):
            raise SQLSafetyError("Only SELECT queries are permitted.")
            
        # Traverse the AST to look for dangerous nodes or pragmas
        for node in statement.walk():
            # In sqlglot, walk() returns tuples of (node, parent, key) or similar?
            # Actually node.walk() yields `node` (wait, no, walk returns generator of nodes or (node, parent, key) depending on sqlglot version). 
            # `find_all` is safer and easier.
            pass
            
        # Let's explicitly check for disallowed node types using find()
        disallowed_types = (
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Drop,
            exp.Create,
            exp.Alter,
            exp.Pragma,
            exp.Command # Handles things like ATTACH etc.
        )
        
        for d_type in disallowed_types:
            if statement.find(d_type):
                raise SQLSafetyError(f"Dangerous SQL operation detected: {d_type.__name__}")

    except sqlglot.errors.ParseError as e:
        raise SQLSafetyError(f"SQL syntax error: {e}")
