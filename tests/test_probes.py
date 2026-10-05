import pytest
from app.exploration.schemas import Probe
from app.exploration.probe_executor import ProbeExecutor

def test_probe_executor_valid_sql():
    executor = ProbeExecutor()
    probe = Probe(purpose="Test valid SQL", sql="SELECT 1 as num")
    results = executor.execute_probes([probe])
    
    assert len(results) == 1
    assert results[0].status == "SUCCESS_WITH_ROWS"
    assert results[0].rows == [{"num": 1}]

def test_probe_executor_invalid_sql():
    executor = ProbeExecutor()
    probe = Probe(purpose="Test invalid SQL", sql="SELECT * FROM non_existent_table_12345")
    results = executor.execute_probes([probe])
    
    assert len(results) == 1
    assert "ERROR" in results[0].status
