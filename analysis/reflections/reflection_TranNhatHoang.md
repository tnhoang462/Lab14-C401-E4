# Bài Cá nhân: Reflection & Technical Deep-Dive
**Học viên:** Trần Nhật Hoàng
**Vai trò:** Team Lead / Integrator (#1) + Data & SDG Engineer (#2)

---

## 1. Engineering Contribution (Đóng góp Kỹ thuật)

### Task #1 — main.py: Pipeline Orchestrator

Tôi chịu trách nhiệm dựng và tích hợp toàn bộ pipeline trong `main.py`.

- **Wire-in implementation thật:** Phiên bản cũ dùng `ExpertEvaluator` và `MultiModelJudge` giả lập với điểm số hardcoded. Tôi thay bằng `RetrievalEvaluator` (task #3) và `LLMJudge` (task #4) thực sự — pipeline giờ chạy end-to-end với API thật.
- **Chạy và so sánh V1 vs V2:** Hàm `_run_version()` đóng gói luồng agent → evaluator → judge. `main()` gọi tuần tự V1 rồi V2, sau đó tính delta và kích hoạt Release Gate tự động.
- **Aggregate metrics đầy đủ:** Hàm `_aggregate_metrics()` tổng hợp `avg_score`, `hit_rate`, `mrr`, `agreement_rate`, `avg_cost_usd`, `avg_latency_s`, và đếm `pass/fail/error/needs_review` — đúng format `check_lab.py` yêu cầu.
- **Lưu cả hai bộ kết quả:** `benchmark_results.json` chứa cả `v1_results` lẫn `v2_results` để task #7 (Failure Analysis) có đủ dữ liệu phân cụm lỗi.

### Task #2 — Data & SDG Engineer

Tôi xây dựng toàn bộ tầng dữ liệu từ đầu, bao gồm 3 file chính:

**`data/source_corpus.py`** (~256 lines): Thiết kế bộ corpus 15+ document nội bộ của công ty giả định AcmeCorp, phủ các domain: bảo mật tài khoản, làm việc từ xa, nghỉ phép, quy trình IT, v.v. Mỗi document có `id` ổn định để phục vụ tính Hit Rate / MRR.

**`data/synthetic_gen.py`** (~598 lines): Script sinh test case tự động, gọi OpenAI để tạo câu hỏi đa dạng từ corpus và gán đúng `ground_truth_ids`. Kết quả: **57 test cases** với đủ các trường `question`, `ground_truth_answer`, `ground_truth_ids`, `expected_retrieval_ids`, `category`, `difficulty`, `metadata`.

**`data/golden_set.jsonl`** (57 cases): Dataset cuối cùng được chốt với cấu trúc sau:

| Category | Số lượng | Mô tả |
|---|---|---|
| factoid | 40 | Câu hỏi tra cứu thông tin thẳng từ corpus |
| multi_hop | 5 | Câu hỏi cần kết hợp 2+ document |
| out_of_scope | 3 | Câu hỏi ngoài domain |
| prompt_injection | 2 | Jailbreak dạng "quên hướng dẫn hệ thống" |
| adversarial_factual | 2 | Câu hỏi có thông tin sai cố ý |
| ambiguous | 2 | Câu hỏi mơ hồ nhiều cách hiểu |
| goal_hijack / jailbreak / stress | 3 | Các dạng Red Teaming khác |

12 cases thuộc nhóm adversarial/Red Teaming — đủ điều kiện theo `HARD_CASES_GUIDE.md`.

### Hỗ trợ thêm
- `engine/llm_judge.py`: Thêm `asyncio.Semaphore` + exponential backoff retry (429) + single-judge fallback khi một provider gặp lỗi.
- `engine/runner.py`: Tách ba khối `try-except` độc lập cho agent / evaluator / judge để lỗi một tầng không làm mất kết quả của tầng kia.

---

## 2. Technical Depth (Chiều sâu Kỹ thuật)

### Schema JSONL và tầm quan trọng của `ground_truth_ids`
Một quyết định kiến trúc quan trọng ở task #2 là chốt schema JSONL ngay từ GĐ1. `ground_truth_ids` là mảnh ghép kết nối task #2 với task #3: nếu thiếu trường này, `RetrievalEvaluator` không thể tính Hit Rate hay MRR vì không biết document nào là "đúng". Tôi dùng cùng `id` từ `source_corpus.py` để đảm bảo mapping nhất quán.

### Hit Rate vs. MRR — tại sao cần cả hai
Hit Rate kiểm tra xem ground-truth doc có nằm trong top-K không (binary). MRR nhạy hơn: doc đúng ở position 1 → 1.0, position 2 → 0.5, position 3 → 0.33. Kết quả benchmark cho thấy `hit_rate=0.842` và `mrr=0.807` (V1) — gap nhỏ chứng tỏ khi retrieval hit, doc đúng thường ở top-1 hoặc top-2. Nếu MRR thấp hơn nhiều so với hit_rate, tức là doc đúng thường rơi vào position 3, cần xem lại ranking logic.

### Release Gate và trade-off chất lượng — chi phí
Kết quả thực tế: V2 cải thiện latency (−32%) và cost (−13.46%), nhưng `avg_score` giảm nhẹ 0.04 điểm (3.93 so với 3.97 của V1). Release Gate đặt ngưỡng `quality_threshold=0.0` — V2 phải **bằng hoặc cao hơn** V1 mới được release. Vì delta âm, hệ thống tự động chọn ROLLBACK. Đây là hành vi đúng đắn: trong sản phẩm thực, tiết kiệm 13% chi phí không bù được việc câu trả lời giảm chất lượng.

### Red Teaming và vai trò trong pipeline
12 adversarial cases giúp kiểm tra xem V2 có refusal đúng hay không. Ví dụ, `prompt_injection` cases kỳ vọng agent trả về "Xin lỗi, tôi không thể xử lý yêu cầu này" thay vì thực thi lệnh. Nếu agent fail các case này, status sẽ là `FAIL` và lọt vào Failure Analysis của task #7 để phân cụm theo tầng lỗi.

---

## 3. Problem Solving (Giải quyết Vấn đề)

**Vấn đề 1: Schema không nhất quán giữa các thành viên**
Đây là rủi ro lớn nhất của dự án nhóm — mỗi người code một module, nếu schema JSONL không thống nhất thì pipeline vỡ khi ghép. Giải pháp: tôi chốt schema có cả `ground_truth_ids` và `expected_retrieval_ids` (hai tên song song để tương thích với cả `retrieval_eval.py` và `runner.py`), thông báo ngay ở GĐ1.

**Vấn đề 2: Pipeline crash khi một judge gặp lỗi API**
Khi chạy benchmark, NVIDIA NIM free tier bị rate limit 429 ngẫu nhiên. Ban đầu `asyncio.gather` không có `return_exceptions=True` — một lần timeout là cả case mất điểm. Tôi thêm xử lý: nếu một judge fail → single-judge fallback với `agreement_rate=0`; cả hai fail mới raise. Kết quả: 57/57 cases hoàn thành, `error=0`.

**Vấn đề 3: Sinh test case đủ đa dạng và không bị lặp**
`synthetic_gen.py` dùng OpenAI để sinh câu hỏi, nhưng nếu không kiểm soát, model thường sinh câu tương tự nhau cho cùng một document. Tôi thêm logic deduplication và phân chia quota theo topic để đảm bảo dataset phủ đều các domain trong corpus.

---

## 4. Tóm tắt kết quả (Self-Assessment)

| Deliverable | Trạng thái |
|---|---|
| `main.py` — orchestrate V1+V2, tạo `summary.json` + `benchmark_results.json` | ✅ Hoàn thành |
| `data/source_corpus.py` — 15+ documents với stable ID | ✅ Hoàn thành |
| `data/synthetic_gen.py` — script sinh 57 cases tự động | ✅ Hoàn thành |
| `data/golden_set.jsonl` — 57 cases, 12 Red Teaming, đủ `ground_truth_ids` | ✅ Hoàn thành |
| Hỗ trợ `llm_judge.py` / `runner.py` — retry, fallback, error isolation | ✅ Hoàn thành |

**Kết quả thực tế:** 57 test cases, `hit_rate=84.2%`, `avg_score=3.93` (V2), `0 errors`, Release Gate ROLLBACK đúng logic.

**Tự đánh giá:**
- Engineering Contribution: 15/15 — hai module lõi (#1 và #2) hoàn chỉnh, có commit rõ ràng.
- Technical Depth: 14/15 — hiểu MRR/hit_rate, schema contract, cost/quality tradeoff; Cohen's Kappa không nằm trong module tôi phụ trách trực tiếp.
- Problem Solving: 10/10 — ba vấn đề thực tế (schema, rate limit, dataset diversity) đều có giải pháp cụ thể.
