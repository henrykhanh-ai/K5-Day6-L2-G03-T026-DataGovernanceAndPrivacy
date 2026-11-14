# Group Report — Day 06 Data Lab (Field-to-Release PoC)

> Mọi con số dưới đây lấy từ file do script sinh ra (`out/*/run_info.json`, `out/poc/decision.json`,
> `reports/internal_eval_dev.md`, `reports/review_slices.md`, `reports/ablation_dev.md`). Điểm chính thức trên split `eval`
> do giảng viên chấm bằng ground truth ẩn; nhóm không có GT này nên các số Recall/Precision ở đây là **tự kiểm trên split dev**.

## 00 · Header

| Mục | Giá trị |
|---|---|
| Group ID | G03 (repo: G03-T026) |
| Challenge | T02 · Raw QC Triage — xếp hạng ảnh nghi lỗi (blur / glare / dark / compression), quyết định KEEP / RECAPTURE |
| Thành viên (4) + vai trò | 1. Nguyễn Duy Khánh — Henry (Lead / Core algorithm / Integrator) · 2. Quân (Gold set + failure mode) · 3. Nguyễn Thị Thúy An (Reviewer + slice/độ bất định) · 4. Lê Ngọc Bích Loan (Report + demo) |
| Git URL | https://github.com/henrykhanh-ai/K5-Day6-L2-G03-T026-DataGovernanceAndPrivacy |
| Tag `demo-180m` (commit) | `edde9a2` (14/11/2026 23:20) — bản demo; **chưa gồm** ablation (`tools/ablation_t02.py`, `reports/ablation_dev.md`), ảnh failure case trong `demo/` và `.mailmap` — các phần này thêm ở `384c4d8` (23:29), sau mốc demo, nằm trong `final-24h` |
| Tag `final-24h` (commit) | commit cuối sau +24h — xem `git rev-parse final-24h` |
| Deadline (giờ VN) | `demo-180m`: phút 180 của buổi lab 14/11/2026 · `final-24h`: +24h sau buổi lab (15/11/2026), theo lịch trong `README.md` |

## 01 · Problem statement

- **Ai bị ảnh hưởng khi hệ thống sai?** Đội huấn luyện model nhận dữ liệu: ảnh mờ / tối / lóa / nén nặng lọt vào tập train làm
  model học sai và khó phát hiện về sau (*miss*). Ngược lại, ảnh tốt bị gắn cờ oan (*false alarm*) làm đội thu thập phải chụp
  lại vô ích, tốn chi phí và thời gian reviewer.
- **Điểm nghẽn cụ thể:** reviewer chỉ có ngân sách **B = 20 ảnh** cho mỗi lô; không thể xem hết. Cần xếp hạng sao cho 20 ảnh đầu
  chứa nhiều ảnh lỗi thật nhất, và ra quyết định cả lô có được phát hành hay không.
- **Đầu vào → đầu ra:** `fixtures/t02_raw_qc/` (96 ảnh + `images.csv` có `camera_id`, `light`, `split` + `manifest.csv` sha256)
  → `out/poc/ranked_review.csv` (điểm, loại lỗi dự đoán, KEEP/RECAPTURE, lý do), `review_queue.csv` + `contact_sheet.html`
  (top-20 cho người duyệt), `audit_log.jsonl`, `decision.json` (GO / HOLD / REWORK + reason_code + owner + evidence).
- **Tiêu chí GO / HOLD / REWORK (chốt 2026-11-14 trong `configs/lab.yaml`, trước khi chạy eval):**
  chưa có người duyệt → HOLD `REVIEW_PENDING`; có mục escalate → HOLD `ESCALATED_ITEMS`; > 15% ảnh RECAPTURE (ngưỡng z ≥ 3,0)
  → REWORK `RECAPTURE_RATE_HIGH`; còn lại → GO `QC_PASSED`.
- **Giả định của nhóm (cần domain owner xác nhận):** (1) ảnh đêm tối là bình thường, chỉ coi là lỗi `dark` khi tối bất thường
  *so với ảnh cùng điều kiện ánh sáng*; (2) cam_B có quang học mềm hơn cam_A nên độ nét được so trong từng camera; (3) ngưỡng
  15% là mức chịu đựng của đội train — con số này cần chủ dữ liệu chốt chính thức.

## 02 · Data & provenance

| Split | N | Nguồn / link | License | Synthetic? |
|---|---|---|---|---|
| dev | 56 (cam_A 36 / cam_B 20; day 36 / dusk 16 / night 4) | `fixtures/t02_raw_qc` — `synthetic:tools/make_fixtures.py (seed 42)` | CC0-1.0 (synthetic, generated for AI20K Day06) | Có |
| eval / heldout | 40 (cam_A 28 / cam_B 12; day 20 / dusk 4 / night 16) | `fixtures/t02_raw_qc` — `synthetic:tools/make_fixtures.py (seed 42)` | CC0-1.0 | Có |

- **Schema & class mapping:** `images.csv`: `image_id, path, camera_id, light, split`. Lớp lỗi: `none / blur / glare / dark /
  compression`; `is_defect = defect_type != none`; hành động `RECAPTURE` nếu có lỗi, `KEEP` nếu không.
- **Seed: 42 · Cách chia split:** theo **nhóm ảnh** (`group_id` = `img_XX`, mỗi nhóm 4 biến thể `_0…_3`). Đã kiểm tra:
  không có `group_id` nào xuất hiện ở cả dev và eval (`python -m tools.check_gold_t02`) → không rò rỉ cảnh giữa 2 split.
- **`manifest.csv` verified (sha256): có** — `python -m tools.verify_manifests` → *14 manifests, 0 failing*. Pipeline chạy với
  `strict_provenance: true` (dừng nếu hash lệch).
- **Dữ liệu thật:** không dùng. **GT nội bộ:** split eval không có nhãn (GT đã được chuyển sang repo riêng của giảng viên), nên
  nhóm tự xây **gold set trên split dev**: Quân gán tay cả 56 ảnh dev (`reports/dev_gold_labels.csv`, cột `defect_type`, `labeler`)
  qua `reports/dev_gold_gallery.html`; kết quả 33 ảnh lỗi (blur 13, compression 10, dark 6, glare 4) và 23 ảnh `none`.
  Script chặn mọi nhãn trên ảnh eval; đã kiểm tra 56/56 ảnh thuộc dev, 0 ảnh eval.
- **Lệch phân phối dev ↔ eval cần lưu ý:** eval có **16/40 ảnh đêm**, dev chỉ có **4/56** → mọi kết luận về ảnh đêm từ gold set dev
  có độ tin cậy thấp (xem 09).

## 03 · Research & design

- **References và vì sao chọn kỹ thuật** (chi tiết ở mục 11):
  - Phương sai Laplacian là thước đo độ nét kinh điển thuộc nhóm toán tử dựa trên đạo hàm bậc hai (Pertuz et al., 2013) → dùng cho
    tín hiệu `blur` và cho baseline.
  - Robust z-score dùng median + MAD thay cho mean + SD để ngưỡng không bị chính ảnh lỗi kéo lệch (Iglewicz & Hoaglin, qua NIST
    e-Handbook) → chuẩn hoá cả 4 tín hiệu.
  - Khoảng tin cậy Wilson được khuyến nghị cho tỉ lệ khi n nhỏ (Brown, Cai & DasGupta, 2001) → dùng cho mọi Recall/Precision.
- **Data flow (5 bước trong `src/pipeline.py`):**
  `01 load` (kiểm manifest sha256, schema, file ảnh) → `02 process` (4 tín hiệu thô → robust-z theo đúng slice → điểm = max log1p(z))
  → `03 rank` (top-B = 20 → `review_queue.csv` + `contact_sheet.html`) → `04 review` (áp quyết định người duyệt, ghi `audit_log.jsonl`,
  không sửa điểm gốc) → `05 decide` (GO/HOLD/REWORK + reason_code + owner + evidence → `decision.json`, `decision_log.csv`).
- **4 tín hiệu (không cần nhãn, `src/features_t02.py`):** `blur` = −log phương sai Laplacian, so **trong từng camera**;
  `dark` = độ sáng trung bình thấp + tỉ lệ pixel tối, so **trong từng điều kiện ánh sáng** (ảnh đêm không bị coi là lỗi);
  `glare` = ô lưới 8×8 gần như bão hoà trắng (bắt lóa cục bộ ở biển số); `compression` = độ chênh gradient tại biên khối 8/16 px.
- **Thành phần offline:** không có model/weights; chỉ numpy, pandas, Pillow, scipy. Chạy `--offline`, không cần mạng.
- **Trade-offs:** (1) tín hiệu thủ công, giải thích được, không cần nhãn — đổi lại không học được lỗi phức tạp; (2) log1p đưa 4 tín
  hiệu về cùng thang để so sánh, nhưng làm ảnh tối đen (z ≈ 365) và tối vừa (z ≈ 260) gần như ngang điểm; (3) chuẩn hoá theo slice
  giảm báo nhầm ảnh đêm / cam_B, nhưng khi một slice có quá nhiều ảnh lỗi thì median bị kéo lệch (xem failure case 1).

## 04 · Baseline vs PoC

- **Baseline:** `src/baselines/t02_laplacian.py` — **một** ngưỡng phương sai Laplacian toàn ảnh (score = −log Laplacian var,
  cắt tại median), không chuẩn hoá theo slice, không tín hiệu khác. Commit `ab277c5`.
- **PoC:** `src/pipeline.py` + `src/features_t02.py`, config `configs/lab.yaml` (`recapture_z: 3.0`, `max_recapture_rate: 0.15`,
  `budget: 20`). Commit `fd78cf1`.
- **Cùng budget / cùng pool / cùng seed: xác nhận** — B = 20, cùng 96 ảnh `fixtures/t02_raw_qc`, seed 42, `--offline`.

**Bảng 1 · Baseline vs PoC & hard slices.** `python -m src.evaluate` / `src.compare` cần GT của split eval, nhóm không có (GT ẩn của
giảng viên) → bảng dưới dùng đánh giá nội bộ trên gold set dev (`python -m src.internal_eval_t02 evaluate` → `reports/internal_eval_dev.md`).

| Metric (unit) | Baseline | PoC | Δ & chú thích |
|---|---|---|---|
| Primary: Defect Recall@20 (image, dev gold) | 15/33 = 0,45 (95% CI 0,30–0,62) | 20/33 = 0,61 (95% CI 0,44–0,75) | +0,15; higher is better. **0,61 là trần** vì 33 ảnh lỗi > B = 20. CI còn chồng nhau → chưa kết luận chắc |
| Precision@20 (image, dev gold) | 15/20 = 0,75 (95% CI 0,53–0,89) | 20/20 = 1,00 (95% CI 0,84–1,00) | +0,25; higher is better |
| Hard-slice: Recall@20 cam_B | 7/15 = 0,47 (0,25–0,70) | 5/15 = 0,33 (0,15–0,58) | −0,13; **PoC kém hơn baseline ở cam_B**; N = 20 |
| Hard-slice: Recall@20 night | 1/3 = 0,33 (0,06–0,79) | 1/3 = 0,33 (0,06–0,79) | 0; N = 4 (quá nhỏ) |
| Review@B / miss / FP | B = 20; miss 18; FP 5 | B = 20; miss 13; FP 0 | miss = ảnh lỗi ngoài top-20; FP = ảnh `none` trong top-20 |
| Runtime / 100 items | 0,18 s (0,1724 s / 96) | 0,58 s (0,5587 s / 96) | ≈ 5,8 ms/ảnh; CPU Intel64 Family 6 Model 141, Windows 11, Python 3.12.8 |

## 05 · Evaluation protocol

- **Primary metric** (`reports/metric_contract.md`): đơn vị = 1 ảnh, ghép theo `image_id`. Recall@B = #ảnh lỗi thật trong top-B /
  #ảnh lỗi thật trong pool; Precision@B = #ảnh lỗi thật trong top-B / B. TP = ảnh lỗi trong top-B, FP = ảnh `none` trong top-B,
  FN = ảnh lỗi ngoài top-B. Pool chính thức = 40 ảnh eval (giảng viên chấm); pool nội bộ = 56 ảnh dev đã gán.
- **Threshold / budget:** B = 20; RECAPTURE khi robust-z ≥ 3,0; REWORK khi > 15% ảnh RECAPTURE. Chốt 2026-11-14 trong
  `configs/lab.yaml` **trước khi** có gold set và trước khi chạy eval; không sửa sau đó.
- **Kiểm tra lại ngưỡng trên dev (không dùng eval)** — `python -m tools.check_gold_t02`:

| recapture_z | TP | FP | FN | Precision | Recall | Tỉ lệ RECAPTURE (96 ảnh) |
|---|---|---|---|---|---|---|
| 2,0 | 28 | 1 | 5 | 0,97 | 0,85 | 50% |
| **3,0 (đã chốt)** | **27** | **0** | **6** | **1,00** | **0,82** | **46%** |
| 5,0 | 24 | 0 | 9 | 1,00 | 0,73 | 39% |
| 10,0 | 14 | 0 | 19 | 1,00 | 0,42 | 24% |

  Ở z = 3 không có báo nhầm nào; nâng ngưỡng chỉ làm mất ảnh lỗi thật mà không giảm thêm FP. Muốn tỉ lệ RECAPTURE < 15% phải nâng
  z lên ≈ 20 (tỉ lệ 12,5%) — vô lý về chất lượng. **Kết luận: giữ ngưỡng đã chốt**; tỉ lệ cao phản ánh dữ liệu kém thật (gold set:
  33/56 = 59% ảnh dev bị lỗi).
- **Độ bất định:** Wilson 95% CI cho mọi tỉ lệ (n nhỏ: 33 ảnh lỗi, slice night chỉ 4 ảnh). Gold set do **một** người gán.
- **Lệnh evaluate:** chính thức `python -m src.evaluate --track t02 --gt <GT ẩn> --pred out/poc/ranked_review.csv --out reports/metrics_poc.json`
  (giảng viên chạy); nội bộ `python -m src.internal_eval_t02 evaluate`.

## 06 · Result slices

Nguồn: `reports/internal_eval_dev.md` (gold set dev, B = 20, Recall trong top-B trên ảnh lỗi của từng slice).

| Slice | N (lỗi) | Baseline | PoC | Ghi chú |
|---|---|---|---|---|
| light = day | 36 (21) | 10/21 = 0,48 · FP 5 | 13/21 = 0,62 · FP 0 | PoC hết báo nhầm ảnh ngày |
| light = dusk | 16 (9) | 4/9 = 0,44 | 6/9 = 0,67 | |
| light = night | 4 (3) | 1/3 = 0,33 | 1/3 = 0,33 | N quá nhỏ; eval có 16 ảnh đêm |
| camera = cam_A | 36 (18) | 8/18 = 0,44 · FP 5 | 15/18 = 0,83 · FP 0 | |
| camera = cam_B | 20 (15) | 7/15 = 0,47 | **5/15 = 0,33** | điểm yếu chính của PoC |

PoC đoán **đúng loại lỗi** cho 27/33 ảnh lỗi = 0,82 (95% CI 0,66–0,91); 6 ảnh sai loại đều là ảnh bị đoán `none` (bỏ sót).

- **Failure case 1 — bỏ sót ảnh mờ của cam_B** (miss, ảnh trong `demo/`): 6 ảnh lỗi có z < 3 bị đoán `none`; **5/6 là ảnh blur của
  cam_B**: `img_18_0` (night, z = 0,3), `img_21_0` (day, z = 0,4), `img_09_0` (z = 1,2), `img_12_0` (z = 1,2), `img_00_0` (z = 2,4);
  ảnh thứ 6 là `img_08_2` (compression, cam_A, z = 1,9). **Root cause (giả thuyết):** tín hiệu blur so **trong từng camera** bằng
  median/MAD. Trong dev, **9/20 ảnh cam_B bị mờ (45%)** — gần điểm vỡ 50% của median/MAD — nên median của cam_B tự lệch về phía
  mờ và ảnh mờ không còn "khác thường" so với đồng loại (hiệu ứng *masking*). Cách sửa đề xuất cho v2: tính median/MAD trên tập
  tham chiếu ảnh tốt đã biết của từng camera, hoặc thêm ngưỡng độ nét tuyệt đối tối thiểu.
- **Failure case 2 — tín hiệu `dark` không phân biệt "tối vừa" với "tối đen"** (bất đồng người duyệt): `img_02_3`, `img_20_2`,
  `img_10_3`, `img_07_2` là ảnh `light=day` nhưng độ sáng trung bình chỉ ≈ 23–26/255 (ảnh gốc cùng cảnh `img_02_0`: 118/255). PoC
  cho z ≈ 258–278, gần bằng ảnh tối đen (z ≈ 365) vì log1p nén thang điểm. Reviewer An **reject** cả 4 ("thiếu sáng nhẹ nhưng vẫn
  nhìn được vật thể"), còn gold set của Quân gán cả 4 là `dark`. **Root cause:** tín hiệu chỉ đo độ sáng, không đo "còn dùng được
  hay không"; định nghĩa lỗi `dark` trong đề chưa nêu mức tối tối thiểu. Đề xuất: thêm mức độ (`severity`) cho `dark` và chốt
  ranh giới với domain owner.
- **Latency / compute:** PoC 0,5587 s cho 96 ảnh ≈ 5,8 ms/ảnh; baseline ≈ 1,8 ms/ảnh. Máy: Intel64 Family 6 Model 141, Windows 11,
  Python 3.12.8, chỉ CPU.

### 06a · Ablation — bỏ từng tín hiệu (gold set dev, B = 20)

Lệnh: `python -m tools.ablation_t02` → `reports/ablation_dev.md` (không áp review của người, không dùng eval).

| Cấu hình | Recall@20 | Precision@20 | Tỉ lệ RECAPTURE (96 ảnh) | Lỗi bắt được trong top-20 theo loại |
|---|---|---|---|---|
| PoC đầy đủ (4 tín hiệu) | 20/33 = 0,61 (0,44–0,75) | 20/20 = 1,00 (0,84–1,00) | 46% | blur 5/13 · dark 6/6 · glare 4/4 · compression 5/10 |
| bỏ `blur` | 20/33 = 0,61 (0,44–0,75) | 20/20 = 1,00 (0,84–1,00) | 33% | **blur 1/13** · dark 6/6 · glare 4/4 · compression 9/10 |
| bỏ `dark` | 20/33 = 0,61 (0,44–0,75) | 20/20 = 1,00 (0,84–1,00) | 40% | blur 8/13 · **dark 0/6** · glare 4/4 · compression 8/10 |
| bỏ `glare` | 20/33 = 0,61 (0,44–0,75) | 20/20 = 1,00 (0,84–1,00) | 38% | blur 7/13 · dark 6/6 · **glare 0/4** · compression 7/10 |
| bỏ `compression` | 19/33 = 0,58 (0,41–0,73) | 19/20 = 0,95 (0,76–0,99) | 32% | blur 8/13 · dark 6/6 · glare 4/4 · **compression 1/10** |

Nhận xét:
- **Recall@20 gần như không đổi khi bỏ tín hiệu** — không phải vì tín hiệu vô dụng, mà vì metric đã **bão hoà**: dev có 33 ảnh lỗi
  > B = 20, nên khi bỏ một tín hiệu, ảnh lỗi loại khác lấp vào top-20. Recall@20 trên pool này không đủ nhạy để so tín hiệu.
- Cột cuối mới cho thấy giá trị thật: **bỏ tín hiệu nào thì gần như mất trắng loại lỗi đó** (blur 5→1, dark 6→0, glare 4→0,
  compression 5→1). 4 tín hiệu **không thay thế được nhau**; mỗi tín hiệu là cách duy nhất để bắt loại lỗi của nó.
- Bỏ `compression` là trường hợp duy nhất làm lọt 1 ảnh sạch vào top-20 (Precision 0,95) và giảm tỉ lệ RECAPTURE mạnh nhất (46% → 32%).
- Kể cả khi bỏ bất kỳ tín hiệu nào, tỉ lệ RECAPTURE vẫn ≥ 32% > 15% → quyết định REWORK **không phụ thuộc** vào một tín hiệu đơn lẻ.
- Hạn chế: ablation không áp review của người và đo trên gold set một người gán; để so tín hiệu tốt hơn cần metric không bão hoà
  (ví dụ recall trên toàn bộ ảnh bị gắn RECAPTURE) hoặc pool có ít ảnh lỗi hơn B.

### 06b · Kết quả human review theo slice (thành viên C · Thúy An)

Nguồn: `reports/review_queue.csv` (20 ảnh top-B đã duyệt) → `python -m src.review_slices_t02` → `reports/review_slices.md`.
Đơn vị = 1 ảnh trong queue; "xác nhận lỗi" = reviewer approve (hoặc edit sang một loại lỗi). Đây là **precision của queue theo
đánh giá reviewer**, *không phải* Recall@20 (recall cần nhãn cho cả ảnh ngoài queue → gold set dev của B / GT ẩn của giảng viên).

- Tổng: **16/20 = 0,80 (Wilson 95% CI 0,58–0,92)** · quyết định: 16 approve, 4 reject, 0 escalate.

| Slice | N trong queue | Xác nhận lỗi (Wilson 95% CI) | False alarm |
|---|---|---|---|
| light = day | 12 | 8/12 = 0,67 (0,39–0,86) | 4 |
| light = dusk | 5 | 5/5 = 1,00 (0,57–1,00) | 0 |
| light = night | 3 | 3/3 = 1,00 (0,44–1,00) | 0 |
| camera_id = cam_A | 17 | 13/17 = 0,76 (0,53–0,90) | 4 |
| camera_id = cam_B | 3 | 3/3 = 1,00 (0,44–1,00) | 0 |
| loại lỗi = dark | 10 | 6/10 = 0,60 (0,31–0,83) | 4 |
| loại lỗi = glare | 6 | 6/6 = 1,00 (0,61–1,00) | 0 |
| loại lỗi = blur | 4 | 4/4 = 1,00 (0,51–1,00) | 0 |

Nhận xét:
- **Cả 4 false alarm đều cùng một kiểu**: `light=day`, `cam_A`, tín hiệu `dark` (img_02_3, img_20_2, img_10_3, img_07_2). Đo độ sáng:
  các ảnh này chỉ sáng ~19–22% so với trung vị ảnh ngày ngoài queue, nhưng vật thể vẫn nhận ra được. Reviewer áp quy tắc
  *"thiếu sáng nhẹ nhưng vẫn nhìn được vật thể → KEEP"*. Root cause: tín hiệu `dark` chỉ đo độ sáng (z-score theo slice light),
  không đo "còn dùng được hay không" → ảnh tối vừa và ảnh tối đen (4–5%) đều bị đẩy lên top với điểm gần nhau (z ≈ 260–365).
  Đây là điểm tranh luận: theo định nghĩa lỗi `dark` của đề, giảng viên có thể coi 4 ảnh này là lỗi thật → reject của reviewer
  có thể là sai; nhóm ghi nhận để so khi có kết quả chấm chính thức.
- `glare` và `blur` không có false alarm trong queue; bẫy "lóa cục bộ ở biển số" (img_18_2, ảnh đêm có độ sáng bình thường 105%)
  được reviewer xác nhận là glare thật, không bị nhầm thành ảnh đêm.
- Ảnh đêm và cam_B chỉ có 3 ảnh mỗi slice trong queue → CI rất rộng (0,44–1,00); không kết luận được pipeline có bỏ sót lỗi ở
  hai slice này hay không — cần gold set dev.
- 7/20 ảnh trong queue thuộc split `eval`: các quyết định review **không** được dùng để chỉnh ngưỡng (`configs/lab.yaml` giữ nguyên).

## 07 · Human & decision

- Review queue (file, B, cách ưu tiên): `out/poc/review_queue.csv` + `contact_sheet.html`, B = 20 ảnh điểm nghi lỗi cao nhất
  (cả split dev và eval). Reviewer: Thúy An (thành viên C). Bản đã duyệt lưu ở `reports/review_queue.csv`.
- Cách override + audit log: reviewer chọn trong contact sheet → Export CSV → chép vào `out/poc/review_queue_reviewed.csv` → chạy lại
  PoC. `reject` → KEEP/none, `edit` → đổi loại lỗi, `escalate` → HOLD cả lô. Mỗi quyết định ghi 1 dòng vào `out/poc/audit_log.jsonl`
  (actor, item, before/after, lý do); điểm gốc không bị sửa.
- Diễn biến review (minh chứng human-in-the-loop): lần 1 có 4 reject không ghi lý do + 2 escalate (img_08_3, img_18_2) → decision
  **HOLD / ESCALATED_ITEMS**. Reviewer làm lại từ đầu với quy tắc thống nhất cho cả lô (ảnh ngày thiếu sáng nhẹ nhưng còn nhìn được
  vật thể → reject, ghi lý do; ảnh đêm có đốm lóa ở biển số → glare thật) → 16 approve / 4 reject / 0 escalate.
- Decision policy + `reason_code` + owner: chưa review → HOLD `REVIEW_PENDING`; có escalate → HOLD `ESCALATED_ITEMS`; tỉ lệ RECAPTURE
  > 15% → REWORK `RECAPTURE_RATE_HIGH`; còn lại → GO `QC_PASSED`. Owner lấy từ `configs/lab.yaml`.
- Kết quả cuối: **REWORK / RECAPTURE_RATE_HIGH** — 42% ảnh (40/96) cần chụp lại sau review (> ngưỡng 15%) → lô chưa được phát hành.
- Khi nào HOLD/REWORK thay vì tự động release: luôn HOLD khi chưa có người duyệt hoặc có mục escalate; REWORK khi tỉ lệ ảnh hỏng
  vượt ngưỡng đã chốt trước khi chạy eval.
- Khai báo công cụ AI (thành viên C): dùng Claude để hướng dẫn quy trình, đo độ sáng tham khảo và viết `src/review_slices_t02.py`
  + test; các quyết định approve/reject do reviewer tự chọn trên contact sheet.

## 08 · Reproduce & tests

```bash
python -m venv .venv && .venv/Scripts/activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m tools.verify_manifests                          # 14 manifests, 0 failing
python -m src.main --track t02 --pipeline src.baselines.t02_laplacian --output out/baseline --run-name baseline --offline --seed 42
python -m src.main --config configs/lab.yaml --track t02 --output out/poc --run-name poc --offline --seed 42
python -m src.internal_eval_t02 evaluate                  # -> reports/internal_eval_dev.md (gold set dev)
python -m tools.check_gold_t02                            # leakage + sweep ngưỡng trên dev
python -m tools.ablation_t02                              # -> reports/ablation_dev.md
pytest -q
```

Quyết định người duyệt đã commit ở `out/poc/review_queue_reviewed.csv` (bản gốc `reports/review_queue.csv`) nên chạy lại PoC cho
đúng `decision.json`: **REWORK / RECAPTURE_RATE_HIGH**, `n_reviewed = 20`, `recapture_rate = 0.4167`, kèm 6 file evidence.

- **Output của `pytest -q`:** 56 passed, 39 skipped (các track khác t02), 0 failed.
- **Máy / CPU / OS / Python:** Intel64 Family 6 Model 141, Windows 11 (10.0.26200), Python 3.12.8 · git sha: `fd78cf1`.

## 09 · Limitations & ethics

- **Pháp lý / PII / license:** dữ liệu là ảnh tổng hợp CC0-1.0, biển số dạng `SYN-…` giả, không có người thật → không có PII.
  Nếu áp cho ảnh đường phố thật: khuôn mặt và biển số là dữ liệu cá nhân, phải che (redaction) trước khi đưa vào contact sheet cho
  reviewer, và kiểm license từng nguồn ảnh.
- **Điều chưa biết / false alarm:**
  - Gold set chỉ do **một** người gán; trên 13 ảnh trùng giữa gold set và hàng đợi review, Quân và An **đồng ý 9/13 (69%)** — cả 4 bất
    đồng là ảnh ngày bị tối (failure case 2). Nhóm sẽ vote đa số theo guideline và ghi nhận khi có kết quả chấm chính thức.
  - Eval có 16/40 ảnh đêm nhưng dev chỉ 4 → hành vi của PoC trên ảnh đêm gần như chưa được kiểm chứng.
  - 7/20 ảnh trong hàng đợi review thuộc split eval; quyết định review chỉ dùng cho decision của lô, **không** dùng để chỉnh ngưỡng.
- **Nếu scale 10×:** runtime tuyến tính (≈ 5,8 ms/ảnh → ~6 s cho 960 ảnh); nhưng ngân sách review B = 20 sẽ chỉ phủ ~2% lô → cần
  tăng B theo kích thước lô hoặc lấy mẫu ngẫu nhiên thêm để ước lượng tỉ lệ lỗi. Median/MAD theo camera cũng cần đủ ảnh tốt mỗi
  camera, nếu không masking (failure case 1) sẽ nặng hơn.
- **Không tuyên bố tuân thủ GDPR / luật Việt Nam** từ pipeline này. Giả định cần DPO/legal và chủ dữ liệu xác nhận: ngưỡng 15%,
  định nghĩa lỗi `dark`, và quy trình lưu audit log.
- **Kế hoạch cải tiến:** (1) chuẩn hoá blur theo tập tham chiếu ảnh tốt của từng camera; (2) thêm `severity` cho `dark`;
  (3) gán đôi gold set (2 người) và báo Cohen's κ; (4) thu thêm ảnh đêm vào dev.

## 10 · Team contribution

**Bảng 2 · Individual contribution evidence** (đối chiếu `git shortlog -sne --all` và `reports/team_contributions.csv`)

| Học viên | Git author/email | Module / vai trò | Commit SHA / diff chứng minh | Trình bày? |
|---|---|---|---|---|
| Nguyễn Duy Khánh (Henry) | Nguyen Duy Khanh / duykhanh19.hr@gmail.com | Lead · Core algorithm · tích hợp: `src/features_t02.py`, `src/pipeline.py`, `src/baselines/t02_laplacian.py`, `src/internal_eval_t02.py`, `tests/test_t02_pipeline.py`, `configs/lab.yaml`, `tools/check_gold_t02.py`, ablation (`tools/ablation_t02.py`, `reports/ablation_dev.md`), evidence trong decision, merge PR | `ab277c5`, `fb00041`, `c6bae0c`, `ba2ed38`, `fd78cf1`, commit *feat(t02): ablation script + dev results* | Có |
| Nguyễn Việt Quân | JakeNguyen99/ quannguyenviet99@gmail.com | Gold set 56 ảnh dev, đánh giá nội bộ, output baseline/PoC | `c7074c6`, `d0e6ca7`, `390f21d` | Không |
| Nguyễn Thị Thúy An | nguyenthithuyan091005-svg / nguyenthithuyan091005@gmail.com | Reviewer 20 ảnh, `src/review_slices_t02.py` + test, bảng slice + Wilson CI, mục 06b/07 | `6624342`, `9d2ba3e` | Có |
| Lê Ngọc Bích Loan | panii273/ lengocbichloan5@gmail.com| Report nhóm (`reports/group_report.md`), slide demo | commit *docs(t02): group report* | Không |

**Khai báo công cụ AI:** nhóm dùng Claude để hỗ trợ viết code (pipeline, script kiểm tra gold set / ablation), kiểm tra leakage và
soạn nháp report; mọi nhãn gold set (Quân) và quyết định approve/reject (An) do người tự chọn; số liệu lấy từ output của script.

## 11 · References

| URL | Ngày xem | 1–2 dòng ý nghĩa (không chép nguyên văn) |
|---|---|---|
| https://doi.org/10.1016/j.patcog.2012.11.011 | 2026-11-14 | Pertuz, Puig & Garcia (2013), *Pattern Recognition* 46(5): so sánh các toán tử đo độ nét, trong đó nhóm dựa trên Laplacian — cơ sở cho tín hiệu `blur` và baseline. |
| https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm | 2026-11-14 | NIST e-Handbook, *Detection of Outliers*: modified z-score dùng median và MAD (Iglewicz & Hoaglin) — cơ sở cho robust-z theo slice. |
| https://doi.org/10.1214/ss/1009213286 | 2026-11-14 | Brown, Cai & DasGupta (2001), *Statistical Science* 16(2): khoảng Wald kém tin cậy, khuyến nghị Wilson cho n nhỏ — lý do dùng Wilson 95% CI. |

---

**Bảng 3 · Checklist chốt khi nộp**

- [ ] Link repo và tag cuối cùng trong README; input mẫu không chứa PII thật.
- [x] Đúng 1 lệnh run, 1 lệnh evaluate, 1 lệnh tests; không cần download khi chạy (`--offline`).
- [x] Có baseline/PoC metrics (dev gold), ≥1 failure case, reviewer evidence, decision log.
- [x] Có license/source provenance, data splits, seed, offline environment, GT/eval N.
- [ ] Mỗi thành viên có ≥1 commit thực chất và được nêu minh bạch trong bảng trên (Loan cần commit report dưới tên mình).
