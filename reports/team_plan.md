# Ke hoach nhom 4 nguoi - T02 Raw QC Triage

Bai toan: xep hang 96 anh (40 anh split eval) theo muc nghi loi (blur / glare / dark / compression) de nguoi duyet
B=20 anh bat duoc nhieu loi nhat; quyet dinh KEEP / RECAPTURE. Metric chinh: **Defect Recall@20 + Precision@20** tren split eval.
Baseline: 1 nguong Laplacian toan anh (`src/baselines/t02_laplacian.py`).

## Trang thai hien tai (14/11, Henry)

Da xong va chay duoc 1 lenh (`Ctrl+Shift+B` trong VS Code):
- `src/features_t02.py`: 4 tin hieu khong can nhan - blur (so theo camera), dark (so theo light), glare cuc bo (theo o luoi), blockiness (bien 8/16 px)
- `src/pipeline.py`: du 5 buoc load -> process -> rank -> review -> decide, contact sheet HTML, audit log, GO/HOLD/REWORK
- `src/baselines/t02_laplacian.py`: baseline bat buoc
- `tests/test_t02_pipeline.py`: 6 test (thanh cong, anh dem, override + audit, thieu reviewer, thieu file anh, unit tin hieu) -> pytest 53 passed, 0 failed
- `configs/lab.yaml`: chot nguong (z >= 3, REWORK neu > 15% RECAPTURE), `reports/metric_contract.md` da dien

## Phan vai con lai (moi nguoi tu lam + tu commit duoi ten minh)

| # | Thanh vien | Vai | Viec cu the | Bang chung trong repo |
|---|---|---|---|---|
| A | Henry | Lead / Core algorithm | Pipeline + tin hieu + baseline + test (da xong); tich hop PR, tag demo | `src/`, `tests/`, `configs/` |
| B | ____ | Gold set + failure mode | Tu gan tay nhan loi cho ~30 anh split **dev** (khong dung eval); chay danh gia noi bo; tim 2 failure case co anh | `reports/dev_gold_labels.csv`, muc failure trong report, anh trong `demo/` |
| C | ____ | Reviewer + slice/do bat dinh | Mo contact sheet, duyet 20 anh (approve/reject/edit) ghi ten minh, Export CSV, chay lai -> audit log; viet bang slice (light, camera) + Wilson CI | `out/poc/audit_log.jsonl` -> chep `reports/review_queue.csv`, muc Results trong report |
| D | ____ | Report + demo | Dien `reports/group_report.md` (3-5 trang), 3-5 slide, ablation (bo tung tin hieu) bang lenh co san | `reports/group_report.md`, `demo/` |

Quy uoc Git: moi nguoi lam tren nhanh `feat/<ten>`, PR vao `main`. Moi nguoi >= 2 commit thuc chat do chinh minh tao
(rubric doi chieu `git shortlog -sne --all` voi `reports/team_contributions.csv`).

## Task list

### B - Gold set + failure mode
- [ ] Mo `fixtures/t02_raw_qc/images/` (split dev), gan tay `defect_type` cho ~30 anh -> `reports/dev_gold_labels.csv` (`image_id,defect_type,is_defect,labeler`)
- [ ] Tinh Recall@20 / Precision@20 noi bo tren dev cho baseline va PoC (ghi ro day la gold set tu gan)
- [ ] 2 failure case: (1) anh loi bi xep thap, (2) anh tot bi xep cao; chup anh + root cause

### C - Reviewer + slice
- [ ] Task VS Code "07 Mo contact sheet" -> nhap ten, chon quyet dinh cho 20 anh, Export CSV
- [ ] Task "08 Ap review" -> kiem `out/poc/audit_log.jsonl` co ten minh, `decision.json` doi tu HOLD sang GO/REWORK
- [ ] Bang ket qua theo slice `light` va `camera_id` + Wilson 95% CI

### D - Report + demo
- [ ] `reports/group_report.md`: problem, data & provenance, design, ket qua, human-in-loop, failure, rui ro
- [ ] Ablation: tat tung tin hieu (sua `src/pipeline.py` tren nhanh rieng), ghi bang
- [ ] 3-5 slide: van de -> baseline vs PoC -> review -> quyet dinh -> failure case

### A - Henry
- [ ] Tao repo nhom, moi 3 thanh vien, push code hien tai
- [ ] Review + merge PR cua B, C, D
- [ ] Tag `demo-180m` (task 11) va `final-24h` (task 12)
