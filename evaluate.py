import json
import logging
from pathlib import Path
from tqdm import tqdm
from app.pipeline.orchestrator import run_pipeline, run_baseline_pipeline
from app.database.executor import execute_query

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def standardize_rows(rows):
    """Convert rows to a set of tuples for order-agnostic comparison."""
    if not rows:
        return set()
    return set(tuple(row.values()) for row in rows)

def run_evaluation(data_path="data/evaluation.json", output_path="data/evaluation_results.json"):
    with open(data_path, "r") as f:
        dataset = json.load(f)

    results = []
    
    total = len(dataset)
    correct_count = 0
    valid_sql_count = 0
    refinement_used_count = 0
    refinement_success_count = 0
    total_probes = 0
    total_latency = 0
    total_refinement_iterations = 0

    print(f"Starting evaluation of {total} questions...")

    for item in tqdm(dataset):
        question = item["question"]
        gold_sql = item["gold_sql"]
        
        # Get ground truth
        gold_result = execute_query(gold_sql)
        gold_rows = standardize_rows(gold_result.get("rows", []))
        
        # Run SDE-SQL pipeline
        pipeline_result = run_pipeline(question)
        
        predicted_rows = standardize_rows(pipeline_result.get("rows", []))
        
        # Calculate metrics for this item
        status = pipeline_result.get("status", "")
        is_valid_sql = status in ["SUCCESS_WITH_ROWS", "SUCCESS_EMPTY"]
        is_correct = is_valid_sql and predicted_rows == gold_rows
        
        trace = pipeline_result.get("trace", {})
        probes = trace.get("probes", [])
        refinements = trace.get("refinement", [])
        
        probes_count = len(probes)
        refinement_iterations = len(refinements)
        
        used_refinement = refinement_iterations > 0
        
        # Consider refinement successful if the query ultimately yielded a correct result 
        # and refinement was invoked.
        refinement_successful = used_refinement and is_correct

        latency = pipeline_result.get("execution_time_ms", 0)
        
        # Update aggregates
        if is_correct:
            correct_count += 1
        if is_valid_sql:
            valid_sql_count += 1
        if used_refinement:
            refinement_used_count += 1
        if refinement_successful:
            refinement_success_count += 1
            
        total_probes += probes_count
        total_latency += latency
        total_refinement_iterations += refinement_iterations

        # Record result
        item_result = {
            "question": question,
            "gold_sql": gold_sql,
            "predicted_sql": pipeline_result.get("sql", ""),
            "status": status,
            "is_correct": is_correct,
            "is_valid_sql": is_valid_sql,
            "probes_count": probes_count,
            "refinement_iterations": refinement_iterations,
            "latency_ms": latency
        }
        results.append(item_result)

    # Compute averages
    exec_accuracy = (correct_count / total) * 100
    valid_rate = (valid_sql_count / total) * 100
    refine_success_rate = (refinement_success_count / refinement_used_count * 100) if refinement_used_count > 0 else 0
    avg_probes = total_probes / total
    avg_latency = total_latency / total
    avg_refine_iters = total_refinement_iterations / total

    metrics = {
        "execution_accuracy": f"{exec_accuracy:.2f}%",
        "valid_sql_rate": f"{valid_rate:.2f}%",
        "refinement_usage": f"{refinement_used_count}/{total}",
        "refinement_success_rate": f"{refine_success_rate:.2f}%",
        "avg_probes_per_question": f"{avg_probes:.2f}",
        "avg_latency_ms": f"{avg_latency:.2f}",
        "avg_refinement_iterations": f"{avg_refine_iters:.2f}"
    }

    print("\n--- Evaluation Summary ---")
    for k, v in metrics.items():
        print(f"{k}: {v}")

    # Save to file
    with open(output_path, "w") as f:
        json.dump({
            "metrics": metrics,
            "results": results
        }, f, indent=2)
    
    print(f"\nSaved detailed results to {output_path}")

if __name__ == "__main__":
    run_evaluation()
