from app.llm.client import OllamaClient
from app.llm.generator import SQLGenerator
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
