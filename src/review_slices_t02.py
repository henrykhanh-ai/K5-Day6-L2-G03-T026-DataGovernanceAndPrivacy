"""Slice table for the human review of the T02 top-B queue (member C - Reviewer + slice).

No ground truth needed: the unit is one image in the reviewed top-B queue, and "confirmed" means the
reviewer agreed it is a real defect (approve, or edit to a defect type). This measures *reviewer-judged
precision of the queue*, NOT Recall@B (recall needs labels for images outside the queue).

    python -m src.review_slices_t02                       # reads reports/review_queue.csv
    python -m src.review_slices_t02 --reviewed out/poc/review_queue_reviewed.csv
    -> reports/review_slices.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from .internal_eval_t02 import DEFECTS, FIXTURE, fmt

OUT = Path("reports/review_slices.md")
SLICES = ["light", "camera_id", "split", "pred_defect_type"]


def confirmed(decision: str, override: str) -> bool | None:
    """True = real defect, False = false alarm, None = not decided (skip/escalate/blank)."""
    d, o = decision.strip().lower(), override.strip().lower()
    if d == "approve":
        return True
    if d == "reject":
        return False
    if d == "edit":
        if o not in DEFECTS:
            raise ValueError(f"edit needs override_value in {sorted(DEFECTS)}, got {override!r}")
        return o != "none"
    return None


def build(reviewed_path: Path) -> pd.DataFrame:
    q = pd.read_csv(reviewed_path, dtype=str).fillna("")
    imgs = pd.read_csv(FIXTURE / "images.csv", dtype=str)
    df = q.merge(imgs[["image_id", "camera_id", "light", "split"]], left_on="item_id", right_on="image_id", how="left")
    if df.image_id.isna().any():
        raise ValueError(f"unknown image ids in review file: {df.loc[df.image_id.isna(), 'item_id'].tolist()}")
    df["pred_defect_type"] = df.reason.str.split(" ").str[0]
    df["confirmed"] = [confirmed(d, o) for d, o in zip(df.reviewer_decision, df.override_value)]
    return df


def report(df: pd.DataFrame) -> str:
    decided = df[df.confirmed.notna()]
    k, n = int(decided.confirmed.sum()), len(decided)
    lines = ["# T02 · Kết quả human review theo slice (thành viên C)", "",
             f"- File review: `reports/review_queue.csv` · B = {len(df)} ảnh · reviewer: "
             f"{', '.join(sorted(set(df.reviewer) - {''}))}",
             f"- Quyết định: {df.reviewer_decision.value_counts().to_dict()}",
             f"- **Precision của queue theo reviewer** (ảnh được xác nhận lỗi / ảnh đã quyết định): {fmt(k, n)}",
             "- Đây KHÔNG phải Recall@20: muốn có recall cần nhãn cho cả ảnh ngoài queue (gold set dev của B, "
             "hoặc GT ẩn của giảng viên trên eval).",
             "- N mỗi slice rất nhỏ nên khoảng tin cậy Wilson 95% rất rộng; chỉ đọc như tín hiệu, không kết luận mạnh.",
             "", "| Slice | Giá trị | N trong queue | Xác nhận lỗi (Wilson 95% CI) | False alarm |",
             "|---|---|---|---|---|"]
    for col in SLICES:
        for val, sub in df.groupby(col, sort=True):
            s = sub[sub.confirmed.notna()]
            kk, nn = int(s.confirmed.sum()), len(s)
            lines.append(f"| {col} | {val} | {len(sub)} | {fmt(kk, nn)} | {nn - kk} |")
    lines += ["", "Slice có N nhỏ (ví dụ cam_B, night) chỉ có vài ảnh trong queue: CI rộng, cần gold set dev "
              "để biết pipeline có bỏ sót lỗi ở slice đó hay không.", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reviewed", type=Path, default=Path("reports/review_queue.csv"))
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)
    if not a.reviewed.exists():
        print(f"missing {a.reviewed}: export the contact sheet and copy it first", file=sys.stderr)
        return 2
    text = report(build(a.reviewed))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
