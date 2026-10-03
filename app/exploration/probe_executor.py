from typing import List
import logging
from app.exploration.schemas import Probe, ProbeResult
from app.database.executor import execute_query

logger = logging.getLogger(__name__)

class ProbeExecutor:
    def execute_probes(self, probes: List[Probe]) -> List[ProbeResult]:
        results = []
        for probe in probes:
            logger.info(f"Executing probe: {probe.purpose} -> {probe.sql}")
            exec_result = execute_query(probe.sql)
            
            result = ProbeResult(
                probe=probe,
                status=exec_result["status"],
                rows=exec_result["rows"],
                row_count=exec_result["row_count"],
                execution_time_ms=exec_result["execution_time_ms"],
                error=exec_result["error"]
            )
            results.append(result)
        return results
