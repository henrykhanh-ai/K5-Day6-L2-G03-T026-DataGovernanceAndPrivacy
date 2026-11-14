# Demo · Failure cases T02 (ảnh gốc từ `fixtures/t02_raw_qc/images/`, split dev)

| File | Gold (Quân) | PoC | Failure case |
|---|---|---|---|
| `failure_img_18_0.jpg` | blur · cam_B · night | KEEP (z = 0,3) | 1 · bỏ sót ảnh mờ cam_B (masking của median/MAD theo camera) |
| `failure_img_21_0.jpg` | blur · cam_B · day | KEEP (z = 0,4) | 1 · như trên |
| `failure_img_02_3.jpg` | dark · cam_A · day | RECAPTURE dark (z = 277,6) → reviewer An **reject** | 2 · bất đồng gold vs reviewer về mức "tối" |

Chi tiết root cause: `reports/group_report.md` mục 06.
