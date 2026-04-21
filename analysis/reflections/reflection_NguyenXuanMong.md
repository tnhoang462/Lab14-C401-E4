# Báo cáo Cá nhân (Individual Reflection) - Lab Day 14
**Họ và tên:** Nguyễn Xuân Mong
**Vai trò trong nhóm:** AI Evaluation Engineer

---

## 1. Đóng góp Kỹ thuật (Engineering Contribution)
Trong dự án này, tôi chịu trách nhiệm chính trong việc xây dựng và tối ưu **Evaluation Engine**, cụ thể là file `engine/runner.py`. Những đóng góp nổi bật bao gồm:

- **Thiết kế Cơ chế Xử lý Bất đồng bộ (Async Batching):** Thay vì chạy từng bài test một cách tuần tự gây lãng phí thời gian, tôi đã cấu trúc lại Runner sử dụng `asyncio.gather`. Tôi triển khai kỹ thuật **Batching** (chia nhỏ thành các nhóm 5 test cases) kết hợp với `asyncio.sleep` giữa các batch để tránh bị Rate Limit từ phía OpenAI/NVIDIA API, qua đó giảm thời gian chạy benchmark (< 2 phút cho 50 cases).
- **Phân loại Trạng thái Thông minh (Status Logic):** Cải tiến logic "Pass/Fail" mặc định. Tôi đưa ra một trạng thái mới là `NEEDS_REVIEW` dành cho các case có điểm AI Judge cao (≥ 3) nhưng Hit Rate thấp (< 1.0). Logic này giúp nhóm tìm ra các trường hợp Agent bị "áo giác" (hallucination) — tức là trả lời đúng hên xui mặc dù không trích xuất được tài liệu đúng.
- **Theo dõi Chi phí (Cost & Token Tracking):** Tích hợp bộ đo tự động `total_tokens_used` để tổng hợp tổng chi phí của cả Pipeline, đáp ứng yêu cầu tối ưu hệ thống của bài Lab.
- **Robust Error Handling:** Bao bọc toàn bộ chu kỳ sống của một evaluation task bằng cấu trúc `try...except`. Nếu một API call bị timeout ở case thứ 49, hệ thống không bị crash toàn bộ mà ghi nhận test case đó là `"ERROR"`, bảo toàn kết quả của 48 cases còn lại.

---

## 2. Chiều sâu Kỹ thuật (Technical Depth)

Quá trình làm Lab giúp tôi hiểu sâu sắc các khái niệm lõi trong AI Engineering và Đánh giá Benchmark:

### A. Giải thích các Metric cốt lõi
- **MRR (Mean Reciprocal Rank):** Là chỉ số để đánh giá xem hệ thống Retrieval "ưu tiên" các kết quả đúng tốt như thế nào. Nếu tài liệu đúng nằm ngay top 1, điểm là `1/1 = 1.0`. Nếu nằm top 2 thì là `1/2 = 0.5`. MRR cao chứng tỏ VectorDB Search Index hoạt động rất chính xác, tìm ra đúng Context đẩy lên đầu cho LLM đọc.
- **Agreement Rate (Độ đồng thuận):** Khi sử dụng Multi-Judge (ví dụ GPT-4o-mini và NVIDIA Llama-3), Agreement Rate đo lường mức độ đồng ý giữa 2 giám khảo (giống như Cohen's Kappa). Nếu hai model thường xuyên chấm điểm cách xa nhau > 1 điểm, tức là prompt của Judge đang lỏng lẻo hoặc câu trả lời có tính đa nghĩa.
- **Position Bias:** Là hiện tượng LLM (Judge) thường có xu hướng thiên vị (cho điểm cao hơn) đoạn text nào xuất hiện trước trong prompt. Để khắc phục, ta có thể đổi chỗ `Response A` và `Response B` rồi cho LLM chấm lại để đối chiếu.

### B. Trade-off giữa Chi phí và Chất lượng (Cost vs Quality)
- Trong quá trình Eval, nếu ta dùng model xịn như `GPT-4o` để làm Judge cho toàn bộ 500 cases, kết quả sẽ rất chuẩn nhưng **chi phí cực lớn**. 
- **Giải pháp:** Sử dụng mô hình `GPT-4o-mini` kết hợp với model nguồn mở chất lượng cao trên `NVIDIA NIM` (ví dụ `Llama-3.3-70b-instruct`) để tối ưu chi phí. CHỈ KI KHI có sự bất đồng lớn (delta > 1.0) giữa hai model giá rẻ này (Agreement rate thấp), Pipeline mới triệu gọi model đắt tiền (GPT-4o) như một "Tie-breaker" (Người gỡ hòa).

---

## 3. Khả năng Giải quyết Vấn đề (Problem Solving)

**Vấn đề:** Trong quá trình chạy Benchmark nghiệm thu (Evaluation Runner), ban đầu nếu chạy đồng loạt 50 test cases qua Async, API bị nghẽn (Rate Limit 429) do request dồn dập cùng lúc vào NVIDIA NIM và OpenAI, dẫn đến crash toàn bộ script và bị mất trắng dữ liệu đã quét trước đó.

**Hướng giải quyết:**
1. **Áp dụng Error Handling chuẩn cấp Production:** Tôi bổ sung `try...except Exception as e:` gọn gàng trong thân hàm `run_single_test`. Không cần biết bên dưới LLM có văng lỗi timeout hay 429, hệ thống bắt buộc chạy trả về object JSON mang flag `"status": "ERROR"` chứa thông báo gốc thay vì chết (Crash) toàn bộ Asyncio Event Loop.
2. **Kỹ thuật Async Batch Processing:** Tôi chia nhỏ 50 cases thành từng nhóm (batch) với `batch_size = 5`. Tại vòng lặp `run_all`, nó sử dụng `asyncio.gather(*tasks)` để chạy 5 case đồng thời. Xong báo chờ 0.5s bằng `await asyncio.sleep(0.5)` làm cho hệ thống "thở" rồi đi tiếp đợt sau. 
3. **UX Cải thiện:** Tích hợp thêm `tqdm.asyncio` hiển thị ProgressBar để biết rõ tốc độ % mà không phải ngồi đoán mò trong màn hình Console kín chữ.

Kết quả là hệ thống chạy ổn định 100%, không phụ thuộc vào tình trạng giật lag của hạ tầng mạng, đánh ứng tuyệt đối yêu cầu về Performance của hạng mục chấm điểm Expert Level.
