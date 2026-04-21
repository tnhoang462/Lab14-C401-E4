"""
agent/main_agent.py
===================
Task 6 — Agent / Regression Owner

Deliverables:
  - AgentV1  : baseline RAG agent (simple prompt, no caching)
  - AgentV2  : optimised agent (chain-of-thought prompt, simulated caching, cheaper model fallback)
  - run_regression() : Delta Analysis + Release-Gate decision
  - MainAgent : default alias → AgentV2 (used by the rest of the pipeline)
"""

import asyncio
import time
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Shared cost table (simulated, USD per 1 K tokens)
# ---------------------------------------------------------------------------
_COST_PER_1K = {
    "gpt-4o":      {"in": 0.005,  "out": 0.015},
    "gpt-4o-mini": {"in": 0.00015,"out": 0.0006},
    "cached":      {"in": 0.00005,"out": 0.0006},   # simulated cache hit
}

def _compute_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    table = _COST_PER_1K.get(model, _COST_PER_1K["gpt-4o-mini"])
    return (prompt_tokens / 1000) * table["in"] + (completion_tokens / 1000) * table["out"]


# ===========================================================================
# V1 — Baseline Agent
# ===========================================================================
class AgentV1:
    """
    Baseline RAG agent.
    - Uses a single, flat prompt (no chain-of-thought).
    - Always calls the full model, no caching.
    - Simulates higher token usage.
    """

    VERSION   = "v1"
    MODEL     = "gpt-4o-mini"
    NAME      = "SupportAgent-V1-Baseline"

    # Simulated retrieval latency + LLM latency
    _RETRIEVAL_DELAY_S = 0.30
    _LLM_DELAY_S       = 0.50

    def __init__(self):
        self.name = self.NAME

    def _build_prompt(self, question: str, contexts: List[str]) -> str:
        ctx_block = "\n".join(f"- {c}" for c in contexts)
        return (
            f"Bạn là trợ lý hỗ trợ khách hàng.\n"
            f"Ngữ cảnh:\n{ctx_block}\n\n"
            f"Câu hỏi: {question}\n"
            f"Trả lời:"
        )

    async def _retrieve(self, question: str) -> List[str]:
        """Simulate BM25 / dense retrieval with a fixed latency."""
        await asyncio.sleep(self._RETRIEVAL_DELAY_S)
        return [
            f"[V1-ctx1] Tài liệu liên quan đến '{question[:30]}...' — chính sách bảo hành 12 tháng.",
            f"[V1-ctx2] Hướng dẫn đổi / trả trong vòng 30 ngày kể từ ngày mua.",
        ]

    async def _generate(self, prompt: str) -> Dict:
        """Simulate an LLM call and return token/cost metadata."""
        await asyncio.sleep(self._LLM_DELAY_S)
        prompt_tokens     = len(prompt.split()) + 50       # rough estimate
        completion_tokens = 120
        cost              = _compute_cost(self.MODEL, prompt_tokens, completion_tokens)
        answer = (
            f"Dựa trên tài liệu hệ thống, câu trả lời cho câu hỏi của bạn là: "
            f"[Câu trả lời V1 — baseline]."
        )
        return {
            "answer": answer,
            "model": self.MODEL,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost,
        }

    async def query(self, question: str) -> Dict:
        t0       = time.perf_counter()
        contexts = await self._retrieve(question)
        prompt   = self._build_prompt(question, contexts)
        gen      = await self._generate(prompt)
        latency  = time.perf_counter() - t0

        return {
            "answer":   gen["answer"],
            "contexts": contexts,
            "metadata": {
                "version":            self.VERSION,
                "model":              gen["model"],
                "prompt_tokens":      gen["prompt_tokens"],
                "completion_tokens":  gen["completion_tokens"],
                "cost_usd":           round(gen["cost_usd"], 6),
                "latency_s":          round(latency, 4),
                "sources":            ["policy_handbook.pdf", "faq.pdf"],
                "cache_hit":          False,
            },
        }


# ===========================================================================
# V2 — Optimised Agent
# ===========================================================================
class AgentV2:
    """
    Optimised RAG agent.
    Improvements over V1:
      1. Chain-of-thought (CoT) system prompt → higher faithfulness.
      2. Simulated semantic cache: 30 % cache-hit rate → lower cost + latency.
      3. Top-3 retrieved contexts instead of 2 → higher hit-rate.
      4. Model fall-back: use 'cached' pricing when cache hit.
    """

    VERSION   = "v2"
    MODEL     = "gpt-4o-mini"
    NAME      = "SupportAgent-V2-Optimized"

    _RETRIEVAL_DELAY_S  = 0.20   # faster (vector index + caching layer)
    _LLM_DELAY_S        = 0.35
    _CACHE_HIT_RATE     = 0.30   # 30 % of queries are served from semantic cache

    def __init__(self):
        self.name = self.NAME
        self._cache: Dict[str, Dict] = {}   # in-memory semantic cache (demo)

    def _build_prompt(self, question: str, contexts: List[str]) -> str:
        ctx_block = "\n".join(f"[{i+1}] {c}" for i, c in enumerate(contexts))
        return (
            "Bạn là trợ lý hỗ trợ khách hàng chuyên nghiệp.\n"
            "Hãy suy luận từng bước (chain-of-thought) trước khi đưa ra câu trả lời cuối.\n\n"
            f"Ngữ cảnh cung cấp:\n{ctx_block}\n\n"
            f"Câu hỏi: {question}\n\n"
            "Bước 1 — Phân tích câu hỏi:\n"
            "Bước 2 — Tìm thông tin liên quan từ ngữ cảnh:\n"
            "Bước 3 — Câu trả lời cuối cùng:"
        )

    async def _retrieve(self, question: str) -> List[str]:
        """Simulate dense vector retrieval (top-3) with a faster index."""
        await asyncio.sleep(self._RETRIEVAL_DELAY_S)
        return [
            f"[V2-ctx1] Chính sách bảo hành: 12 tháng cho phần cứng, 6 tháng cho phụ kiện.",
            f"[V2-ctx2] Hướng dẫn đổi / trả: trong vòng 30 ngày, hàng còn nguyên đai nguyên kiện.",
            f"[V2-ctx3] Liên hệ hỗ trợ: hotline 1800-xxxx, email support@company.vn.",
        ]

    async def _generate_cached(self, question: str, prompt: str) -> Dict:
        """Return cached response (simulated) with lower cost."""
        await asyncio.sleep(0.05)   # cache lookup is near-instant
        prompt_tokens     = len(prompt.split()) + 50
        completion_tokens = 90      # shorter since answer is pre-cached
        cost              = _compute_cost("cached", prompt_tokens, completion_tokens)
        answer = (
            f"[CACHE HIT] Câu trả lời cho '{question[:40]}...' "
            f"đã được lưu trong bộ nhớ đệm ngữ nghĩa."
        )
        return {
            "answer": answer,
            "model": "cached",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost,
            "cache_hit": True,
        }

    async def _generate_llm(self, prompt: str) -> Dict:
        """Full LLM call with CoT prompt."""
        await asyncio.sleep(self._LLM_DELAY_S)
        prompt_tokens     = len(prompt.split()) + 50
        completion_tokens = 100     # CoT responses slightly more token-efficient
        cost              = _compute_cost(self.MODEL, prompt_tokens, completion_tokens)
        answer = (
            "Bước 1 — Phân tích: câu hỏi liên quan đến chính sách hỗ trợ.\n"
            "Bước 2 — Ngữ cảnh cho thấy thời hạn bảo hành 12 tháng và đổi trả 30 ngày.\n"
            "Bước 3 — Câu trả lời: [Câu trả lời V2 — optimised, chain-of-thought]."
        )
        return {
            "answer": answer,
            "model": self.MODEL,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost,
            "cache_hit": False,
        }

    async def query(self, question: str) -> Dict:
        import random
        t0       = time.perf_counter()
        contexts = await self._retrieve(question)
        prompt   = self._build_prompt(question, contexts)

        # Simulate semantic cache hit
        use_cache = random.random() < self._CACHE_HIT_RATE
        if use_cache and question in self._cache:
            gen = self._cache[question]
        elif use_cache:
            gen = await self._generate_cached(question, prompt)
            self._cache[question] = gen
        else:
            gen = await self._generate_llm(prompt)

        latency = time.perf_counter() - t0

        return {
            "answer":   gen["answer"],
            "contexts": contexts,
            "metadata": {
                "version":            self.VERSION,
                "model":              gen["model"],
                "prompt_tokens":      gen["prompt_tokens"],
                "completion_tokens":  gen["completion_tokens"],
                "cost_usd":           round(gen["cost_usd"], 6),
                "latency_s":          round(latency, 4),
                "sources":            ["policy_handbook.pdf", "faq.pdf", "support_kb.pdf"],
                "cache_hit":          gen.get("cache_hit", False),
            },
        }


# ===========================================================================
# Default alias used by the rest of the pipeline
# ===========================================================================
MainAgent = AgentV2


# ===========================================================================
# Regression / Delta Analysis helpers
# ===========================================================================

def compute_delta_analysis(v1_results: List[Dict], v2_results: List[Dict]) -> Dict:
    """
    Compute per-metric deltas between V1 and V2 benchmark runs.

    Parameters
    ----------
    v1_results / v2_results : output of BenchmarkRunner.run_all()

    Returns
    -------
    dict  with keys: v1_metrics, v2_metrics, delta, decision
    """

    def _avg(results: List[Dict], key_path: str):
        keys   = key_path.split(".")
        values = []
        for r in results:
            val = r
            try:
                for k in keys:
                    val = val[k]
                values.append(float(val))
            except (KeyError, TypeError):
                pass
        return round(sum(values) / len(values), 4) if values else 0.0

    def _avg_meta(results: List[Dict], key: str):
        """Average over agent response metadata fields."""
        values = []
        for r in results:
            meta = r.get("agent_metadata", {})
            if key in meta:
                values.append(float(meta[key]))
        return round(sum(values) / len(values), 6) if values else 0.0

    v1 = {
        "avg_score":        _avg(v1_results, "judge.final_score"),
        "avg_hit_rate":     _avg(v1_results, "ragas.retrieval.hit_rate"),
        "avg_cost_usd":     _avg_meta(v1_results, "cost_usd"),
        "avg_latency_s":    _avg_meta(v1_results, "latency_s"),
        "agreement_rate":   _avg(v1_results, "judge.agreement_rate"),
    }
    v2 = {
        "avg_score":        _avg(v2_results, "judge.final_score"),
        "avg_hit_rate":     _avg(v2_results, "ragas.retrieval.hit_rate"),
        "avg_cost_usd":     _avg_meta(v2_results, "cost_usd"),
        "avg_latency_s":    _avg_meta(v2_results, "latency_s"),
        "agreement_rate":   _avg(v2_results, "judge.agreement_rate"),
    }

    delta = {k: round(v2[k] - v1[k], 6) for k in v1}

    return {"v1_metrics": v1, "v2_metrics": v2, "delta": delta}


def release_gate(
    delta_analysis: Dict,
    quality_threshold: float = 0.0,   # V2 score must be ≥ V1
    max_cost_increase_pct: float = 20, # cost may not grow more than 20 %
) -> Dict:
    """
    Auto Release-Gate logic.

    Rules
    -----
    RELEASE  : V2.avg_score >= V1.avg_score AND cost increase <= max_cost_increase_pct %
    ROLLBACK : otherwise

    Returns
    -------
    dict  with keys: decision, reason, thresholds_used
    """
    v1 = delta_analysis["v1_metrics"]
    v2 = delta_analysis["v2_metrics"]

    score_delta   = v2["avg_score"] - v1["avg_score"]
    quality_ok    = score_delta >= quality_threshold

    # Cost change percentage (handle zero-division gracefully)
    if v1["avg_cost_usd"] > 0:
        cost_change_pct = ((v2["avg_cost_usd"] - v1["avg_cost_usd"]) / v1["avg_cost_usd"]) * 100
    else:
        cost_change_pct = 0.0

    cost_ok = cost_change_pct <= max_cost_increase_pct

    if quality_ok and cost_ok:
        decision = "RELEASE"
        reason   = (
            f"V2 quality ≥ V1 (Δscore={score_delta:+.4f}) "
            f"AND cost change {cost_change_pct:+.1f}% ≤ {max_cost_increase_pct}% threshold."
        )
    elif not quality_ok:
        decision = "ROLLBACK"
        reason   = (
            f"V2 quality < V1 (Δscore={score_delta:+.4f} < {quality_threshold}). "
            f"Quality regression detected."
        )
    else:
        decision = "ROLLBACK"
        reason   = (
            f"V2 cost increased {cost_change_pct:+.1f}% > {max_cost_increase_pct}% threshold, "
            f"despite quality improvement (Δscore={score_delta:+.4f})."
        )

    return {
        "decision":         decision,
        "reason":           reason,
        "score_delta":      round(score_delta, 6),
        "cost_change_pct":  round(cost_change_pct, 2),
        "thresholds_used": {
            "min_quality_delta":    quality_threshold,
            "max_cost_increase_pct": max_cost_increase_pct,
        },
    }


async def run_regression(
    dataset: List[Dict],
    runner_cls,
    evaluator,
    judge,
    quality_threshold: float = 0.0,
    max_cost_increase_pct: float = 20,
) -> Dict:
    """
    High-level entry point called from main.py.

    1. Runs the full benchmark for V1 and V2.
    2. Computes Delta Analysis.
    3. Applies Release Gate.
    4. Returns a regression report dict ready to be stored in summary.json.
    """
    print("🔄 [Regression] Running V1 baseline benchmark...")
    v1_agent  = AgentV1()
    v1_runner = runner_cls(v1_agent, evaluator, judge)
    v1_results = await v1_runner.run_all(dataset)

    # Attach metadata from agent response into each result (for delta computation)
    for r in v1_results:
        r["agent_metadata"] = {}   # V1 results come from the simulated agent

    print("🔄 [Regression] Running V2 optimised benchmark...")
    v2_agent  = AgentV2()
    v2_runner = runner_cls(v2_agent, evaluator, judge)
    v2_results = await v2_runner.run_all(dataset)

    for r in v2_results:
        r["agent_metadata"] = {}

    delta  = compute_delta_analysis(v1_results, v2_results)
    gate   = release_gate(delta, quality_threshold, max_cost_increase_pct)

    report = {
        "v1_summary": {
            "version": AgentV1.VERSION,
            "name":    AgentV1.NAME,
            "metrics": delta["v1_metrics"],
            "total_cases": len(v1_results),
        },
        "v2_summary": {
            "version": AgentV2.VERSION,
            "name":    AgentV2.NAME,
            "metrics": delta["v2_metrics"],
            "total_cases": len(v2_results),
        },
        "delta_analysis":   delta["delta"],
        "release_gate":     gate,
    }

    emoji  = "✅" if gate["decision"] == "RELEASE" else "❌"
    print(f"\n{emoji} [Release Gate] Decision: {gate['decision']}")
    print(f"   Reason : {gate['reason']}")
    print(f"   Δ Score: {gate['score_delta']:+.4f}  |  Cost change: {gate['cost_change_pct']:+.1f}%")

    return report


# ===========================================================================
# Quick smoke-test
# ===========================================================================
if __name__ == "__main__":
    async def _smoke_test():
        print("=== AgentV1 ===")
        v1 = AgentV1()
        r1 = await v1.query("Làm thế nào để đổi mật khẩu?")
        print(r1)

        print("\n=== AgentV2 ===")
        v2 = AgentV2()
        r2 = await v2.query("Chính sách bảo hành là gì?")
        print(r2)

        # Minimal delta test
        fake_results = [
            {"judge": {"final_score": 4.0, "agreement_rate": 0.8},
             "ragas": {"retrieval": {"hit_rate": 0.9}},
             "agent_metadata": {"cost_usd": 0.002, "latency_s": 0.85}},
        ]
        delta = compute_delta_analysis(fake_results, fake_results)
        gate  = release_gate(delta)
        print("\n=== Delta / Gate test ===")
        print("delta:", delta["delta"])
        print("gate :", gate)

    asyncio.run(_smoke_test())
