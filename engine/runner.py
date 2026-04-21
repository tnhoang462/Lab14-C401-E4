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
        
        try:
            # 1. Gọi Agent
            response = await self.agent.query(test_case["question"])
            latency = time.perf_counter() - start_time
            
            # Cập nhật token used nếu có
            if "metadata" in response and "tokens_used" in response["metadata"]:
                self.total_tokens_used += response["metadata"]["tokens_used"]
            
            # 2. Chạy RAGAS/Retrieval metrics
            # Gọi evaluator.score dựa theo chuẩn API hiện tại của file retrieval_eval.py
            ragas_scores = await self.evaluator.score(test_case, response)
            
            # 3. Chạy Multi-Judge
            judge_result = await self.judge.evaluate_multi_judge(
                question=test_case["question"], 
                answer=response.get("answer", ""), 
                ground_truth=test_case.get("expected_answer", "")
            )
            
            # Tính toán passing status linh hoạt hơn
            hit_rate = ragas_scores.get("retrieval", {}).get("hit_rate", 0.0)
            final_score = judge_result.get("final_score", 0.0)
            
            if final_score >= 3.0 and hit_rate >= 1.0:
                status = "PASS"
            elif final_score >= 3.0 and hit_rate < 1.0:
                status = "NEEDS_REVIEW" # Trả lời đúng nhưng có thể là Hallucination/đã biết trước
            else:
                status = "FAIL"
                
            return {
                "test_case_id": test_case.get("id", "unknown"),
                "question": test_case["question"],
                "expected_answer": test_case.get("expected_answer", ""),
                "agent_response": response.get("answer", ""),
                "expected_retrieval_ids": test_case.get("expected_retrieval_ids", []),
                "retrieved_ids": response.get("retrieved_ids", []) or response.get("metadata", {}).get("retrieved_ids", []),
                "latency": round(latency, 2),
                "ragas": ragas_scores,
                "judge": judge_result,
                "status": status
            }
            
        except Exception as e:
            # Fallback nếu agent/judge/api bị lỗi timeout
            return {
                "test_case_id": test_case.get("id", "unknown"),
                "question": test_case["question"],
                "latency": round(time.perf_counter() - start_time, 2),
                "status": "ERROR",
                "error_message": str(e),
                "ragas": {"retrieval": {"hit_rate": 0.0, "mrr": 0.0}},
                "judge": {"final_score": 0.0, "agreement_rate": 0.0}
            }

    async def run_all(self, dataset: List[Dict], batch_size: int = 5) -> List[Dict]:
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
