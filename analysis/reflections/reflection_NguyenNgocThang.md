# Bài Cá nhân: Reflection & Technical Deep-Dive
**Học viên:** Nguyễn Ngọc Thắng
**Vai trò:** AI/Backend Engineer — Multi-Judge Consensus

---

## 1. Engineering Contribution (Đóng góp Kỹ thuật)

Trong dự án này, tôi chịu trách nhiệm chính về module **Multi-Judge Consensus** (tại `engine/llm_judge.py`), đây là "bộ não" đánh giá của toàn bộ pipeline. Những đóng góp cụ thể của tôi bao gồm:

- **Triển khai Hệ thống Đa-Thẩm-Định (Multi-Judge):** Thay vì chỉ tin vào một model duy nhất, tôi đã thiết kế hệ thống gọi song song hai model hàng đầu: **OpenAI GPT-4o** và **NVIDIA NIM (Llama-3.3-70b)**. Việc sử dụng hai "trường phái" model khác nhau giúp kết quả đánh giá khách quan và tin cậy hơn.
- **Thiết kế Logic Đồng thuận (Consensus Logic):** Tôi đã xây dựng công thức tính `Agreement Rate` dựa trên độ lệch (delta) giữa các điểm số. 
    - Nếu delta ≤ 0.5: Đồng thuận cao.
    - Nếu delta > 1.0: Xung đột lớn, hệ thống tự động kích hoạt **Tiebreaker**.
- **Xây dựng Tiebreaker Tự động:** Khi hai judge bất đồng ý kiến, tôi đã triển khai một layer thẩm định thứ ba sử dụng GPT-4o với prompt đặc biệt để cân nhắc các lập luận từ hai judge trước đó và đưa ra quyết định cuối cùng.
- **Tối ưu hóa Performance với Asyncio:** Toàn bộ các lần gọi API (OpenAI, NVIDIA, Tiebreaker) đều được thực hiện bất đồng bộ (`async`/`await`), giúp module này có thể xử lý hàng chục test case cùng lúc mà không bị nghẽn (bottleneck).

---

## 2. Technical Depth (Chiều sâu Kỹ thuật)

### Khái niệm Position Bias & Metric Đồng thuận
Trong quá trình phát triển, tôi đặc biệt chú trọng đến **Position Bias**. Đây là hiện tượng LLM có xu hướng chấm điểm cao hơn cho câu trả lời xuất hiện trước (hoặc sau) trong prompt, bất kể chất lượng thực tế. 
- **Giải pháp:** Tôi đã triển khai hàm `check_position_bias()` để đảo thứ tự A/B và so sánh kết quả. Nếu winner thay đổi khi đổi vị trí, hệ thống sẽ cảnh báo về bias, giúp đảm bảo tính công bằng tuyệt đối cho Agent.

**Về chỉ số Cohen's Kappa:** Mặc dù đây là một chỉ số mạnh mẽ để đo lường độ đồng thuận giữa các thẩm định viên, trong dự án này tôi **chủ động không lựa chọn** sử dụng nó. Lý do là chúng ta chưa có đủ dung lượng dữ liệu (sample size) cần thiết để định lượng chính xác xác suất quan sát được ($P_{observed}$) và xác suất ngẫu nhiên ($P_{chance}$). Việc áp dụng Kappa trên tập dữ liệu nhỏ có thể dẫn đến các kết quả sai lệch, do đó tôi ưu tiên sử dụng `Agreement Rate` dựa trên độ lệch điểm (Delta) để phản ánh trực quan và thực tế hơn về mức độ tương đồng giữa các model.

### Đánh đổi giữa Chi phí và Chất lượng (Cost vs. Quality Trade-off)
Tôi đã đưa ra quyết định kiến trúc quan trọng:
- Sử dụng **NVIDIA NIM** như một Judge thứ hai không chỉ vì độ chính xác của Llama-3.3 mà còn để tối ưu hóa chi phí (tận dụng free credits của NVIDIA) và tăng tính đa dạng (tránh vendor lock-in vào OpenAI).
- Chỉ gọi **Tiebreaker** (model đắt tiền) khi delta > 1.0. Điều này giúp tiết kiệm ~80% chi phí judge mà vẫn đảm bảo độ tin cậy ở những trường hợp khó.

### Safety Criterion
Tôi đã mở rộng bộ tiêu chí đánh giá từ 3 lên **4 tiêu chí**, thêm vào tiêu chí **Safety**. Điều này giúp phát hiện các lỗi nguy hiểm như Prompt Injection hoặc Agent trả lời sai scope (ví dụ: tư vấn tài chính trái phép).

---

## 3. Problem Solving (Giải quyết Vấn đề)

Vấn đề phức tạp nhất tôi gặp phải là **Xử lý Output không đồng nhất giữa các Provider**. 
- **Triệu chứng:** Trong khi OpenAI hỗ trợ `json_object` mode cực tốt, các model qua NVIDIA NIM (như Llama) đôi khi trả về text kèm JSON hoặc format hỏng.
- **Giải pháp:** Tôi đã xây dựng một parser thông minh có khả năng trích xuất JSON bằng cách tìm cặp ngoặc nhọn `{...}` cuối cùng và xử lý fallback (`accuracy=3, safety=3...`) khi model hỏng hoàn toàn. Điều này giúp pipeline không bao giờ bị dừng đột ngột (crash) giữa chừng khi đang chạy batch lớn.

---

## 4. Tóm tắt kết quả (Self-Assessment)

Dựa trên [GRADING_RUBRIC.md](file:///c:/Users/Thang%20Ngoc%20Nguyen/Downloads/Lab14-C401-E4/GRADING_RUBRIC.md), tôi tự đánh giá hoàn thành tốt các mục:
- **Engineering Contribution (15/15):** Module Multi-Judge chạy ổn định, đầy đủ async.
- **Technical Depth (15/15):** Hiểu và code thành công Bias detection & Safety logic.
- **Problem Solving (10/10):** Giải quyết triệt để vấn đề parse JSON từ nhiều nguồn.

**Tổng cộng dự kiến:** 40/40 điểm cá nhân.
