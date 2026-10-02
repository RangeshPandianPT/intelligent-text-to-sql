from app.llm.client import OllamaClient
from app.llm.generator import SQLGenerator
from app.schema_linking.linker import SchemaLinker
from app.database.executor import execute_query
from app.database.safety import validate_sql_safety, SQLSafetyError

def run_baseline_pipeline(question: str, llm_client=None) -> dict:
    """
    Runs the baseline Text-to-SQL pipeline.
    Question -> Schema -> LLM -> SQL -> Validator -> Database -> Result
    """
    if llm_client is None:
        llm_client = OllamaClient()
        
    generator = SQLGenerator(llm_client)
    
    # 1. Generate SQL
    try:
        response = generator.generate_baseline_sql(question)
        sql = response.sql
    except Exception as e:
        return {
            "status": "generation_error",
            "error": str(e)
        }
    
    # 2. Validate Safety
    try:
        validate_sql_safety(sql)
    except SQLSafetyError as e:
        return {
            "status": "safety_rejection",
            "sql": sql,
            "error": str(e)
        }
        
    # 3. Execute
    result = execute_query(sql)
    result["sql"] = sql  # Include generated SQL in the result
    return result

def run_phase3_pipeline(question: str, llm_client=None) -> dict:
    """
    Runs the Text-to-SQL pipeline using Schema Linking (Phase 3).
    Question -> Entity Extraction -> Candidate Values -> Linked Schema -> LLM -> SQL -> Validator -> Database -> Result
    """
    if llm_client is None:
        llm_client = OllamaClient()
        
    linker = SchemaLinker(llm_client)
    generator = SQLGenerator(llm_client)
    
    # 1. Schema Linking
    try:
        linked_schema = linker.link(question)
    except Exception as e:
        return {
            "status": "schema_linking_error",
            "error": str(e)
        }
    
    # 2. Generate SQL
    try:
        response = generator.generate_linked_sql(question, linked_schema)
        sql = response.sql
    except Exception as e:
        return {
            "status": "generation_error",
            "error": str(e),
            "linked_schema": linked_schema.dict()
        }
    
    # 3. Validate Safety
    try:
        validate_sql_safety(sql)
    except SQLSafetyError as e:
        return {
            "status": "safety_rejection",
            "sql": sql,
            "error": str(e),
            "linked_schema": linked_schema.dict()
        }
        
    # 4. Execute
    result = execute_query(sql)
    result["sql"] = sql
    result["linked_schema"] = linked_schema.dict()
    return result
