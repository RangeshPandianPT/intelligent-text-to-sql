import logging
from typing import Dict, Any
from app.llm.generator import SQLGenerator
from app.database.executor import execute_query

logger = logging.getLogger(__name__)

class TargetChecker:
    """
    Phase 8: Target Checking
    
    Ensures that the SQL SELECT target precisely matches the user's request.
    If the generator included extra columns, this component asks the LLM to prune them
    without altering the core logic.
    """
    def __init__(self, sql_generator: SQLGenerator):
        self.generator = sql_generator

    def check_and_refine_target(self, question: str, generated_sql: str) -> Dict[str, Any]:
        """
        Checks if the SELECT target strictly corresponds to what was requested, 
        and prunes unnecessary columns if needed.
        
        Executes the pruned query and returns the final execution result.
        If pruning fails or errors, it falls back to the original SQL's result.
        
        Parameters
        ----------
        question      : The original user question.
        generated_sql : The SQL that is already working and produces rows.
        
        Returns
        -------
        Dict[str, Any] containing the final executed query result.
        """
        logger.info("Performing target checking on SQL: %.120s...", generated_sql.replace("\n", " "))
        
        # Execute the original SQL to get a baseline result
        original_result = execute_query(generated_sql)
        
        # If original didn't even succeed, just return it. Target checking shouldn't fix broken SQL.
        if original_result.get("status") not in ("SUCCESS_WITH_ROWS", "SUCCESS_EMPTY"):
            original_result["target_checked"] = False
            return original_result
            
        try:
            # Ask the LLM to check and optionally refine the target
            response = self.generator.generate_target_checked_sql(
                question=question, 
                generated_sql=generated_sql
            )
            refined_sql = response.sql
            
            # If the LLM returned the exact same SQL, just return the original result
            if refined_sql.strip() == generated_sql.strip():
                logger.info("Target checking made no changes.")
                original_result["target_checked"] = False
                return original_result
                
            logger.info("Target checking produced new SQL: %.120s...", refined_sql.replace("\n", " "))
            
            # Execute the refined SQL
            refined_result = execute_query(refined_sql)
            
            # If the new SQL fails, fallback to the original
            if refined_result.get("status") not in ("SUCCESS_WITH_ROWS", "SUCCESS_EMPTY"):
                logger.warning("Target checked SQL failed (%s). Falling back to original SQL.", refined_result.get("status"))
                original_result["target_checked"] = False
                return original_result
                
            # If successful, return the refined result
            refined_result["target_checked"] = True
            refined_result["original_sql"] = generated_sql
            return refined_result
            
        except Exception as e:
            logger.error("Target checking failed: %s", e)
            original_result["target_checked"] = False
            return original_result
