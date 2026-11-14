# T02 · Kết quả human review theo slice (thành viên C)

- File review: `reports/review_queue.csv` · B = 20 ảnh · reviewer: Thúy An
- Quyết định: {'approve': 16, 'reject': 4}
- **Precision của queue theo reviewer** (ảnh được xác nhận lỗi / ảnh đã quyết định): 16/20 = 0.80 (95% CI 0.58–0.92)
- Đây KHÔNG phải Recall@20: muốn có recall cần nhãn cho cả ảnh ngoài queue (gold set dev của B, hoặc GT ẩn của giảng viên trên eval).
- N mỗi slice rất nhỏ nên khoảng tin cậy Wilson 95% rất rộng; chỉ đọc như tín hiệu, không kết luận mạnh.

| Slice | Giá trị | N trong queue | Xác nhận lỗi (Wilson 95% CI) | False alarm |
|---|---|---|---|---|
| light | day | 12 | 8/12 = 0.67 (95% CI 0.39–0.86) | 4 |
| light | dusk | 5 | 5/5 = 1.00 (95% CI 0.57–1.00) | 0 |
| light | night | 3 | 3/3 = 1.00 (95% CI 0.44–1.00) | 0 |
| camera_id | cam_A | 17 | 13/17 = 0.76 (95% CI 0.53–0.90) | 4 |
| camera_id | cam_B | 3 | 3/3 = 1.00 (95% CI 0.44–1.00) | 0 |
| split | dev | 13 | 9/13 = 0.69 (95% CI 0.42–0.87) | 4 |
| split | eval | 7 | 7/7 = 1.00 (95% CI 0.65–1.00) | 0 |
| pred_defect_type | blur | 4 | 4/4 = 1.00 (95% CI 0.51–1.00) | 0 |
| pred_defect_type | dark | 10 | 6/10 = 0.60 (95% CI 0.31–0.83) | 4 |
| pred_defect_type | glare | 6 | 6/6 = 1.00 (95% CI 0.61–1.00) | 0 |

Slice có N nhỏ (ví dụ cam_B, night) chỉ có vài ảnh trong queue: CI rộng, cần gold set dev để biết pipeline có bỏ sót lỗi ở slice đó hay không.
