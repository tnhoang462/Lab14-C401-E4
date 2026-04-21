# 📋 Phân chia công việc — Lab Day 14 (Team 7 người)

> Map trực tiếp vào cấu trúc repo hiện tại và trọng số điểm trong `GRADING_RUBRIC.md`.

---

## 👥 Bảng phân công

| # | Vai trò | File/Module chính | Deliverable chính | Rubric liên quan |
|---|---|---|---|---|
| **1** | **Team Lead / Integrator** | `main.py`, `check_lab.py`, `reports/` | Orchestrate toàn pipeline, tạo `summary.json` + `benchmark_results.json`, đảm bảo `check_lab.py` pass trước khi nộp | Điều phối, ghép kết quả |
| **2** | **Data / SDG Engineer** | `data/synthetic_gen.py`, `data/HARD_CASES_GUIDE.md` | 50+ test cases có `ground_truth_ids`; ≥1 bộ Red Teaming phá được hệ thống | Dataset & SDG (10đ) |
| **3** | **Retrieval Evaluator** | `engine/retrieval_eval.py` | Hit Rate & MRR cho 50+ cases; viết đoạn phân tích "Retrieval quality → Answer quality" | Retrieval Eval (10đ) |
| **4** | **Multi-Judge Engineer** | `engine/llm_judge.py` | ≥2 Judge (vd GPT + Claude), tính Agreement Rate + Cohen's Kappa, logic xử lý xung đột (tie-breaker / voting) | Multi-Judge (15đ) — **tránh điểm liệt** |
| **5** | **Async / Perf Engineer** | `engine/runner.py` | Async runner < 2 phút cho 50 cases; log Token + USD cost per eval; đề xuất giảm 30% chi phí | Performance (10đ) |
| **6** | **Agent / Regression Owner** | `agent/main_agent.py`, logic Release Gate trong `main.py` | Ít nhất 2 version Agent (V1 baseline, V2 tối ưu); Delta analysis; auto-gate Release/Rollback theo ngưỡng | Regression Testing (10đ) |
| **7** | **Analyst / Failure Analysis** | `analysis/failure_analysis.md` | Failure Clustering + 5 Whys chỉ rõ lỗi ở tầng nào (Ingestion / Chunking / Retrieval / Prompting) | Failure Analysis (5đ) |

> **Mỗi người (bắt buộc):** tự viết `analysis/reflections/reflection_[Tên_SV].md` + có commit cá nhân rõ ràng trong module mình phụ trách (Engineering Contribution 15đ + Technical Depth 15đ + Problem Solving 10đ).

---

## ✅ Checklist deliverable theo từng vai trò

### #1 — Team Lead / Integrator
- [ ] Dựng khung `main.py` orchestrate: load golden set → retrieval eval → agent run → judge → report.
- [ ] Tạo folder `reports/` và đảm bảo sinh đúng `summary.json` + `benchmark_results.json`.
- [ ] Ghép kết quả Regression (V1 vs V2) vào `summary.json`.
- [ ] Chạy `python check_lab.py` pass trước nộp.
- [ ] Review PR/commit của 6 thành viên còn lại.

### #2 — Data / SDG Engineer
- [ ] Viết `data/synthetic_gen.py` sinh ≥ 50 cases vào `data/golden_set.jsonl`.
- [ ] Mỗi case có: `question`, `ground_truth_answer`, `ground_truth_ids` (list doc IDs).
- [ ] Bổ sung ≥ 10 case Red Teaming theo `HARD_CASES_GUIDE.md` (adversarial, out-of-scope, ambiguous).
- [ ] Chốt **schema JSONL** với cả team ngay đầu GĐ1.

### #3 — Retrieval Evaluator
- [ ] Implement `engine/retrieval_eval.py`: hàm `compute_hit_rate`, `compute_mrr`.
- [ ] Chạy eval trên toàn bộ golden set, xuất số liệu theo từng case.
- [ ] Viết 1 đoạn (~200 chữ) phân tích mối liên hệ Retrieval → Answer Quality vào `analysis/failure_analysis.md`.

### #4 — Multi-Judge Engineer  ⚠️ *tránh điểm liệt*
- [ ] Implement `engine/llm_judge.py` gọi ≥ 2 model Judge khác nhau (ví dụ `gpt-4o-mini` + `claude-haiku`).
- [ ] Tính **Agreement Rate** và **Cohen's Kappa** giữa các Judge.
- [ ] Logic xử lý xung đột: voting / tie-breaker / trung bình có trọng số.
- [ ] Chú ý **Position Bias** — shuffle thứ tự khi chấm.

### #5 — Async / Perf Engineer
- [ ] Refactor `engine/runner.py` dùng `asyncio.gather` / `aiohttp`.
- [ ] Target: < 2 phút cho 50 cases end-to-end.
- [ ] Log `prompt_tokens`, `completion_tokens`, `cost_usd` cho từng lần gọi.
- [ ] Viết đề xuất giảm 30% chi phí (vd: cache, judge rẻ hơn cho case dễ, batch API).

### #6 — Agent / Regression Owner
- [ ] Trong `agent/main_agent.py` tạo **2 version**: `agent_v1` (baseline) và `agent_v2` (tối ưu: prompt / chunking / retrieval khác).
- [ ] Logic **Delta Analysis**: so sánh score trung bình, cost, latency giữa V1 và V2.
- [ ] **Release Gate** auto: nếu V2 Quality ≥ V1 AND cost tăng ≤ X% → `release`, ngược lại `rollback`.
- [ ] Ghi kết quả vào `reports/summary.json` field `regression`.

### #7 — Analyst / Failure Analysis
- [ ] Sau khi có `benchmark_results.json`, phân cụm các case fail (by error type / topic / length).
- [ ] Viết **5 Whys** trong `analysis/failure_analysis.md` chỉ rõ root cause ở tầng nào:
  - Ingestion pipeline
  - Chunking strategy
  - Retrieval
  - Prompting
- [ ] Đưa ra ≥ 2 khuyến nghị cho người #6 để build V2.

---

## 📅 Lịch phối hợp 4 giai đoạn

| Giai đoạn | Thời lượng | Ai làm gì |
|---|---|---|
| **GĐ 1** | 45' | **#2** chạy trước → `golden_set.jsonl`. **#3, #4, #5, #6** đọc schema để chốt contract dữ liệu. **#1** setup repo/reports. |
| **GĐ 2** | 90' | **#3, #4, #5, #6** code song song các module. **#1** dựng khung `main.py` đợi plug-in các component. |
| **GĐ 3** | 60' | **#1** chạy full benchmark → **#7** phân cụm lỗi & 5 Whys. **#6** chạy V1 vs V2 regression. |
| **GĐ 4** | 45' | **#6** tune Agent theo insight của **#7**. Cả nhóm viết reflection cá nhân. **#1** chạy `check_lab.py` final. |

---

## ⚠️ Lưu ý điểm liệt & điểm cao

- **Điểm liệt (cap 30đ):** thiếu Multi-Judge (#4) hoặc thiếu Retrieval Metrics (#3) → assign cho 2 người mạnh nhất.
- **Ground Truth IDs** (#2) bắt buộc để (#3) tính được Hit Rate — **chốt schema JSONL ngay GĐ1**.
- **Red Teaming cases** (#2) là điều kiện để đạt full 10đ Dataset & SDG.
- **Cohen's Kappa + Position Bias** (#4) là keyword giám khảo sẽ hỏi → nhớ giải thích được.
- **< 2 phút cho 50 cases** (#5) là ngưỡng cứng của Performance 10đ.

---

## 📤 Submission Checklist (do #1 phụ trách chốt)

- [ ] Source code đầy đủ, không có `.env`.
- [ ] `reports/summary.json` + `reports/benchmark_results.json` đã sinh.
- [ ] `analysis/failure_analysis.md` hoàn chỉnh (5 Whys + clustering).
- [ ] Đủ 7 file `analysis/reflections/reflection_[Tên_SV].md`.
- [ ] `python check_lab.py` không báo lỗi.
- [ ] Git history có commit cá nhân rõ ràng của từng thành viên.
