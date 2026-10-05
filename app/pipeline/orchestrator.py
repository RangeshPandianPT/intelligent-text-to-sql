from app.llm.client import OllamaClient
from app.llm.generator import SQLGenerator
from app.schema_linking.linker import SchemaLinker
from app.exploration.exploration_manager import ExplorationManager
from app.database.executor import execute_query

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
    
    # 2. Execute
    result = execute_query(sql)
    # The generated SQL is already included in result by execute_query
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
    
    # 3. Execute
    result = execute_query(sql)
    result["linked_schema"] = linked_schema.dict()
    return result

def run_phase5_pipeline(question: str, llm_client=None) -> dict:
    """
    Runs the Text-to-SQL pipeline using Schema Linking AND Two-Stage Exploration (Phase 5).
    """
    if llm_client is None:
        llm_client = OllamaClient()
        
    linker = SchemaLinker(llm_client)
    generator = SQLGenerator(llm_client)
    explorer = ExplorationManager()
    
    # 1. Schema Linking
    try:
        linked_schema = linker.link(question)
    except Exception as e:
        return {
            "status": "schema_linking_error",
            "error": str(e)
        }
        
    # 2. Two-Stage Exploration
    try:
        exploration_data = explorer.two_stage_explore(question, linked_schema.dict())
    except Exception as e:
        return {
            "status": "exploration_error",
            "error": str(e),
            "linked_schema": linked_schema.dict()
        }
    
    # 3. Generate SQL
    try:
        response = generator.generate_explored_sql(
            question, 
            linked_schema, 
            exploration_data["successful_combinations"], 
            exploration_data["rejected_combinations"]
        )
        sql = response.sql
    except Exception as e:
        return {
            "status": "generation_error",
            "error": str(e),
            "linked_schema": linked_schema.dict(),
            "exploration": exploration_data
        }
    
    # 4. Execute
    result = execute_query(sql)
    result["linked_schema"] = linked_schema.dict()
    # Serialize exploration data for JSON (ProbeResult models -> dict)
    result["exploration"] = {
        "stage_a_results": [r.dict() for r in exploration_data["stage_a_results"]],
        "stage_b_results": [r.dict() for r in exploration_data["stage_b_results"]],
        "successful_combinations": [r.dict() for r in exploration_data["successful_combinations"]],
        "rejected_combinations": [r.dict() for r in exploration_data["rejected_combinations"]]
    }
    return result
