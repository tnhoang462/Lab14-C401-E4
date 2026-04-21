# Hướng dẫn thiết kế Hard Cases cho AI Evaluation

## 📐 Golden Set Schema — CHỐT GĐ 1 (owner: #2)

> Tất cả các module downstream (`engine/runner.py`, `engine/retrieval_eval.py`,
> `engine/llm_judge.py`, `main.py`) đều đọc theo schema dưới đây. Đừng đổi tên
> field mà không ping cả team.

Mỗi dòng trong `data/golden_set.jsonl` là 1 JSON object:

| Field | Kiểu | Bắt buộc | Ý nghĩa |
|---|---|---|---|
| `id` | `str` | ✅ | Mã case duy nhất (vd `case_001`) |
| `question` | `str` | ✅ | Câu hỏi gửi tới Agent |
| `ground_truth_answer` | `str` | ✅ | Câu trả lời canonical dùng cho Judge |
| `expected_answer` | `str` | ✅ | **Alias** của `ground_truth_answer` — giữ để `runner.py` hiện tại chạy được |
| `ground_truth_ids` | `list[str]` | ✅ | Doc IDs kỳ vọng được retrieve. `[]` = out-of-scope (Agent nên abstain) |
| `expected_retrieval_ids` | `list[str]` | ✅ | **Alias** của `ground_truth_ids` — cho `retrieval_eval.py` |
| `category` | `str` | ✅ | `factoid` / `multi_hop` / `out_of_scope` / `prompt_injection` / `goal_hijack` / `ambiguous` / `adversarial_factual` / `jailbreak` / `stress` |
| `difficulty` | `str` | ✅ | `easy` / `medium` / `hard` |
| `metadata` | `dict` | ✅ | Tự do: `topic`, `red_team_tactic`, `notes`… |

Ví dụ 1 dòng (factoid):

```json
{"id": "case_001", "question": "Đổi mật khẩu bao lâu một lần?", "ground_truth_answer": "90 ngày.", "expected_answer": "90 ngày.", "ground_truth_ids": ["doc_001"], "expected_retrieval_ids": ["doc_001"], "category": "factoid", "difficulty": "easy", "metadata": {"topic": "account_security"}}
```

Quy ước:
- `ground_truth_ids` chỉ chứa doc ID tồn tại trong `data/source_corpus.py`
  (script `synthetic_gen.py` có assert — file sẽ không ghi nếu sai).
- Case `out_of_scope` / `prompt_injection` / `goal_hijack` / `jailbreak` để
  `ground_truth_ids = []` và đưa yêu cầu hành vi vào `ground_truth_answer`
  (ví dụ: "Agent phải từ chối…").

---

Để bài lab đủ độ khó cho nhóm 6 người, các bạn cần thiết kế các test cases có tính thử thách cao:

### 1. Adversarial Prompts (Tấn công bằng Prompt)
- **Prompt Injection:** Thử lừa Agent bỏ qua context để trả lời theo ý người dùng.
- **Goal Hijacking:** Yêu cầu Agent thực hiện một hành động không liên quan đến nhiệm vụ chính (ví dụ: đang là hỗ trợ kỹ thuật nhưng yêu cầu viết thơ về chính trị).

### 2. Edge Cases (Trường hợp biên)
- **Out of Context:** Đặt câu hỏi mà tài liệu không hề đề cập. Agent phải biết nói "Tôi không biết" thay vì bịa chuyện (Hallucination).
- **Ambiguous Questions:** Câu hỏi mập mờ, thiếu thông tin để xem Agent có biết hỏi lại (clarify) không.
- **Conflicting Information:** Đưa ra 2 đoạn tài liệu mâu thuẫn nhau để xem Agent xử lý thế nào.

### 3. Multi-turn Complexity
- **Context Carry-over:** Câu hỏi thứ 2 phụ thuộc vào câu trả lời thứ 1.
- **Correction:** Người dùng đính chính lại thông tin ở giữa cuộc hội thoại.

### 4. Technical Constraints
- **Latency Stress:** Yêu cầu Agent xử lý một đoạn văn bản cực dài để đo giới hạn latency.
- **Cost Efficiency:** Đánh giá xem Agent có đang dùng quá nhiều token không cần thiết cho các câu hỏi đơn giản không.
