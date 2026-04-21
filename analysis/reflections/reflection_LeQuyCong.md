# Bài Cá nhân: Reflection & Technical Deep-Dive
**Học viên:** Lê Quý Công
**Vai trò:** Analyst / Failure Analysis

---

## 1. Engineering Contribution (Đóng góp Kỹ thuật)

Trong Lab Day 14, tôi phụ trách vai trò **#7 - Analyst / Failure Analysis**, với deliverable chính là file `analysis/failure_analysis.md`. Công việc của tôi không chỉ là viết báo cáo mô tả kết quả benchmark, mà là đọc toàn bộ pipeline để xác định **nguyên nhân gốc rễ** khiến Agent V2 bị rollback.

Những đóng góp chính của tôi gồm:

- **Đọc end-to-end pipeline** từ `data/synthetic_gen.py`, `data/source_corpus.py`, `agent/main_agent.py`, `engine/retrieval_eval.py`, `engine/runner.py`, `engine/llm_judge.py`, `main.py` để hiểu rõ dữ liệu đi như thế nào từ golden set đến benchmark report.
- **Phân tích trực tiếp trên output thật** từ `reports/summary.json` và `reports/benchmark_results.json`, thay vì viết failure analysis theo mẫu chung chung.
- **Phân cụm các case fail** theo ba chiều mà đề bài yêu cầu:
  - theo `error type/category`
  - theo `topic`
  - theo `question length`
- **Tách riêng strict fail và non-pass cases** (`FAIL + NEEDS_REVIEW`) để tránh bỏ sót các case từ chối đúng nhưng bị rule benchmark đánh dấu cần review.
- **Viết 5 Whys** cho bốn tầng nguyên nhân mà rubric yêu cầu:
  - Ingestion pipeline
  - Chunking strategy
  - Retrieval
  - Prompting
- **Đưa ra khuyến nghị cho người #6 build V2**, bám đúng các regression thật của V2 thay vì nêu giải pháp mơ hồ.

Deliverable cuối cùng của tôi là một báo cáo failure analysis có thể dùng trực tiếp cho vòng tối ưu agent tiếp theo, không chỉ để "nộp cho đủ file".

---

## 2. Technical Depth (Chiều sâu Kỹ thuật)

### Phân biệt triệu chứng và root cause
Điểm quan trọng nhất trong phần việc của tôi là phân biệt:

- **Triệu chứng:** agent trả lời sai
- **Nguyên nhân bề mặt:** retrieval lấy nhầm document đứng đầu
- **Nguyên nhân gốc rễ:** cách chunking, cách ranking, và cách prompting đang phối hợp với nhau không đúng

Ví dụ, nếu chỉ nhìn `hit_rate`, rất dễ kết luận retrieval đang ổn. Nhưng khi tôi đi sâu vào benchmark, tôi thấy có tới **5/9 case fail của V2 vẫn có `hit_rate = 1.0`**. Điều này cho thấy:

- hệ thống vẫn chạm được tài liệu đúng,
- nhưng tài liệu đúng không đứng top-1,
- và generator lại mặc định copy `contexts[0]`.

Từ đó tôi rút ra kết luận kỹ thuật quan trọng: **vấn đề chính của V2 không nằm ở recall retrieval, mà nằm ở ranking precision và answer selection policy**.

### Đọc benchmark bằng nhiều lớp tín hiệu
Tôi không chỉ đọc `status = FAIL/PASS`, mà còn kết hợp nhiều tín hiệu:

- `hit_rate`
- `mrr`
- `judge.final_score`
- `agreement_rate`
- `retrieved_ids`
- `agent_response`
- so sánh V1 và V2 trên cùng một case

Nhờ đó tôi phát hiện được một số regression quan trọng:

- `case_035` và `case_038`: V1 pass nhưng V2 fail dù doc đúng vẫn nằm trong top-k.
- `case_055`: V2 lấy đúng `doc_004` nhưng không phản bác tiền đề sai, cho thấy lỗi prompting kiểu **refute false premise**.
- nhóm `out_of_scope` và `goal_hijack`: V2 vẫn trả lời dựa trên doc gần nhất thay vì abstain, cho thấy **goal guard chưa đủ rộng**.

### Mapping 4 tầng nguyên nhân vào code thật
Một khó khăn kỹ thuật của vai trò analyst là đề bài yêu cầu chỉ rõ lỗi nằm ở:

- Ingestion pipeline
- Chunking strategy
- Retrieval
- Prompting

Trong khi code hiện tại **không có ingestion pipeline và chunking pipeline theo nghĩa production**. Mỗi document trong `source_corpus.py` thực tế đang đóng vai trò như một chunk lớn.

Nếu phân tích cẩu thả, tôi có thể viết 5 Whys theo template lý thuyết. Nhưng tôi chọn cách phân tích trung thực hơn:

- **Ingestion**: hiện mới là nạp dữ liệu thô với schema `id/title/topic/content`, chưa có section-level structure.
- **Chunking**: hiện tương đương `1 document = 1 chunk`, nên mất độ chính xác ở các câu factoid nằm cuối document.
- **Retrieval**: lexical overlap + title boost làm top-1 dễ lệch intent.
- **Prompting**: chưa có chính sách rõ cho `clarify`, `refuse`, `refute`.

Tôi đánh giá đây là phần thể hiện chiều sâu kỹ thuật rõ nhất trong phần việc của mình, vì nó biến một báo cáo "mô tả lỗi" thành một báo cáo "chỉ ra nơi cần sửa trong kiến trúc".

---

## 3. Problem Solving (Giải quyết Vấn đề)

Vấn đề lớn nhất tôi gặp phải là **không được phép phân tích hời hợt dựa trên score tổng**, vì score tổng dễ làm mình hiểu sai hệ thống.

### Vấn đề 1: Benchmark V2 fail nhưng hit rate vẫn cao
- **Triệu chứng:** nhìn summary thì V2 chỉ giảm điểm nhẹ so với V1, rất dễ nghĩ đây là nhiễu judge.
- **Cách xử lý:** tôi bóc riêng từng case `FAIL` và `NEEDS_REVIEW`, rồi so sánh `question`, `retrieved_ids`, `agent_response`, `judge reasoning`.
- **Kết quả:** phát hiện lỗi lặp lại là "retrieval hit nhưng trả lời sai", đặc biệt do lấy nhầm `contexts[0]`.

### Vấn đề 2: Đề bài yêu cầu 5 Whys ở 4 tầng nhưng code không có chunker/injestor rõ ràng
- **Triệu chứng:** nếu bám sát code, rất khó gán lỗi vào ingestion/chunking như trong rubric.
- **Cách xử lý:** tôi diễn giải failure analysis ở mức kiến trúc thực tế của repo, tức xem `source_corpus.py` là lớp ingestion thô và mỗi document là một chunk lớn.
- **Kết quả:** vẫn map được đúng 4 tầng nguyên nhân mà không phải "bịa" thêm thành phần không tồn tại.

### Vấn đề 3: Judge output có nhiễu
- **Triệu chứng:** nhiều case bị single-judge fallback do NVIDIA `429/502`, thậm chí có case như `case_055` có dấu hiệu điểm cuối không khớp trực giác.
- **Cách xử lý:** tôi không dựa mù quáng vào một score, mà ưu tiên pattern lặp lại trong retrieval và response.
- **Kết quả:** báo cáo cuối cùng tập trung vào lỗi kiến trúc, ít phụ thuộc vào nhiễu chấm điểm từng case.

Qua phần này, tôi học được rằng failure analysis tốt không phải là liệt kê lỗi, mà là:

1. gom các lỗi thành pattern,
2. chỉ ra pattern đó bắt nguồn từ tầng nào,
3. biến insight thành hành động cụ thể cho vòng build tiếp theo.

---

## 4. Tóm tắt kết quả (Self-Assessment)

Dựa trên phần việc thực tế tôi đã hoàn thành, tôi tự đánh giá:

- **Engineering Contribution:** Hoàn thành đầy đủ báo cáo `analysis/failure_analysis.md`, có đọc toàn pipeline và dùng benchmark thật để phân tích.
- **Technical Depth:** Xác định được sự khác nhau giữa retrieval recall, ranking precision, chunk granularity, và prompting policy; map chính xác vào 4 tầng root cause.
- **Problem Solving:** Xử lý được tình huống benchmark có nhiễu judge và codebase không có ingestion/chunking pipeline hoàn chỉnh nhưng vẫn viết được báo cáo có giá trị kỹ thuật.

Nếu tự chấm theo rubric cá nhân, tôi tin rằng phần việc của mình đáp ứng tốt các tiêu chí:

- **Engineering Contribution:** hoàn thành đúng deliverable, có giá trị thực tế cho team
- **Technical Depth:** phân tích đúng bản chất regression của V2
- **Problem Solving:** đưa ra khuyến nghị cụ thể, có thể chuyển ngay cho người #6 để build V2

Điều tôi thấy làm tốt nhất trong bài này là không dừng ở câu "agent trả lời sai", mà đi tới được câu "agent sai vì tầng nào trong pipeline đang thiết kế chưa đúng".
