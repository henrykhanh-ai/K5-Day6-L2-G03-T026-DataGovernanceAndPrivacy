# G03 · T02 Raw QC Triage — Sơ đồ pipeline

Một lệnh (`python -m src.main --config configs/lab.yaml --track t02 --offline --seed 42`) chạy 5 bước. Bước 02 là phần thuật toán của nhóm; bước 04 là chỗ con người duyệt và ký.

## 1. Luồng 5 bước

```mermaid
flowchart LR
    IN[("fixtures/t02_raw_qc<br/>96 ảnh + images.csv<br/>manifest.csv")] --> L

    subgraph PIPE["src/pipeline.py"]
        direction LR
        L["01 load<br/>kiểm sha256 manifest<br/>kiểm đủ file ảnh"] --> P["02 process<br/>4 tín hiệu lỗi<br/>→ score + loại lỗi"]
        P --> R["03 rank<br/>top-B = 20<br/>review_queue.csv<br/>contact_sheet.html"]
        R --> V["04 review<br/>người duyệt:<br/>approve / reject / edit / escalate"]
        V --> D{"05 decide"}
    end

    D -->|"chưa ai duyệt<br/>hoặc có escalate"| HOLD["HOLD"]
    D -->|"RECAPTURE > 15%"| REWORK["REWORK<br/>chụp lại trước khi phát hành"]
    D -->|"RECAPTURE ≤ 15%"| GO["GO"]

    P --> OUT[/"ranked_review.csv<br/>image_id, score,<br/>pred_defect_type, pred_action"/]
    V --> AUD[/"audit_log.jsonl<br/>ai sửa, trước / sau, lý do"/]
    D --> DEC[/"decision.json<br/>reason_code + owner"/]

    classDef core fill:#e8f0fe,stroke:#1a73e8,stroke-width:2px;
    classDef human fill:#fef7e0,stroke:#f9ab00,stroke-width:2px;
    class P core
    class V human
```

## 2. Bước 02: bốn tín hiệu, mỗi tín hiệu so trong "nhóm công bằng"

```mermaid
flowchart TB
    IMG["Ảnh 320×180"] --> F1["Độ nét<br/>Laplacian variance"]
    IMG --> F2["Độ sáng<br/>mean + tỉ lệ pixel tối"]
    IMG --> F3["Lóa cục bộ<br/>ô lưới 8×8 có pixel > 245"]
    IMG --> F4["Vỡ khối JPEG<br/>gradient ở biên 8/16 px"]

    F1 -->|"robust-z trong cùng camera_id<br/>(cam_B vốn mềm hơn)"| Z1["z_blur"]
    F2 -->|"robust-z trong cùng light<br/>(ảnh đêm tối là bình thường)"| Z2["z_dark"]
    F3 -->|"robust-z toàn bộ"| Z3["z_glare"]
    F4 -->|"robust-z toàn bộ"| Z4["z_compression"]

    Z1 & Z2 & Z3 & Z4 --> S["score = max log1p(z)<br/>loại lỗi = tín hiệu lớn nhất"]
    S --> T{"z ≥ 3 ?<br/>(chốt trước khi chấm)"}
    T -->|có| RC["RECAPTURE"]
    T -->|không| KP["KEEP"]
```

Robust-z = (giá trị − trung vị) / (1,4826 × MAD), tính trong từng nhóm; nhóm < 6 ảnh dùng độ phân tán toàn bộ. Không dùng nhãn ở bất kỳ bước nào.

## 3. Vòng human-in-the-loop

```mermaid
sequenceDiagram
    participant P as Pipeline
    participant CS as contact_sheet.html
    participant RV as Reviewer (thành viên nhóm)
    participant A as audit_log.jsonl
    P->>CS: top-20 ảnh + score + loại lỗi gợi ý
    RV->>CS: nhập tên, chọn approve / reject / edit / escalate
    CS-->>RV: Export CSV → review_queue_reviewed.csv
    RV->>P: chép vào out/poc/ rồi chạy lại (task 08)
    P->>A: ghi mỗi thay đổi: ai, trước, sau, lý do
    P->>P: decide() đổi HOLD → GO / REWORK
```

## 4. Baseline so sánh

| | Baseline (`src/baselines/t02_laplacian.py`) | PoC (`src/pipeline.py`) |
|---|---|---|
| Tín hiệu | 1: độ nét Laplacian toàn ảnh | 4: mờ, tối, lóa cục bộ, vỡ khối |
| Chuẩn hoá theo slice | Không | Có: camera cho độ nét, light cho độ sáng |
| Bắt được | Chủ yếu ảnh mờ | Mờ, tối, lóa, vỡ khối |
| Pool / B / seed | 40 ảnh eval / 20 / 42 | 40 ảnh eval / 20 / 42 |
