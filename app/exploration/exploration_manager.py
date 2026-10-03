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
