"""
main.py — Pipeline Orchestrator  (Task #1)
==========================================
End-to-end flow:
  1. Load golden dataset (data/golden_set.jsonl)
  2. Run benchmark for AgentV1 (baseline) and AgentV2 (optimised) with
     the real RetrievalEvaluator (engine/retrieval_eval.py) and the real
     multi-judge LLMJudge (engine/llm_judge.py).
  3. Compute Delta Analysis + Release Gate (Task #6).
  4. Persist reports/summary.json + reports/benchmark_results.json
     for check_lab.py and the Failure Analysis report (Task #7).
"""

import asyncio
import json
import os
import time
from statistics import mean

from dotenv import load_dotenv

from agent.main_agent import (
    AgentV1,
    AgentV2,
    compute_delta_analysis,
    release_gate,
)
from engine.runner import BenchmarkRunner
from engine.retrieval_eval import RetrievalEvaluator
from engine.llm_judge import LLMJudge

load_dotenv()


GOLDEN_SET_PATH = "data/golden_set.jsonl"
REPORTS_DIR     = "reports"


def _load_dataset(path: str) -> list:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing {path} — run `python data/synthetic_gen.py` first."
        )
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _aggregate_metrics(results: list) -> dict:
    """Shape required by check_lab.py + downstream failure analysis."""
    n = max(1, len(results))

    avg_score      = mean(r["judge"].get("final_score", 0.0)          for r in results)
    hit_rate       = mean(r["ragas"]["retrieval"].get("hit_rate", 0.0) for r in results)
    mrr            = mean(r["ragas"]["retrieval"].get("mrr", 0.0)      for r in results)
    agreement_rate = mean(r["judge"].get("agreement_rate", 0.0)        for r in results)
    avg_cost       = mean(
        (r.get("agent_metadata") or {}).get("cost_usd", 0.0) for r in results
    )
    avg_latency    = mean(r.get("latency", 0.0) for r in results)
    pass_count     = sum(1 for r in results if r.get("status") == "PASS")
    fail_count     = sum(1 for r in results if r.get("status") == "FAIL")
    error_count    = sum(1 for r in results if r.get("status") == "ERROR")
    review_count   = sum(1 for r in results if r.get("status") == "NEEDS_REVIEW")

    return {
        "avg_score":      round(avg_score, 4),
        "hit_rate":       round(hit_rate, 4),
        "mrr":            round(mrr, 4),
        "agreement_rate": round(agreement_rate, 4),
        "avg_cost_usd":   round(avg_cost, 6),
        "avg_latency_s":  round(avg_latency, 4),
        "pass":           pass_count,
        "fail":           fail_count,
        "error":          error_count,
        "needs_review":   review_count,
        "total":          len(results),
    }


async def _run_version(agent, dataset, tag: str):
    print(f"\n🚀 Running benchmark for {tag} ({agent.NAME}) …")
    evaluator = RetrievalEvaluator(top_k=3)
    judge     = LLMJudge()
    runner    = BenchmarkRunner(agent, evaluator, judge)
    t0        = time.perf_counter()
    results   = await runner.run_all(dataset)
    elapsed   = time.perf_counter() - t0
    print(f"   ⏱  {tag} finished in {elapsed:.1f}s over {len(results)} cases")
    return results, elapsed


async def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)

    dataset = _load_dataset(GOLDEN_SET_PATH)
    if not dataset:
        print("❌ golden_set.jsonl is empty.")
        return
    print(f"📦 Loaded {len(dataset)} test cases from {GOLDEN_SET_PATH}")

    # ------------------------------------------------------------------
    # 1 — Run V1 baseline and V2 optimised
    # ------------------------------------------------------------------
    v1_results, v1_elapsed = await _run_version(AgentV1(), dataset, "V1_Baseline")
    v2_results, v2_elapsed = await _run_version(AgentV2(), dataset, "V2_Optimized")

    # ------------------------------------------------------------------
    # 2 — Delta Analysis + Release Gate (Task #6)
    # ------------------------------------------------------------------
    print("\n📊 Computing Delta Analysis (V1 vs V2) …")
    delta = compute_delta_analysis(v1_results, v2_results)
    gate  = release_gate(delta, quality_threshold=0.0, max_cost_increase_pct=20)

    regression_report = {
        "v1_summary": {
            "version":     AgentV1.VERSION,
            "name":        AgentV1.NAME,
            "total_cases": len(v1_results),
            "elapsed_s":   round(v1_elapsed, 2),
            "metrics":     delta["v1_metrics"],
        },
        "v2_summary": {
            "version":     AgentV2.VERSION,
            "name":        AgentV2.NAME,
            "total_cases": len(v2_results),
            "elapsed_s":   round(v2_elapsed, 2),
            "metrics":     delta["v2_metrics"],
        },
        "delta_analysis": delta["delta"],
        "release_gate":   gate,
    }

    # ------------------------------------------------------------------
    # 3 — Build primary summary (V2 is the candidate for release)
    # ------------------------------------------------------------------
    v2_metrics = _aggregate_metrics(v2_results)
    v1_metrics = _aggregate_metrics(v1_results)

    summary = {
        "metadata": {
            "version":   "Agent_V2_Optimized",
            "total":     len(v2_results),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dataset":   GOLDEN_SET_PATH,
        },
        "metrics":    v2_metrics,
        "v1_metrics": v1_metrics,
        "regression": regression_report,
    }

    # ------------------------------------------------------------------
    # 4 — Persist reports
    # ------------------------------------------------------------------
    with open(os.path.join(REPORTS_DIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Keep both V1 + V2 results for failure analysis (Task #7).
    combined = {
        "v1_results": v1_results,
        "v2_results": v2_results,
    }
    with open(os.path.join(REPORTS_DIR, "benchmark_results.json"), "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Reports saved → {REPORTS_DIR}/summary.json & benchmark_results.json")

    # ------------------------------------------------------------------
    # 5 — Release Gate verdict
    # ------------------------------------------------------------------
    print("\n" + "=" * 64)
    if gate["decision"] == "RELEASE":
        print("✅  RELEASE GATE: APPROVED — V2 is promoted to production.")
    else:
        print("❌  RELEASE GATE: ROLLBACK — Keeping V1 in production.")
    print(f"   Reason : {gate['reason']}")
    print(f"   ΔScore : {gate['score_delta']:+.4f}  |  ΔCost : {gate['cost_change_pct']:+.1f}%")
    print("=" * 64)


if __name__ == "__main__":
    asyncio.run(main())
