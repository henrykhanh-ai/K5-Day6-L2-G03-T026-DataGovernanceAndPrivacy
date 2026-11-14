# Group Report — Day 06 Data Lab (Field-to-Release PoC)

> Điền đầy đủ, cụ thể, không viết chung chung. Mọi con số phải lấy từ file do script sinh ra
> (`reports/metrics_*.json`, `reports/table1_baseline_vs_poc.md`) — không gõ tay, không làm tròn mất đơn vị.
> 3–5 trang (hoặc README + report.md tương đương).

## 00 · Header

| Mục | Giá trị |
|---|---|
| Group ID | G__ |
| Challenge | T__ · ______________________ |
| Thành viên (5–6) + vai trò | 1. ____ (Lead/Integrator) · 2. ____ (Data & fixtures) · 3. ____ (Core algorithm) · 4. ____ (QA/metric) · 5. ____ (Review + report) · 6. ____ |
| Git URL | ____ |
| Tag `demo-180m` (commit) | ____ |
| Tag `final-24h` (commit) | ____ |
| Deadline (giờ VN) | ____ |

## 01 · Problem statement

- Ai bị ảnh hưởng / ai chịu hậu quả khi hệ thống sai? ____
- Điểm nghẽn cụ thể: ____
- Đầu vào → đầu ra: ____
- Tiêu chí GO / HOLD / REWORK (chốt trước khi chạy eval): ____
- Giả định của nhóm (cần DPO/legal/domain owner xác nhận): ____

## 02 · Data & provenance

| Split | N | Nguồn / link | License | Synthetic? |
|---|---|---|---|---|
| dev | | | | |
| eval / heldout | | | | |

- Schema & class mapping: ____
- Seed: 42 · Cách chia split (theo scene/group/segment?): ____
- `manifest.csv` verified (sha256): có / không — lệnh: `python -m tools.verify_manifests`
- Dữ liệu thật dùng (nếu có) và cách xây GT cho nó: ____

## 03 · Research & design

- 2–3 references (URL + ngày xem) và **vì sao** chọn kỹ thuật: ____
- Sơ đồ data flow (input → process → rank/QC → review → decision → report): ____
- Thành phần offline (model/weights + checksum + license nếu có): ____
- Trade-offs đã cân nhắc: ____

## 04 · Baseline vs PoC

- Baseline (mô tả, version/config, commit): ____
- PoC (mô tả, version/config, commit): ____
- Cùng budget / cùng heldout / cùng seed: xác nhận ____

**Bảng 1 · Baseline vs PoC & hard slices** — dán output của
`python -m src.compare reports/metrics_baseline.json reports/metrics_poc.json`:

| Metric (unit) | Baseline | PoC | Δ & chú thích |
|---|---|---|---|
| Primary: ______ | ____ | ____ | ____; higher/lower? |
| Hard-slice: ______ | ____ | ____ | ____; N=__ |
| Review@B / miss / FP | ____ | ____ | ____; B=__ |
| Runtime / 100 items | ____ | ____ | ____; CPU=__ |

## 05 · Evaluation protocol

- Công thức primary metric, đơn vị đánh giá, TP/FP/FN, denominator: ____ (xem `reports/metric_contract.md`)
- Threshold / budget B / K và lúc chốt: ____
- Độ bất định (CI/bootstrap/variance) khi N nhỏ: ____
- Lệnh evaluate chính xác: `python -m src.evaluate --track t__ --pred ... --out ...`

## 06 · Result slices

| Slice | N | Baseline | PoC | Ghi chú |
|---|---|---|---|---|
| | | | | |
| | | | | |

- Failure case 1 (ảnh/metadata + root cause): ____
- Failure case 2: ____
- Latency / compute (máy, CPU, ms/item): ____

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
make setup          # hoặc: python -m venv .venv && pip install -r requirements.txt
python -m src.main --input fixtures/<track> --config configs/lab.yaml --output out/ --offline --seed 42
python -m src.evaluate --track t__ --pred out/<file> --out reports/metrics_poc.json
pytest -q
```

- Output của `pytest -q`: ____
- Máy / CPU / OS / Python: ____ · git sha: ____

## 09 · Limitations & ethics

- Rủi ro pháp lý / PII / license: ____
- Điều chưa biết; false alarms; nếu scale 10× thì sao: ____
- Không tuyên bố "đạt GDPR / luật Việt Nam" từ checklist tự động; giả định cần DPO/legal xác nhận: ____
- Kế hoạch cải tiến: ____

## 10 · Team contribution

**Bảng 2 · Individual contribution evidence** (đối chiếu với `git shortlog -sne --all` và `reports/team_contributions.csv`)

| Học viên | Git author/email | Module / vai trò | Commit SHA / diff chứng minh | Trình bày? |
|---|---|---|---|---|
| Member 1 | | Integration / CLI | | |
| Member 2 | | Data + GT | | |
| Member 3 | | Core algorithm | | |
| Member 4 | | Metric + tests | | |
| Member 5 | | Review queue + report | | |
| Member 6 (nếu có) | | Research / ablation / debate | | |

## 11 · References

| URL | Ngày xem | 1–2 dòng ý nghĩa (không chép nguyên văn) |
|---|---|---|
| | | |

---

**Bảng 3 · Checklist chốt khi nộp**

- [ ] Link repo và tag cuối cùng trong README; input mẫu không chứa PII thật.
- [ ] Đúng 1 lệnh run, 1 lệnh evaluate, 1 lệnh tests; không cần download khi chạy.
- [ ] Có baseline/PoC metrics, ≥1 failure case, reviewer evidence, decision log.
- [ ] Có license/source provenance, data splits, seed, offline environment, GT/eval N.
- [ ] Mỗi thành viên có ≥1 commit thực chất và được nêu minh bạch trong bảng trên.
