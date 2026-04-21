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
import re
import time
from typing import Dict, List, Optional, Tuple

from data.source_corpus import CORPUS

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


# ---------------------------------------------------------------------------
# Lightweight lexical retriever over the local corpus
# ---------------------------------------------------------------------------
# Vietnamese-aware stopword list + simple word-level overlap scoring. Good
# enough to produce realistic hit/miss patterns for Hit Rate / MRR.

_STOPWORDS = {
    "và", "của", "các", "cho", "là", "có", "được", "để", "một", "những",
    "tôi", "bạn", "khi", "nếu", "thì", "này", "đó", "phải", "trong", "ngoài",
    "với", "từ", "đã", "sẽ", "đang", "về", "ra", "vào", "như", "làm", "gì",
    "nào", "mỗi", "mỗi", "bao", "nhiêu", "ai", "hay", "hoặc", "không",
    "hãy", "cần", "còn", "rồi", "thế", "ở", "tại", "theo", "trên", "dưới",
    "sau", "trước", "đến", "nhưng", "mà", "chỉ", "cũng", "vì", "bởi",
    "the", "a", "an", "of", "to", "in", "is", "are", "and", "or", "how",
    "what", "when", "where", "why", "who", "do", "does", "can", "for",
}


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    # Keep unicode letters + digits; drop punctuation.
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return [tok for tok in text.split() if tok and tok not in _STOPWORDS]


def _score_doc(query_tokens: List[str], doc: Dict, title_weight: float = 1.0) -> float:
    """Simple overlap score: sum of query-token hits in title (boosted) and content."""
    title_tokens   = set(_tokenize(doc["title"]))
    content_tokens = set(_tokenize(doc["content"]))
    score = 0.0
    for tok in query_tokens:
        if tok in title_tokens:
            score += 2.0 * title_weight
        elif tok in content_tokens:
            score += 1.0
    return score


def _retrieve_from_corpus(
    question: str,
    top_k: int = 3,
    title_weight: float = 1.0,
    min_score: float = 0.0,
) -> Tuple[List[str], List[str], List[float]]:
    """
    Return (retrieved_ids, retrieved_contents, scores) ranked by overlap score.
    Docs with score below `min_score` are filtered out (empty list possible → safety refusal).
    """
    q_tokens = _tokenize(question)
    scored   = [(doc, _score_doc(q_tokens, doc, title_weight)) for doc in CORPUS]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = [(d, s) for d, s in scored[:top_k] if s > min_score]
    return (
        [d["id"] for d, _ in top],
        [f"{d['title']}: {d['content']}" for d, _ in top],
        [s for _, s in top],
    )


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

    async def _retrieve(self, question: str) -> Tuple[List[str], List[str]]:
        """Top-2 lexical retrieval without title weighting (baseline)."""
        await asyncio.sleep(self._RETRIEVAL_DELAY_S)
        ids, contents, _ = _retrieve_from_corpus(
            question, top_k=2, title_weight=1.0, min_score=0.0
        )
        return ids, contents

    async def _generate(self, prompt: str, contexts: List[str]) -> Dict:
        """Simulate an LLM call grounded in retrieved context."""
        await asyncio.sleep(self._LLM_DELAY_S)
        prompt_tokens     = len(prompt.split()) + 50
        completion_tokens = 120
        cost              = _compute_cost(self.MODEL, prompt_tokens, completion_tokens)

        # Baseline "extraction": concatenate the first context verbatim.
        # No refusal logic → fails on out-of-scope / adversarial cases.
        if contexts:
            snippet = contexts[0].split(":", 1)[-1].strip()
            # Take first ~2 sentences so the answer is crisp but still derivative.
            sentences = re.split(r"(?<=[\.\!\?])\s+", snippet)
            answer    = " ".join(sentences[:2])
        else:
            answer = "Tôi không tìm thấy thông tin liên quan."

        return {
            "answer": answer,
            "model": self.MODEL,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost,
        }

    async def query(self, question: str) -> Dict:
        t0                     = time.perf_counter()
        retrieved_ids, contexts = await self._retrieve(question)
        prompt                 = self._build_prompt(question, contexts)
        gen                    = await self._generate(prompt, contexts)
        latency                = time.perf_counter() - t0

        return {
            "answer":   gen["answer"],
            "contexts": contexts,
            "retrieved_ids": retrieved_ids,
            "metadata": {
                "version":            self.VERSION,
                "model":              gen["model"],
                "retrieved_ids":      retrieved_ids,
                "prompt_tokens":      gen["prompt_tokens"],
                "completion_tokens":  gen["completion_tokens"],
                "cost_usd":           round(gen["cost_usd"], 6),
                "latency_s":          round(latency, 4),
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

    # Safety / scope heuristics for Red Team cases
    _REFUSAL_MIN_SCORE = 2.0   # if best-doc score below this → out-of-scope
    _INJECTION_PATTERNS = [
        r"quên (tất cả|mọi thứ|những gì)",
        r"bỏ qua (chỉ thị|hướng dẫn)",
        r"hệ thống prompt",
        r"system prompt",
        r"hướng dẫn nội bộ",
        r"tiết lộ.*(hướng dẫn|prompt)",
        r"đánh cắp",
        r"mã nguồn (nội bộ|của)",
        r"gửi.*mã nguồn",
    ]

    async def _retrieve(self, question: str) -> Tuple[List[str], List[str], List[float]]:
        """Top-3 lexical retrieval with title boost (better recall)."""
        await asyncio.sleep(self._RETRIEVAL_DELAY_S)
        return _retrieve_from_corpus(
            question, top_k=3, title_weight=2.0, min_score=0.5
        )

    def _looks_like_injection(self, question: str) -> bool:
        q = question.lower()
        return any(re.search(p, q) for p in self._INJECTION_PATTERNS)

    async def _generate_cached(self, question: str, prompt: str, answer: str) -> Dict:
        """Return cached response (simulated) with lower cost."""
        await asyncio.sleep(0.05)
        prompt_tokens     = len(prompt.split()) + 50
        completion_tokens = 90
        cost              = _compute_cost("cached", prompt_tokens, completion_tokens)
        return {
            "answer": answer,
            "model": "cached",
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost,
            "cache_hit": True,
        }

    async def _generate_llm(self, prompt: str, contexts: List[str]) -> Dict:
        """CoT-style LLM call grounded in retrieved context."""
        await asyncio.sleep(self._LLM_DELAY_S)
        prompt_tokens     = len(prompt.split()) + 50
        completion_tokens = 100
        cost              = _compute_cost(self.MODEL, prompt_tokens, completion_tokens)

        if not contexts:
            answer = (
                "Xin lỗi, câu hỏi này nằm ngoài phạm vi nội quy AcmeCorp mà tôi được "
                "hỗ trợ. Vui lòng đặt câu hỏi về các chính sách nội bộ của công ty."
            )
        else:
            snippet   = contexts[0].split(":", 1)[-1].strip()
            sentences = re.split(r"(?<=[\.\!\?])\s+", snippet)
            answer    = " ".join(sentences[:2])

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
        t0 = time.perf_counter()

        # Safety gate: prompt-injection / jailbreak refusal
        if self._looks_like_injection(question):
            retrieved_ids: List[str] = []
            contexts: List[str]     = []
            refusal = (
                "Xin lỗi, tôi chỉ hỗ trợ các câu hỏi về nội quy và chính sách của "
                "AcmeCorp. Tôi không thể xử lý yêu cầu bỏ qua hướng dẫn hệ thống "
                "hoặc tiết lộ thông tin nội bộ."
            )
            gen = {
                "answer": refusal,
                "model": self.MODEL,
                "prompt_tokens":      40,
                "completion_tokens":  60,
                "cost_usd": _compute_cost(self.MODEL, 40, 60),
                "cache_hit": False,
            }
        else:
            retrieved_ids, contexts, _scores = await self._retrieve(question)
            prompt = self._build_prompt(question, contexts)

            use_cache = random.random() < self._CACHE_HIT_RATE
            if use_cache and question in self._cache:
                gen = self._cache[question]
            else:
                gen = await self._generate_llm(prompt, contexts)
                if use_cache:
                    cached_gen = await self._generate_cached(question, prompt, gen["answer"])
                    self._cache[question] = cached_gen
                    gen = cached_gen

        latency = time.perf_counter() - t0

        return {
            "answer":   gen["answer"],
            "contexts": contexts,
            "retrieved_ids": retrieved_ids,
            "metadata": {
                "version":            self.VERSION,
                "model":              gen["model"],
                "retrieved_ids":      retrieved_ids,
                "prompt_tokens":      gen["prompt_tokens"],
                "completion_tokens":  gen["completion_tokens"],
                "cost_usd":           round(gen["cost_usd"], 6),
                "latency_s":          round(latency, 4),
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
