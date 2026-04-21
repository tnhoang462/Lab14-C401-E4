"""
main.py — Pipeline Orchestrator
================================
Runs the full benchmark pipeline:
  1. Load golden dataset
  2. Run benchmark (V2 agent, used by evaluator + judge)
  3. Run Regression: V1 vs V2 Delta Analysis + Release Gate  ← Task 6
  4. Persist reports/summary.json + reports/benchmark_results.json
"""

import asyncio
import json
import os
import time

from engine.runner import BenchmarkRunner
from agent.main_agent import (
    AgentV1,
    AgentV2,
    MainAgent,
    run_regression,
)


# ---------------------------------------------------------------------------
# Simulated expert components
# (replaced by real implementations from tasks #3 and #4 when integrated)
# ---------------------------------------------------------------------------

class ExpertEvaluator:
    """Simulates RAGAS-style retrieval + faithfulness evaluation."""

    async def score(self, case: dict, resp: dict) -> dict:
        # In the real pipeline this calls retrieval_eval.py metrics
        hit_rate = 1.0 if resp.get("contexts") else 0.0
        mrr      = 0.75
        return {
            "faithfulness": 0.90,
            "relevancy":    0.85,
            "retrieval":    {"hit_rate": hit_rate, "mrr": mrr},
        }


class MultiModelJudge:
    """Simulates ≥2-model judge consensus (GPT + Claude)."""

    async def evaluate_multi_judge(self, question: str, answer: str, ground_truth: str) -> dict:
        # In the real pipeline this calls llm_judge.py
        return {
            "final_score":    4.5,
            "agreement_rate": 0.80,
            "cohen_kappa":    0.72,
            "reasoning":      "Both judges agree: the answer is accurate and relevant.",
        }


# ---------------------------------------------------------------------------
# Benchmark runner (single agent version, used for the primary V2 report)
# ---------------------------------------------------------------------------

async def run_benchmark_with_results(agent, version_tag: str):
    print(f"🚀 Running benchmark for {version_tag} …")

    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Missing data/golden_set.jsonl — run 'python data/synthetic_gen.py' first.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ data/golden_set.jsonl is empty — add at least 1 test case.")
        return None, None

    evaluator = ExpertEvaluator()
    judge     = MultiModelJudge()
    runner    = BenchmarkRunner(agent, evaluator, judge)
    results   = await runner.run_all(dataset)

    total   = len(results)
    summary = {
        "metadata": {
            "version":   version_tag,
            "total":     total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            "avg_score":      sum(r["judge"]["final_score"]          for r in results) / total,
            "hit_rate":       sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total,
            "agreement_rate": sum(r["judge"]["agreement_rate"]        for r in results) / total,
        },
    }
    return results, summary


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def main():
    os.makedirs("reports", exist_ok=True)

    # ------------------------------------------------------------------
    # 1 — Primary benchmark (V2 agent, reported as main results)
    # ------------------------------------------------------------------
    v2_agent              = AgentV2()
    v2_results, v2_summary = await run_benchmark_with_results(v2_agent, "Agent_V2_Optimized")

    if not v2_results or not v2_summary:
        print("❌ Benchmark failed. Check data/golden_set.jsonl.")
        return

    # ------------------------------------------------------------------
    # 2 — Regression: V1 vs V2 Delta Analysis + Release Gate  (Task 6)
    # ------------------------------------------------------------------
    print("\n📊 Running Regression Analysis (V1 vs V2) …")

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    regression_report = await run_regression(
        dataset              = dataset,
        runner_cls           = BenchmarkRunner,
        evaluator            = ExpertEvaluator(),
        judge                = MultiModelJudge(),
        quality_threshold    = 0.0,    # V2 score must be ≥ V1
        max_cost_increase_pct= 20,     # cost may not grow more than 20 %
    )

    # ------------------------------------------------------------------
    # 3 — Persist reports
    # ------------------------------------------------------------------
    v2_summary["regression"] = regression_report

    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)

    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    print("\n✅ Reports saved to reports/summary.json & reports/benchmark_results.json")

    # ------------------------------------------------------------------
    # 4 — Print Release Gate decision
    # ------------------------------------------------------------------
    gate_decision = regression_report["release_gate"]["decision"]
    gate_reason   = regression_report["release_gate"]["reason"]

    print("\n" + "=" * 60)
    if gate_decision == "RELEASE":
        print("✅  RELEASE GATE: APPROVED — V2 is promoted to production.")
    else:
        print("❌  RELEASE GATE: ROLLBACK — Keeping V1 in production.")
    print(f"   Reason : {gate_reason}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
