import pytest
from app.database.schema import get_database_schema
from app.database.safety import validate_sql_safety, SQLSafetyError
from app.database.executor import execute_query
from app.config import settings

def test_schema_extraction():
    schema = get_database_schema()
    assert "tables" in schema
    table_names = [t["name"] for t in schema["tables"]]
    assert "students" in table_names
    assert "courses" in table_names
    assert "enrollments" in table_names

def test_execute_valid_select():
    result = execute_query("SELECT * FROM students")
    assert result["status"] in ("success_with_rows", "success_truncated")
    assert result["row_count"] > 0
    assert "student_id" in result["columns"]
    assert "name" in result["columns"]

def test_filtering():
    result = execute_query("SELECT * FROM students WHERE department = 'CSE'")
    assert result["status"] == "success_with_rows"
    for row in result["rows"]:
        assert row["department"] == "CSE"

def test_aggregation():
    result = execute_query("SELECT COUNT(*) as count FROM students")
    assert result["status"] == "success_with_rows"
    assert result["rows"][0]["count"] == 10  # Based on seed data

def test_joins():
    sql = """
    SELECT s.name, c.course_name, e.marks 
    FROM students s
    JOIN enrollments e ON s.student_id = e.student_id
    JOIN courses c ON e.course_id = c.course_id
    WHERE s.department = 'CSE'
    """
    result = execute_query(sql)
    assert result["status"] == "success_with_rows"
    assert len(result["columns"]) == 3
    assert result["row_count"] > 0

def test_invalid_sql_detection():
    result = execute_query("SELECT * FROM non_existent_table")
    assert result["status"] == "execution_error"
    assert "error" in result

def test_dangerous_sql_rejection():
    # Attempting to drop a table
    result = execute_query("DROP TABLE students")
    assert result["status"] == "safety_rejection"
    assert "Only SELECT queries are permitted" in result["error"]
    
    # Attempting to insert data
    result = execute_query("INSERT INTO students (student_id, name) VALUES (999, 'Hacker')")
    assert result["status"] == "safety_rejection"
    assert "Only SELECT queries are permitted" in result["error"]

def test_multiple_statements_rejection():
    result = execute_query("SELECT * FROM students; DROP TABLE courses;")
    assert result["status"] == "safety_rejection"
    assert "Multiple SQL statements" in result["error"]

def test_row_limit(monkeypatch):
    # Temporarily lower the row limit
    monkeypatch.setattr(settings, "max_rows", 2)
    result = execute_query("SELECT * FROM students")
    assert result["status"] == "success_truncated"
    assert result["row_count"] == 2
