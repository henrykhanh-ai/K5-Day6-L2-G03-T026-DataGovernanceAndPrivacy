# Đánh giá nội bộ T02 trên split dev (gold set tự gán)

- Gold set: 56 ảnh dev đã gán, 33 ảnh lỗi; người gán: Quan
- Budget B = 20 trên pool 56 ảnh đã gán; khoảng tin cậy Wilson 95%
- Đây là số tự kiểm, **không phải điểm chính thức** (giảng viên chấm trên split eval bằng ground truth ẩn).

## Kết quả chính

| Run | Recall@B | Precision@B | Loại lỗi đúng (trên ảnh lỗi) |
|---|---|---|---|
| baseline | 15/33 = 0.45 (95% CI 0.30–0.62) | 15/20 = 0.75 (95% CI 0.53–0.89) | – |
| poc | 20/33 = 0.61 (95% CI 0.44–0.75) | 20/20 = 1.00 (95% CI 0.84–1.00) | loại lỗi đúng: 23/33 = 0.70 (95% CI 0.53–0.83) |

## Theo slice

| Run | Slice | N | Recall trong top-B (ảnh lỗi) | False alarm trong top-B (ảnh sạch) |
|---|---|---|---|---|
| baseline | light=day | 36 | 10/21 = 0.48 (95% CI 0.28–0.68) | 5/15 = 0.33 (95% CI 0.15–0.58) |
| baseline | light=dusk | 16 | 4/9 = 0.44 (95% CI 0.19–0.73) | 0/7 = 0.00 (95% CI 0.00–0.35) |
| baseline | light=night | 4 | 1/3 = 0.33 (95% CI 0.06–0.79) | 0/1 = 0.00 (95% CI 0.00–0.79) |
| baseline | camera_id=cam_A | 36 | 8/18 = 0.44 (95% CI 0.25–0.66) | 5/18 = 0.28 (95% CI 0.12–0.51) |
| baseline | camera_id=cam_B | 20 | 7/15 = 0.47 (95% CI 0.25–0.70) | 0/5 = 0.00 (95% CI 0.00–0.43) |
| poc | light=day | 36 | 13/21 = 0.62 (95% CI 0.41–0.79) | 0/15 = 0.00 (95% CI 0.00–0.20) |
| poc | light=dusk | 16 | 6/9 = 0.67 (95% CI 0.35–0.88) | 0/7 = 0.00 (95% CI 0.00–0.35) |
| poc | light=night | 4 | 1/3 = 0.33 (95% CI 0.06–0.79) | 0/1 = 0.00 (95% CI 0.00–0.79) |
| poc | camera_id=cam_A | 36 | 15/18 = 0.83 (95% CI 0.61–0.94) | 0/18 = 0.00 (95% CI 0.00–0.18) |
| poc | camera_id=cam_B | 20 | 5/15 = 0.33 (95% CI 0.15–0.58) | 0/5 = 0.00 (95% CI 0.00–0.43) |
