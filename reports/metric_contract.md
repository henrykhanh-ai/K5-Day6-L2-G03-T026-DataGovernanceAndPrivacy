# Metric contract (khai báo bắt buộc — chốt ở phút 30, trước khi chạy eval)

> Các metric chuẩn đã được cài trong `src/metrics/tracks.py`. File này là nơi nhóm **cam kết** cách dùng chúng.
> Không đổi testset, threshold hay trọng số sau khi đã thấy kết quả eval.

| Mục | Khai báo của nhóm |
|---|---|
| Track | T02 · Raw QC Triage |
| Primary metric (tên đúng như evaluator in ra) | Defect Recall@B (kèm Precision@B) |
| Tăng tốt hay giảm tốt? | higher |
| Đơn vị đánh giá | image |
| Công thức + numerator / denominator | Recall@B = #ảnh lỗi thật trong top-B (split eval) / #ảnh lỗi thật trong split eval; Precision@B = #ảnh lỗi thật trong top-B / B |
| Cách ghép prediction ↔ GT | theo `image_id` |
| Candidate pool cố định | 40 ảnh split `eval` trong `fixtures/t02_raw_qc/images.csv` |
| Review budget B / K | B = 20 |
| Seed | 42 |
| Threshold policy | Không dùng nhãn. Điểm = max log1p(robust-z) của 4 tín hiệu (blur theo camera, dark theo light, glare cục bộ, blockiness). Ngưỡng RECAPTURE: z ≥ 3,0; batch REWORK nếu > 15% ảnh RECAPTURE. Chốt trong `configs/lab.yaml` ngày 2026-11-14 |
| Eval split (không dùng để tune) | `eval` |
| Chỉ số lỗi xấu | miss (ảnh lỗi lọt khỏi top-B) và false alarm trên ảnh đêm |
| Slices sẽ báo cáo (≥2) | `light` (day / dusk / night), `camera_id` (cam_A / cam_B), defect type |
| Cách báo độ bất định khi N nhỏ | Wilson 95% CI cho Recall@B và Precision@B |
| Baseline so sánh | 1 ngưỡng Laplacian toàn ảnh (`src/baselines/t02_laplacian.py`), cùng pool / B / seed |
| Ngày giờ chốt + người chốt | 2026-11-14 · Nguyễn Duy Khánh (lead) |

Nếu baseline = 0 thì ghi rõ "baseline = 0" thay vì phần trăm cải thiện.
