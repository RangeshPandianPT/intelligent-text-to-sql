import time
import sqlite3
import logging
from typing import Dict, Any
from app.database.connection import get_connection
from app.database.safety import validate_sql_safety, SQLSafetyError
from app.config import settings

logger = logging.getLogger(__name__)

def execute_query(sql: str, params: tuple = ()) -> Dict[str, Any]:
    """
    Executes a SQL query safely and returns the results with metadata.
    """
    start_time = time.perf_counter()
    
    result = {
        "sql": sql,
        "status": "error",
        "rows": [],
        "columns": [],
        "row_count": 0,
        "execution_time_ms": 0.0,
        "error": None
    }
    
    try:
        # Step 1: Safety validation
        validate_sql_safety(sql)
        
        # Step 2: Execution (read-only)
        with get_connection(read_only=True) as conn:
            # We can't strictly timeout sqlite3 queries in Python easily without
            # interrupt() or threads, but we can set a progress handler.
            # For simplicity, we just rely on standard execution and limit rows.
            
            cursor = conn.cursor()
            
            # Optionally wrap with a row limit if not present, but for now we just fetch up to MAX_ROWS.
            cursor.execute(sql, params)
            
            columns = [description[0] for description in cursor.description] if cursor.description else []
            result["columns"] = columns
            
            rows = cursor.fetchmany(settings.max_rows)
            result["rows"] = [dict(row) for row in rows]
            result["row_count"] = len(result["rows"])
            
            # Check if there are more rows we didn't fetch
            if len(rows) == settings.max_rows and cursor.fetchone() is not None:
                result["status"] = "success_truncated"
            elif result["row_count"] == 0:
                result["status"] = "success_empty"
            else:
                result["status"] = "success_with_rows"

    except SQLSafetyError as e:
        result["status"] = "safety_rejection"
        result["error"] = str(e)
    except sqlite3.Error as e:
        # Usually a schema or execution error
        result["status"] = "execution_error"
        result["error"] = str(e)
    except Exception as e:
        result["status"] = "system_error"
        result["error"] = str(e)
    finally:
        end_time = time.perf_counter()
        result["execution_time_ms"] = round((end_time - start_time) * 1000, 2)
        
    return result
