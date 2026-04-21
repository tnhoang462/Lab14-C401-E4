import asyncio
import time
from typing import List, Dict, Any
from tqdm.asyncio import tqdm

class BenchmarkRunner:
    def __init__(self, agent: Any, evaluator: Any, judge: Any):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge
        
        # Track overall cost / tokens
        self.total_tokens_used = 0

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()

        # ── 1. Agent ──────────────────────────────────────────────────
        try:
            response = await self.agent.query(test_case["question"])
        except Exception as e:
            return {
                "test_case_id": test_case.get("id", "unknown"),
                "question": test_case["question"],
                "latency": round(time.perf_counter() - start_time, 2),
                "status": "ERROR",
                "error_message": f"agent_error: {e}",
                "ragas": {"retrieval": {"hit_rate": 0.0, "mrr": 0.0}},
                "judge": {"final_score": 0.0, "agreement_rate": 0.0},
                "category": test_case.get("category", "unknown"),
                "difficulty": test_case.get("difficulty", "unknown"),
                "topic": (test_case.get("metadata") or {}).get("topic", "unknown"),
                "agent_metadata": {},
            }

        latency = time.perf_counter() - start_time
        if "metadata" in response and "tokens_used" in response["metadata"]:
            self.total_tokens_used += response["metadata"]["tokens_used"]

        # ── 2. Retrieval eval (isolated — must not be wiped by judge failures) ──
        try:
            ragas_scores = await self.evaluator.score(test_case, response)
        except Exception as e:
            ragas_scores = {
                "retrieval": {"hit_rate": 0.0, "mrr": 0.0},
                "error": f"evaluator_error: {e}",
            }

        # ── 3. Multi-Judge (isolated — degrade gracefully on API errors) ──
        judge_error = None
        try:
            judge_result = await self.judge.evaluate_multi_judge(
                question=test_case["question"],
                answer=response.get("answer", ""),
                ground_truth=test_case.get("expected_answer", ""),
            )
        except Exception as e:
            judge_error = str(e)
            judge_result = {
                "final_score": 0.0,
                "agreement_rate": 0.0,
                "error": judge_error,
            }

        hit_rate    = ragas_scores.get("retrieval", {}).get("hit_rate", 0.0)
        final_score = judge_result.get("final_score", 0.0)

        if judge_error:
            status = "JUDGE_ERROR"     # retrieval still measured, but score unusable
        elif final_score >= 3.0 and hit_rate >= 1.0:
            status = "PASS"
        elif final_score >= 3.0 and hit_rate < 1.0:
            status = "NEEDS_REVIEW"    # answer looks right but retrieval didn't hit
        else:
            status = "FAIL"

        result = {
            "test_case_id": test_case.get("id", "unknown"),
            "question": test_case["question"],
            "expected_answer": test_case.get("expected_answer", ""),
            "agent_response": response.get("answer", ""),
            "expected_retrieval_ids": test_case.get("expected_retrieval_ids", []),
            "retrieved_ids": response.get("retrieved_ids", []) or response.get("metadata", {}).get("retrieved_ids", []),
            "latency": round(latency, 2),
            "ragas": ragas_scores,
            "judge": judge_result,
            "status": status,
            "category": test_case.get("category", "unknown"),
            "difficulty": test_case.get("difficulty", "unknown"),
            "topic": (test_case.get("metadata") or {}).get("topic", "unknown"),
            "agent_metadata": response.get("metadata", {}),
        }
        if judge_error:
            result["error_message"] = f"judge_error: {judge_error}"
        return result

    async def run_all(self, dataset: List[Dict], batch_size: int = 3) -> List[Dict]:
        """
        Chạy song song bằng asyncio.gather với giới hạn batch_size để tránh Rate Limit.
        Có thanh tiến trình (tqdm).
        """
        results = []
        
        # tqdm for async
        pbar = tqdm(total=len(dataset), desc="Running Benchmark")
        
        for i in range(0, len(dataset), batch_size):
            batch = dataset[i:i + batch_size]
            tasks = [self.run_single_test(case) for case in batch]
            
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            # Tạm nghỉ xíu để giảm Rate Limit (tuỳ chọn)
            await asyncio.sleep(0.5)
            
            pbar.update(len(batch))
            
        pbar.close()
        return results
