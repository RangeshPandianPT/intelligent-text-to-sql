import time
import sqlite3
import logging
from typing import Dict, Any
from app.database.connection import get_connection
from app.database.validator import validate_sql, SQLSafetyError, SQLSchemaError, SQLSyntaxError
from app.config import settings

logger = logging.getLogger(__name__)

def execute_query(sql: str, params: tuple = ()) -> Dict[str, Any]:
    """
    Executes a SQL query safely and returns the results with metadata.
    """
    start_time = time.perf_counter()
    
    result = {
        "sql": sql,
        "status": "EXECUTION_ERROR",
        "rows": [],
        "columns": [],
        "row_count": 0,
        "execution_time_ms": 0.0,
        "error": None
    }
    
    try:
        # Step 1: Validation (Syntax, Safety, Schema)
        validate_sql(sql)
        
        # Step 2: Execution (read-only)
        with get_connection(read_only=True) as conn:
            cursor = conn.cursor()
            
            cursor.execute(sql, params)
            
            columns = [description[0] for description in cursor.description] if cursor.description else []
            result["columns"] = columns
            
            rows = cursor.fetchmany(settings.max_rows)
            result["rows"] = [dict(row) for row in rows]
            result["row_count"] = len(result["rows"])
            
            # The spec specifies SUCCESS_WITH_ROWS and SUCCESS_EMPTY, 
            # we can merge success_truncated into SUCCESS_WITH_ROWS for the spec's sake.
            if result["row_count"] == 0:
                result["status"] = "SUCCESS_EMPTY"
            else:
                result["status"] = "SUCCESS_WITH_ROWS"

    except SQLSyntaxError as e:
        result["status"] = "SYNTAX_ERROR"
        result["error"] = str(e)
    except SQLSchemaError as e:
        result["status"] = "SCHEMA_ERROR"
        result["error"] = str(e)
    except SQLSafetyError as e:
        result["status"] = "SAFETY_REJECTION"
        result["error"] = str(e)
    except sqlite3.Error as e:
        result["status"] = "EXECUTION_ERROR"
        result["error"] = str(e)
    except Exception as e:
        result["status"] = "EXECUTION_ERROR"
        result["error"] = str(e)
    finally:
        end_time = time.perf_counter()
        result["execution_time_ms"] = round((end_time - start_time) * 1000, 2)
        
    return result
