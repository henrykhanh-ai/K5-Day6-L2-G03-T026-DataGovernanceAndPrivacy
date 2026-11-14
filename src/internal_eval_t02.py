"""Internal (self-labelled) evaluation for T02 on the DEV split only.

The student repo has no ground truth, so the group builds its own small gold set on `dev` and
measures baseline vs PoC there. The official score stays the instructor's run on `eval`.

Step 1 (member B) - make the labelling sheet + a picture gallery:
    python -m src.internal_eval_t02 template
    -> reports/dev_gold_labels.csv      fill: defect_type (none/blur/glare/dark/compression), labeler
    -> reports/dev_gold_gallery.html    open in a browser while labelling

Step 2 (member B/C) - after running baseline + PoC:
    python -m src.internal_eval_t02 evaluate
    -> reports/internal_eval_dev.md     Recall@B / Precision@B with Wilson 95% CI, slices by light & camera
"""
from __future__ import annotations

import argparse
import base64
import io
import math
import sys
from pathlib import Path

import pandas as pd
from PIL import Image

FIXTURE = Path("fixtures/t02_raw_qc")
GOLD = Path("reports/dev_gold_labels.csv")
GALLERY = Path("reports/dev_gold_gallery.html")
REPORT = Path("reports/internal_eval_dev.md")
DEFECTS = {"none", "blur", "glare", "dark", "compression"}
RUNS = {"baseline": Path("out/baseline/ranked_review.csv"), "poc": Path("out/poc/ranked_review.csv")}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% interval for k successes out of n (good for small n)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def fmt(k: int, n: int) -> str:
    if n == 0:
        return "n/a (0 mẫu)"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.2f} (95% CI {lo:.2f}–{hi:.2f})"


def make_template() -> None:
    imgs = pd.read_csv(FIXTURE / "images.csv")
    dev = imgs[imgs.split == "dev"].reset_index(drop=True)
    if GOLD.exists():
        sys.exit(f"{GOLD} already exists - not overwriting labels. Delete it first if you really want a fresh sheet.")
    sheet = dev[["image_id", "camera_id", "light"]].assign(defect_type="", labeler="", note="")
    GOLD.parent.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(GOLD, index=False)
    cards = []
    for r in dev.itertuples():
        buf = io.BytesIO()
        Image.open(FIXTURE / r.path).save(buf, "JPEG", quality=90)
        uri = base64.b64encode(buf.getvalue()).decode()
        cards.append(f"<figure><img src='data:image/jpeg;base64,{uri}' alt='{r.image_id}'>"
                     f"<figcaption><b>{r.image_id}</b> · {r.camera_id} · {r.light}</figcaption></figure>")
    GALLERY.write_text(
        "<!DOCTYPE html><html lang='vi'><meta charset='utf-8'><title>T02 dev gold set</title>"
        "<style>body{font:14px sans-serif;margin:16px;background:#f5f6f8}main{display:flex;flex-wrap:wrap;gap:10px}"
        "figure{margin:0;background:#fff;padding:6px;border-radius:8px}img{width:320px;display:block}</style>"
        f"<h1>T02 · {len(dev)} ảnh split dev để tự gán nhãn</h1>"
        "<p>Mở song song với <code>reports/dev_gold_labels.csv</code>. Mỗi ảnh điền <code>defect_type</code>: "
        "none / blur / glare / dark / compression, và tên mình ở cột <code>labeler</code>. "
        "Nhìn thấy lỗi rõ thì ghi loại lỗi, không chắc thì ghi vào cột note. Ảnh ban đêm tối là bình thường.</p>"
        f"<main>{''.join(cards)}</main></html>", encoding="utf-8")
    print(f"wrote {GOLD} ({len(dev)} rows) and {GALLERY}")


def load_gold() -> pd.DataFrame:
    if not GOLD.exists():
        sys.exit(f"{GOLD} not found - run `python -m src.internal_eval_t02 template` first")
    g = pd.read_csv(GOLD, dtype=str).fillna("")
    g["defect_type"] = g.defect_type.str.strip().str.lower()
    g = g[g.defect_type != ""]
    bad = sorted(set(g.defect_type) - DEFECTS)
    if bad:
        sys.exit(f"unknown defect_type values {bad}; allowed {sorted(DEFECTS)}")
    if (g.labeler.str.strip() == "").any():
        sys.exit("every labelled row needs a `labeler` name")
    imgs = pd.read_csv(FIXTURE / "images.csv")
    if set(g.image_id) - set(imgs.loc[imgs.split == "dev", "image_id"]):
        sys.exit("gold set must contain dev images only (never label the eval split)")
    g["is_defect"] = (g.defect_type != "none").astype(int)
    return g


def evaluate(budget: int) -> None:
    gold = load_gold()
    pos = set(gold.loc[gold.is_defect == 1, "image_id"])
    lines = ["# Đánh giá nội bộ T02 trên split dev (gold set tự gán)", "",
             f"- Gold set: {len(gold)} ảnh dev đã gán, {len(pos)} ảnh lỗi; người gán: {', '.join(sorted(set(gold.labeler)))}",
             f"- Budget B = {budget} trên pool {len(gold)} ảnh đã gán; khoảng tin cậy Wilson 95%",
             "- Đây là số tự kiểm, **không phải điểm chính thức** (giảng viên chấm trên split eval bằng ground truth ẩn).", ""]
    summary, slices = [], []
    for name, path in RUNS.items():
        if not path.exists():
            lines.append(f"> Thiếu `{path}` - chạy {name} trước.")
            continue
        pred = pd.read_csv(path)
        pred = pred[pred.image_id.isin(gold.image_id)].sort_values("score", ascending=False, kind="mergesort")
        top = set(pred.image_id.head(budget))
        tp = len(top & pos)
        summary.append(f"| {name} | {fmt(tp, len(pos))} | {fmt(tp, min(budget, len(pred)))} |")
        g = gold.assign(in_top=gold.image_id.isin(top).astype(int))
        for col in ("light", "camera_id"):
            for val, sub in g.groupby(col):
                p, n = sub[sub.is_defect == 1], sub[sub.is_defect == 0]
                slices.append(f"| {name} | {col}={val} | {len(sub)} | {fmt(int(p.in_top.sum()), len(p))} | "
                              f"{fmt(int(n.in_top.sum()), len(n))} |")
        if "pred_defect_type" in pred.columns:
            m = gold[gold.is_defect == 1].merge(pred[["image_id", "pred_defect_type"]], on="image_id")
            ok = int((m.defect_type == m.pred_defect_type).sum())
            summary[-1] += f" loại lỗi đúng: {fmt(ok, len(m))} |"
        else:
            summary[-1] += " – |"
    lines += ["## Kết quả chính", "", "| Run | Recall@B | Precision@B | Loại lỗi đúng (trên ảnh lỗi) |", "|---|---|---|---|", *summary, "",
              "## Theo slice", "", "| Run | Slice | N | Recall trong top-B (ảnh lỗi) | False alarm trong top-B (ảnh sạch) |",
              "|---|---|---|---|---|", *slices, ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {REPORT}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["template", "evaluate"])
    ap.add_argument("--budget", type=int, default=20)
    a = ap.parse_args(argv)
    make_template() if a.cmd == "template" else evaluate(a.budget)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
