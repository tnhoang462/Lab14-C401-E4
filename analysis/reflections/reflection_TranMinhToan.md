# Individual Reflection

Trần Minh Toàn - 2A202600297

## 1. Engineering Contribution (15 diem)

### Module chinh da dong gop
- Hoan thien module danh gia Retrieval trong [engine/retrieval_eval.py](../../engine/retrieval_eval.py).
- Dam bao tuong thich interface voi runner trong [engine/runner.py](../../engine/runner.py) thong qua ham async `score(test_case, response)`.
- Chuan hoa viec trich xuat du lieu expected va retrieved tu nhieu format schema khac nhau.

### Cong viec ky thuat cu the
- Trien khai va kiem chung cong thuc Hit Rate@k va RR/MRR cho tung test case.
- Bo sung logic xu ly du lieu thieu de tranh vo pipeline:
  - Neu thieu expected_retrieval_ids thi danh dau skipped.
  - Neu thieu retrieved_ids thi van tinh metric voi gia tri 0 de minh bach.
- Mo rong output danh gia theo batch:
  - avg_hit_rate, avg_mrr
  - total_cases, valid_cases, skipped_cases
  - per_case de debug theo tung mau
- Kiem thu nhanh bang du lieu mau va xac nhan module chay on dinh.

### Gia tri mang lai cho he thong
- Metric Retrieval khong con la placeholder, co the dung de benchmark that.
- Runner co the goi evaluator thong nhat cho tung case, giam rui ro loi tich hop.
- Co kha nang truy vet loi retrieval theo tung case de phuc vu Failure Analysis.

## 2. Technical Depth (15 diem)

### MRR
- RR cho mot cau hoi:
  - Neu tai lieu dung dau tien nam o vi tri r (1-indexed), RR = 1/r.
  - Neu khong tim thay tai lieu dung, RR = 0.
- MRR la trung binh RR tren toan bo tap test.
- Y nghia: MRR thuong phat manh truong hop tai lieu dung xuat hien muon trong ranking.

### Cohen's Kappa
- Do muc do dong thuan giua cac judge sau khi loai bo kha nang dong thuan ngau nhien.
- Cong dung trong he thong Multi-Judge:
  - Khong chi nhin agreement rate don thuan.
  - Danh gia do tin cay that su cua qua trinh cham diem.

### Position Bias
- Judge co the thien vi vi tri A/B thay vi noi dung.
- Cach xu ly:
  - Dao vi tri dap an A/B va cham lai.
  - So sanh do lech diem truoc/sau dao vi tri.
  - Neu do lech lon, can hieu chinh prompt judge hoac bo sung co che calibration.

### Trade-off Chat luong va Chi phi
- Tang top_k thuong giup tang kha nang hit nhung co the tang latency va token cost.
- Danh gia retrieval dung cach giup giam hallucination o generation ma khong can tang model size qua muc.
- Huong toi toi uu can bang:
  - Chat luong retrieval du cao de nang answer quality.
  - Chi phi va toc do dap ung muc tieu benchmark.

## 3. Problem Solving (10 diem)

### Van de 1: Khong khop interface giua Runner va Evaluator
- Trieu chung: Runner goi `score(test_case, response)` nhung evaluator ban dau chi co `evaluate_batch`.
- Cach xu ly: Bo sung ham `score` async de tra metric retrieval theo tung case, giu dung contract cua pipeline.

### Van de 2: Mismatch schema du lieu
- Trieu chung: expected_ids/retrieved_ids co the nam o root hoac nested object, gay tinh sai metric.
- Cach xu ly: Viet bo ham trich xuat id linh hoat, chuan hoa ve list string truoc khi tinh.

### Van de 3: Diem retrieval thap gia tao do dat ten ID khong dong bo
- Trieu chung: Golden set dung dang `doc_id_1`, trong khi output retrieval co the dang `doc_1`.
- Cach xu ly: Thong nhat quy uoc dat ten ID giua dataset va output cua agent; dung per_case de phat hien nhanh mismatch.

### Van de 4: Kho debug neu chi co diem trung binh
- Trieu chung: Khong biet case nao loi retrieval.
- Cach xu ly: Tra them `per_case`, `valid_cases`, `skipped_cases` de nhin duoc loi theo tung test case.

## 4. Ket qua va bai hoc rut ra

### Ket qua
- Retrieval evaluator da san sang cho benchmark that thay vi demo.
- He thong co the tong hop metric retrieval theo case va theo batch.
- Nen tang de phan tich lien he giua Retrieval Quality va Answer Quality.

### Bai hoc
- Can chot schema du lieu som de tranh vo contract giua module.
- Metric trung binh chi la lop tong quat; du lieu per-case moi giup debug hieu qua.
- Danh gia retrieval la dieu kien can de nang chat luong generation ben vung.

## 5. Ke hoach cai tien tiep theo

- Bo sung cac metric retrieval nang cao: Recall@k, nDCG.
- Them canh bao tu dong khi skipped_cases vuot nguong.
- Gan retrieval evaluator vao summary/report theo regressions V1 vs V2 de theo doi phat trien dai han.
