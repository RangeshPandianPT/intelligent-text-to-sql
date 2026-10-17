from app.llm.client import OllamaClient
from app.llm.generator import SQLGenerator
from app.schema_linking.linker import SchemaLinker
from app.exploration.exploration_manager import ExplorationManager
from app.exploration.probe_generator import ProbeGenerator
from app.database.executor import execute_query
from app.database.schema import get_database_schema
from app.refinement.engine import RefinementEngine
from app.refinement.target_checker import TargetChecker

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


def run_phase7_pipeline(question: str, llm_client=None) -> dict:
    """
    Runs the full SDE-SQL pipeline with the Phase 7 Refinement Engine.

    Flow:
        Question
          → Schema Linking  (Phase 3)
          → Two-Stage Exploration  (Phase 5)
          → Initial SQL Generation
          → Refinement Loop  (Phase 7)  ← iteratively corrects errors / empty results
          → Final Result
    """
    if llm_client is None:
        llm_client = OllamaClient()

    linker = SchemaLinker(llm_client)
    generator = SQLGenerator(llm_client)
    explorer = ExplorationManager()
    refiner = RefinementEngine(sql_generator=generator)

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

    # 3. Initial SQL Generation (same as Phase 5)
    try:
        response = generator.generate_explored_sql(
            question,
            linked_schema,
            exploration_data["successful_combinations"],
            exploration_data["rejected_combinations"]
        )
        initial_sql = response.sql
    except Exception as e:
        return {
            "status": "generation_error",
            "error": str(e),
            "linked_schema": linked_schema.dict(),
            "exploration": {
                "stage_a_results": [r.dict() for r in exploration_data["stage_a_results"]],
                "stage_b_results": [r.dict() for r in exploration_data["stage_b_results"]],
                "successful_combinations": [r.dict() for r in exploration_data["successful_combinations"]],
                "rejected_combinations": [r.dict() for r in exploration_data["rejected_combinations"]]
            }
        }

    # 4. Refinement Loop
    refinement_result = refiner.refine(
        initial_sql=initial_sql,
        question=question,
        linked_schema=linked_schema.dict(),
        exploration_data=exploration_data,
    )

    # 5. Assemble response
    return {
        "sql": refinement_result.final_sql,
        "status": refinement_result.final_status,
        "rows": refinement_result.final_rows,
        "columns": refinement_result.final_columns,
        "row_count": refinement_result.final_row_count,
        "execution_time_ms": refinement_result.final_execution_time_ms,
        "error": refinement_result.error,
        "refined": refinement_result.refined,
        "total_attempts": refinement_result.total_attempts,
        "refinement_attempts": [a.dict() for a in refinement_result.refinement_attempts],
        "linked_schema": linked_schema.dict(),
        "exploration": {
            "stage_a_results": [r.dict() for r in exploration_data["stage_a_results"]],
            "stage_b_results": [r.dict() for r in exploration_data["stage_b_results"]],
            "successful_combinations": [r.dict() for r in exploration_data["successful_combinations"]],
            "rejected_combinations": [r.dict() for r in exploration_data["rejected_combinations"]]
        }
    }


def run_pipeline(
    question: str,
    llm_client=None,
    enable_schema_linking: bool = True,
    enable_generation_exploration: bool = True,
    enable_refinement: bool = True,
    enable_refinement_exploration: bool = True,
    enable_target_checking: bool = True,
) -> dict:
    """
    Runs the SDE-SQL pipeline with configurable ablation flags (Phase 9 & Phase 14).

    Parameters
    ----------
    question: str
        The natural language query.
    llm_client: LLMClient, optional
        LLM client to use. Defaults to OllamaClient().
    enable_schema_linking: bool
        Whether to perform schema linking before SQL generation.
    enable_generation_exploration: bool
        Whether to run two-stage SQL exploration probes before generation.
    enable_refinement: bool
        Whether to iteratively refine failed/empty SQL results.
    enable_refinement_exploration: bool
        Whether to pass exploration probe hints during refinement.
    enable_target_checking: bool
        Whether to verify and prune SELECT target columns.
    """
    if llm_client is None:
        llm_client = OllamaClient()

    linker = SchemaLinker(llm_client)
    generator = SQLGenerator(llm_client)
    probe_generator = ProbeGenerator(llm_client=llm_client)
    explorer = ExplorationManager(generator=probe_generator)
    refiner = RefinementEngine(sql_generator=generator)
    target_checker = TargetChecker(sql_generator=generator)

    def _to_dict(obj):
        if obj is None:
            return None
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        return obj

    linked_schema = None
    linked_schema_dict = {}
    exploration_data = None
    probes_list = []

    # 1. Schema Linking
    if enable_schema_linking:
        try:
            linked_schema = linker.link(question)
            linked_schema_dict = _to_dict(linked_schema) or {}
        except Exception as e:
            return {
                "question": question,
                "status": "schema_linking_error",
                "sql": "",
                "rows": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "trace": {}
            }

    # 2. Generation Exploration
    if enable_generation_exploration:
        schema_for_exploration = linked_schema_dict if enable_schema_linking else get_database_schema()
        try:
            exploration_data = explorer.two_stage_explore(question, schema_for_exploration)
            stage_a = [_to_dict(r) for r in exploration_data.get("stage_a_results", [])]
            stage_b = [_to_dict(r) for r in exploration_data.get("stage_b_results", [])]
            probes_list = stage_a + stage_b
        except Exception as e:
            return {
                "question": question,
                "status": "exploration_error",
                "sql": "",
                "rows": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "trace": {
                    "schema_linking": linked_schema_dict if enable_schema_linking else None
                }
            }

    # 3. Initial SQL Generation
    try:
        if enable_generation_exploration and exploration_data:
            schema_to_pass = linked_schema if enable_schema_linking else linked_schema_dict
            response = generator.generate_explored_sql(
                question,
                schema_to_pass,
                exploration_data["successful_combinations"],
                exploration_data["rejected_combinations"]
            )
        elif enable_schema_linking and linked_schema:
            response = generator.generate_linked_sql(question, linked_schema)
        else:
            response = generator.generate_baseline_sql(question)
        initial_sql = response.sql
    except Exception as e:
        return {
            "question": question,
            "status": "generation_error",
            "sql": "",
            "rows": [],
            "row_count": 0,
            "execution_time_ms": 0,
            "trace": {
                "schema_linking": linked_schema_dict if enable_schema_linking else None,
                "probes": probes_list
            }
        }

    # 4. Refinement Loop or Direct Execution
    refinement_attempts = []
    if enable_refinement:
        schema_for_refinement = linked_schema_dict if enable_schema_linking else get_database_schema()
        refinement_result = refiner.refine(
            initial_sql=initial_sql,
            question=question,
            linked_schema=schema_for_refinement,
            exploration_data=exploration_data,
            enable_refinement_exploration=enable_refinement_exploration,
        )
        current_sql = refinement_result.final_sql
        candidate_result = {
            "sql": current_sql,
            "status": refinement_result.final_status,
            "rows": refinement_result.final_rows,
            "row_count": refinement_result.final_row_count,
            "execution_time_ms": refinement_result.final_execution_time_ms,
            "error": refinement_result.error,
        }
        refinement_attempts = [_to_dict(a) for a in refinement_result.refinement_attempts]
    else:
        candidate_result = execute_query(initial_sql)
        current_sql = candidate_result.get("sql", initial_sql)

    # 5. Target Checking
    if enable_target_checking:
        final_result = target_checker.check_and_refine_target(question, current_sql)
    else:
        final_result = candidate_result

    # 6. Assemble Final Response
    trace = {
        "schema_linking": linked_schema_dict if enable_schema_linking else None,
        "probes": probes_list,
        "refinement": refinement_attempts
    }

    return {
        "question": question,
        "status": final_result.get("status", "error"),
        "sql": final_result.get("sql", ""),
        "rows": final_result.get("rows", []),
        "row_count": final_result.get("row_count", 0),
        "execution_time_ms": final_result.get("execution_time_ms", 0),
        "trace": trace
    }

