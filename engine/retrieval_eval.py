from typing import Any, Dict, List

class RetrievalEvaluator:
    def __init__(self, top_k: int = 3):
        self.top_k = max(1, top_k)

    @staticmethod
    def _as_id_list(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    def _extract_expected_ids(self, item: Dict[str, Any]) -> List[str]:
        # Direct field
        expected = self._as_id_list(item.get("expected_retrieval_ids"))
        if expected:
            return expected

        # Nested in test_case (if test_case is a dict)
        test_case = item.get("test_case")
        if isinstance(test_case, dict):
            expected = self._as_id_list(test_case.get("expected_retrieval_ids"))
            if expected:
                return expected

        # Nested in case
        case_obj = item.get("case")
        if isinstance(case_obj, dict):
            expected = self._as_id_list(case_obj.get("expected_retrieval_ids"))
            if expected:
                return expected

        return []

    def _extract_retrieved_ids(self, item: Dict[str, Any]) -> List[str]:
        # Direct field
        retrieved = self._as_id_list(item.get("retrieved_ids"))
        if retrieved:
            return retrieved

        # Nested in response
        response = item.get("response")
        if isinstance(response, dict):
            retrieved = self._as_id_list(response.get("retrieved_ids"))
            if retrieved:
                return retrieved

        # Nested in agent_response (if agent_response is dict)
        agent_response = item.get("agent_response")
        if isinstance(agent_response, dict):
            retrieved = self._as_id_list(agent_response.get("retrieved_ids"))
            if retrieved:
                return retrieved

        # Nested in item["response"]["metadata"] (some pipelines)
        if isinstance(response, dict):
            metadata = response.get("metadata")
            if isinstance(metadata, dict):
                retrieved = self._as_id_list(metadata.get("retrieved_ids"))
                if retrieved:
                    return retrieved

        return []

    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        if not expected_ids or not retrieved_ids:
            return 0.0
        top_retrieved = retrieved_ids[:max(1, top_k)]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        if not expected_ids or not retrieved_ids:
            return 0.0
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    async def score(self, test_case: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tương thích với BenchmarkRunner:
        runner gọi self.evaluator.score(test_case, response) cho từng mẫu.
        """
        expected_ids = self._extract_expected_ids(test_case)
        retrieved_ids = self._extract_retrieved_ids({"response": response})

        hit_rate = self.calculate_hit_rate(expected_ids, retrieved_ids, top_k=self.top_k)
        mrr = self.calculate_mrr(expected_ids, retrieved_ids)

        # Giữ shape gần giống RAGAS output để main.py có thể tổng hợp trực tiếp.
        return {
            "faithfulness": 0.0,
            "relevancy": 0.0,
            "retrieval": {
                "hit_rate": hit_rate,
                "mrr": mrr,
                "expected_ids": expected_ids,
                "retrieved_ids": retrieved_ids,
            },
        }

    async def evaluate_batch(self, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Chạy eval cho toàn bộ bộ dữ liệu.
        Dataset cần có trường 'expected_retrieval_ids' và Agent trả về 'retrieved_ids'.
        """
        total_hit_rate = 0.0
        total_mrr = 0.0
        total_cases = len(dataset)
        valid_cases = 0
        skipped_cases = 0
        per_case: List[Dict[str, Any]] = []

        for idx, sample in enumerate(dataset):
            expected_ids = self._extract_expected_ids(sample)
            retrieved_ids = self._extract_retrieved_ids(sample)

            if not expected_ids:
                skipped_cases += 1
                per_case.append(
                    {
                        "index": idx,
                        "status": "skipped",
                        "reason": "missing_expected_retrieval_ids",
                        "expected_ids": expected_ids,
                        "retrieved_ids": retrieved_ids,
                        "hit_rate": 0.0,
                        "mrr": 0.0,
                    }
                )
                continue

            valid_cases += 1
            hit = self.calculate_hit_rate(expected_ids, retrieved_ids, top_k=self.top_k)
            mrr = self.calculate_mrr(expected_ids, retrieved_ids)

            total_hit_rate += hit
            total_mrr += mrr

            per_case.append(
                {
                    "index": idx,
                    "status": "ok",
                    "expected_ids": expected_ids,
                    "retrieved_ids": retrieved_ids,
                    "hit_rate": hit,
                    "mrr": mrr,
                }
            )

        avg_hit_rate = total_hit_rate / valid_cases if valid_cases > 0 else 0.0
        avg_mrr = total_mrr / valid_cases if valid_cases > 0 else 0.0

        return {
            "avg_hit_rate": avg_hit_rate,
            "avg_mrr": avg_mrr,
            "top_k": self.top_k,
            "total_cases": total_cases,
            "valid_cases": valid_cases,
            "skipped_cases": skipped_cases,
            "per_case": per_case,
        }
    
if __name__ == "__main__":
    evaluator = RetrievalEvaluator()
    # Ví dụ test
    dataset = [
        {"expected_retrieval_ids": ["doc1", "doc2"], "retrieved_ids": ["doc3", "doc1", "doc4"]},
        # {"expected_retrieval_ids": ["doc5"], "retrieved_ids": ["doc6", "doc7"]},
        # {"expected_retrieval_ids": ["doc8"], "retrieved_ids": ["doc8", "doc9"]},
    ]
    import asyncio
    results = asyncio.run(evaluator.evaluate_batch(dataset))
    print(results)
