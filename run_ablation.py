"""
Phase 14: Ablation Study Runner

Evaluates the SDE-SQL pipeline across different component configurations:
1. Baseline: Pure Text-to-SQL (No Schema Linking, No Probes, No Refinement, No Target Checking)
2. + Schema Linking
3. + Generation Exploration
4. + Refinement
5. + Gen & Refine Exploration
6. Full SDE-SQL (Schema Linking + Gen Exploration + Refinement + Target Checking)

Outputs the comparative ablation metrics table and saves results to data/ablation_results.json.
"""

import json
import logging
import argparse
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable
from app.pipeline.orchestrator import run_pipeline
from app.database.executor import execute_query

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CONFIGURATIONS = {
    "Baseline": {
        "enable_schema_linking": False,
        "enable_generation_exploration": False,
        "enable_refinement": False,
        "enable_refinement_exploration": False,
        "enable_target_checking": False,
    },
    "+ Schema Linking": {
        "enable_schema_linking": True,
        "enable_generation_exploration": False,
        "enable_refinement": False,
        "enable_refinement_exploration": False,
        "enable_target_checking": False,
    },
    "+ Generation Exploration": {
        "enable_schema_linking": True,
        "enable_generation_exploration": True,
        "enable_refinement": False,
        "enable_refinement_exploration": False,
        "enable_target_checking": False,
    },
    "+ Refinement": {
        "enable_schema_linking": True,
        "enable_generation_exploration": False,
        "enable_refinement": True,
        "enable_refinement_exploration": False,
        "enable_target_checking": False,
    },
    "+ Gen & Refine Exploration": {
        "enable_schema_linking": True,
        "enable_generation_exploration": True,
        "enable_refinement": True,
        "enable_refinement_exploration": True,
        "enable_target_checking": False,
    },
    "Full SDE-SQL": {
        "enable_schema_linking": True,
        "enable_generation_exploration": True,
        "enable_refinement": True,
        "enable_refinement_exploration": True,
        "enable_target_checking": True,
    },
}

def standardize_rows(rows):
    """Convert rows to a set of tuples for order-agnostic comparison."""
    if not rows:
        return set()
    return set(tuple(row.values()) for row in rows)

def evaluate_configuration(config_name: str, config_flags: dict, dataset: list, llm_client=None) -> dict:
    """Runs a single ablation configuration over the dataset."""
    total = len(dataset)
    correct_count = 0
    valid_sql_count = 0
    total_probes = 0
    total_latency = 0
    item_results = []

    print(f"\nEvaluating configuration: [{config_name}] ({total} items)...")

    for item in tqdm(dataset, desc=config_name):
        question = item["question"]
        gold_sql = item["gold_sql"]

        # Ground truth
        gold_result = execute_query(gold_sql)
        gold_rows = standardize_rows(gold_result.get("rows", []))

        # Pipeline execution
        pipeline_result = run_pipeline(question, llm_client=llm_client, **config_flags)

        predicted_rows = standardize_rows(pipeline_result.get("rows", []))
        status = pipeline_result.get("status", "")
        is_valid_sql = status in ["SUCCESS_WITH_ROWS", "SUCCESS_EMPTY"]
        is_correct = is_valid_sql and predicted_rows == gold_rows

        trace = pipeline_result.get("trace", {}) or {}
        probes = trace.get("probes", []) or []
        probes_count = len(probes)
        latency = pipeline_result.get("execution_time_ms", 0.0)

        if is_correct:
            correct_count += 1
        if is_valid_sql:
            valid_sql_count += 1
        total_probes += probes_count
        total_latency += latency

        item_results.append({
            "question": question,
            "gold_sql": gold_sql,
            "predicted_sql": pipeline_result.get("sql", ""),
            "status": status,
            "is_correct": is_correct,
            "is_valid_sql": is_valid_sql,
            "probes_count": probes_count,
            "latency_ms": latency
        })

    exec_acc = (correct_count / total * 100) if total > 0 else 0.0
    valid_rate = (valid_sql_count / total * 100) if total > 0 else 0.0
    avg_probes = (total_probes / total) if total > 0 else 0.0
    avg_latency = (total_latency / total) if total > 0 else 0.0

    return {
        "config_name": config_name,
        "flags": config_flags,
        "execution_accuracy": f"{exec_acc:.2f}%",
        "valid_sql_rate": f"{valid_rate:.2f}%",
        "avg_probes": f"{avg_probes:.2f}",
        "avg_latency_ms": f"{avg_latency:.2f}",
        "metrics_raw": {
            "execution_accuracy_pct": exec_acc,
            "valid_sql_rate_pct": valid_rate,
            "avg_probes": avg_probes,
            "avg_latency_ms": avg_latency,
            "total_items": total,
            "correct_items": correct_count,
            "valid_items": valid_sql_count,
        },
        "item_results": item_results
    }

def print_ablation_table(summary_list: list):
    """Prints the markdown ablation comparison table."""
    headers = ["Configuration", "Execution Accuracy", "Valid SQL", "Avg Probes", "Avg Latency (ms)"]
    print("\n" + "=" * 80)
    print("PHASE 14: ABLATION STUDY COMPARISON TABLE")
    print("=" * 80)
    print(f"| {headers[0]:<28} | {headers[1]:>18} | {headers[2]:>10} | {headers[3]:>10} | {headers[4]:>16} |")
    print(f"|{'-' * 30}|{'-' * 20}:|{'-' * 12}:|{'-' * 12}:|{'-' * 18}:|")
    for s in summary_list:
        print(f"| {s['config_name']:<28} | {s['execution_accuracy']:>18} | {s['valid_sql_rate']:>10} | {s['avg_probes']:>10} | {s['avg_latency_ms']:>16} |")
    print("=" * 80 + "\n")

def run_ablation_study(
    data_path: str = "data/evaluation.json",
    output_path: str = "data/ablation_results.json",
    limit: int = None,
    llm_client=None
):
    with open(data_path, "r") as f:
        dataset = json.load(f)

    if limit and limit > 0:
        dataset = dataset[:limit]

    ablation_summaries = []
    full_output = {
        "configurations": {},
        "table": []
    }

    for config_name, config_flags in CONFIGURATIONS.items():
        res = evaluate_configuration(config_name, config_flags, dataset, llm_client=llm_client)
        ablation_summaries.append(res)
        full_output["configurations"][config_name] = res
        full_output["table"].append({
            "Configuration": config_name,
            "Execution Accuracy": res["execution_accuracy"],
            "Valid SQL": res["valid_sql_rate"],
            "Avg Probes": res["avg_probes"],
            "Avg Latency (ms)": res["avg_latency_ms"]
        })

    print_ablation_table(ablation_summaries)

    with open(output_path, "w") as f:
        json.dump(full_output, f, indent=2)

    print(f"Detailed ablation results saved to: {output_path}")
    return full_output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run SDE-SQL Phase 14 Ablation Study")
    parser.add_argument("--data", default="data/evaluation.json", help="Path to evaluation dataset")
    parser.add_argument("--output", default="data/ablation_results.json", help="Path to output results file")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on number of questions to evaluate")
    parser.add_argument("--mock", action="store_true", help="Run ablation study using mock LLM (offline verification)")
    args = parser.parse_args()

    client = None
    if args.mock:
        from tests.test_ablation import MultiStepMockLLM
        client = MultiStepMockLLM()

    run_ablation_study(data_path=args.data, output_path=args.output, limit=args.limit, llm_client=client)
