from typing import List, Dict, Any
from app.exploration.probe_generator import ProbeGenerator
from app.exploration.probe_executor import ProbeExecutor
from app.exploration.schemas import ProbeResult
from app.config import settings

class ExplorationManager:
    def __init__(self, generator: ProbeGenerator = None, executor: ProbeExecutor = None):
        self.generator = generator or ProbeGenerator()
        self.executor = executor or ProbeExecutor()
        
    def explore(self, question: str, linked_schema: Dict[str, Any]) -> List[ProbeResult]:
        """
        Coordinates the exploration phase.
        1. Generates probes based on the question and schema.
        2. Executes the valid probes.
        3. Returns the results.
        """
        probes = self.generator.generate_probes(
            question=question, 
            linked_schema=linked_schema, 
            max_probes=settings.max_probes
        )
        
        if not probes:
            return []
            
        results = self.executor.execute_probes(probes)
        return results

    def two_stage_explore(self, question: str, linked_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinates the Phase 5 two-stage exploration.
        """
        # Stage A: Candidate Exploration
        stage_a_probes = self.generator.generate_stage_a_probes(
            question=question, 
            linked_schema=linked_schema, 
            max_probes=settings.max_probes
        )
        stage_a_results = self.executor.execute_probes(stage_a_probes) if stage_a_probes else []
        
        # Stage B: Combination Exploration
        stage_b_probes = self.generator.generate_stage_b_probes(
            question=question, 
            linked_schema=linked_schema, 
            stage_a_results=stage_a_results,
            max_probes=settings.max_probes
        )
        stage_b_results = self.executor.execute_probes(stage_b_probes) if stage_b_probes else []
        
        # Separate successful combinations from rejected combinations
        successful_combinations = []
        rejected_combinations = []
        for res in stage_b_results:
            if res.status == "SUCCESS_EMPTY" or res.row_count == 0:
                rejected_combinations.append(res)
            elif res.status == "SUCCESS_WITH_ROWS":
                successful_combinations.append(res)
                
        return {
            "stage_a_results": stage_a_results,
            "stage_b_results": stage_b_results,
            "successful_combinations": successful_combinations,
            "rejected_combinations": rejected_combinations
        }
