# Bài Cá nhân: Reflection & Technical Deep-Dive
**Học viên:** Phạm Đỗ Ngọc Minh
**Vai trò:** AI/Backend Engineer — Agent / Regression Owner

---

## 1. Engineering Contribution (Đóng góp Kỹ thuật)

Trong dự án này, tôi chịu trách nhiệm chính về module **Agent & Regression Pipeline** (tại `agent/main_agent.py` và `main.py`), đây là lớp thực thi truy vấn và cơ chế kiểm soát chất lượng của toàn bộ hệ thống. Commit chính của tôi là `7c2f1ae feat: agent v1 and v2`. Những đóng góp cụ thể bao gồm:

- **Triển khai hai phiên bản Agent (V1 & V2):** Tôi thiết kế và cài đặt hai agent hoàn chỉnh với kiến trúc rõ ràng:
    - `AgentV1` — Baseline RAG agent: dùng prompt phẳng, không có cache, gọi model đầy đủ mỗi lần.
    - `AgentV2` — Optimised agent: tích hợp Chain-of-Thought prompt, semantic cache (30% hit rate), top-3 retrieval với title boost, và safety refusal gate.
- **Xây dựng Lexical Retriever nội bộ:** Tôi tự thiết kế bộ retriever lexical với Vietnamese-aware stopword filtering và overlap scoring có trọng số tiêu đề (`title_weight=2.0`), giúp tăng recall mà không cần hạ tầng vector database bên ngoài.
- **Triển khai Delta Analysis & Release Gate:** Tôi cài đặt hàm `compute_delta_analysis()` để so sánh 5 chỉ số giữa V1 và V2, và `release_gate()` để tự động quyết định `RELEASE` hoặc `ROLLBACK` dựa trên ngưỡng chất lượng và chi phí.
- **Tích hợp hoàn chỉnh vào `main.py`:** Tôi refactor `main.py` để sử dụng `run_regression()` từ `agent/main_agent.py`, đảm bảo toàn bộ pipeline chạy end-to-end và lưu kết quả vào `reports/summary.json` và `reports/benchmark_results.json`.

---

## 2. Technical Depth (Chiều sâu Kỹ thuật)

### Kiến trúc Agent V1 vs V2: Quyết định thiết kế có chủ đích

Tôi không chỉ tạo ra hai class agent đơn thuần mà còn thiết kế chúng để có sự khác biệt rõ ràng và có thể đo lường được:

| Chiều kỹ thuật | AgentV1 (Baseline) | AgentV2 (Optimised) |
|---|---|---|
| Prompt strategy | Flat prompt | Chain-of-Thought (3 bước) |
| Retrieval top-k | 2 docs | 3 docs |
| Title weight | 1.0 (không boost) | 2.0 (boost tiêu đề) |
| Semantic cache | Không | Có (30% hit rate, giảm 97% cost) |
| Safety gate | Không | Có (Prompt Injection regex) |
| Min score filter | 0.0 (lấy tất cả) | 0.5 (loại doc không liên quan) |

### Cost Model & Trade-off Chi phí

Tôi định nghĩa bảng giá token theo từng model (`_COST_PER_1K`) để mô phỏng thực tế:
- `gpt-4o-mini`: $0.00015/1K in, $0.0006/1K out
- `cached`: $0.00005/1K in (giảm 66% so với gpt-4o-mini)

Việc tích hợp cache trong V2 không chỉ giảm chi phí mà còn giảm latency từ ~0.80s xuống ~0.25s trên mỗi cache hit.

### Release Gate Logic: Quyết định tự động có lý luận

Tôi thiết kế `release_gate()` với hai điều kiện song song:
- **Quality gate:** `V2.avg_score ≥ V1.avg_score` (delta phải ≥ 0)
- **Cost gate:** Cost tăng không quá 20% so với V1

Hệ thống trả về lý do chi tiết thay vì chỉ trả về `True/False`, giúp team có thể audit quyết định. Đây là pattern phổ biến trong MLOps production deployment.

---

## 3. Problem Solving (Giải quyết Vấn đề)

Vấn đề phức tạp nhất tôi gặp phải là **thiết kế hàm `compute_delta_analysis()` để xử lý cấu trúc dict lồng nhau linh hoạt**.
- **Triệu chứng:** Kết quả từ `BenchmarkRunner.run_all()` có cấu trúc lồng nhiều tầng (`result["ragas"]["retrieval"]["hit_rate"]`), và code naive sẽ crash nếu một key bị thiếu trong bất kỳ test case nào.
- **Giải pháp:** Tôi cài đặt hàm `_avg(results, key_path)` dùng dotted path notation (`"ragas.retrieval.hit_rate"`) và bọc key traversal trong `try/except`, đảm bảo hàm gracefully skip các case bị lỗi thay vì crash toàn bộ regression report.

Vấn đề thứ hai là **Safety / Scope detection cho out-of-scope queries**:
- **Giải pháp:** Tôi xây dựng danh sách `_INJECTION_PATTERNS` gồm các regex pattern phát hiện Prompt Injection bằng tiếng Việt (ví dụ: `"quên tất cả"`, `"bỏ qua hướng dẫn"`, `"tiết lộ prompt"`). Khi phát hiện, agent từ chối và trả về câu trả lời chuẩn hóa, không để lộ nội dung system prompt.

---

## 4. Tóm tắt kết quả (Self-Assessment)

Dựa trên [GRADING_RUBRIC.md](../../GRADING_RUBRIC.md), tôi tự đánh giá hoàn thành tốt các mục:
- **Engineering Contribution (15/15):** Module Agent V1/V2 và Regression pipeline chạy ổn định, đầy đủ async, tích hợp End-to-End vào `main.py`.
- **Technical Depth (15/15):** Hiểu và cài đặt thành công Cost model, Cache strategy, CoT prompting, và Release Gate logic có lý luận rõ ràng.
- **Problem Solving (10/10):** Giải quyết triệt để vấn đề nested-key traversal và Safety gate cho adversarial queries.

**Tổng cộng dự kiến:** 40/40 điểm cá nhân.
