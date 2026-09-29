from typing import Dict, Any, List
from app.database.connection import get_connection

def get_database_schema() -> Dict[str, Any]:
    """
    Extracts the full schema of the SQLite database dynamically.
    Returns a dictionary of tables and their columns with types.
    """
    schema = {"tables": []}
    
    with get_connection(read_only=True) as conn:
        cursor = conn.cursor()
        
        # Get all non-system tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row['name'] for row in cursor.fetchall()]
        
        for table_name in tables:
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns_info = cursor.fetchall()
            
            columns = []
            for col in columns_info:
                columns.append({
                    "name": col['name'],
                    "type": col['type'],
                    "primary_key": bool(col['pk'])
                })
                
            schema["tables"].append({
                "name": table_name,
                "columns": columns
            })
            
    return schema
