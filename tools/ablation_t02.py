"""Ablation T02: bo tung tin hieu, do lai Recall@20 / Precision@20 tren gold set DEV.

    python -m tools.ablation_t02            -> reports/ablation_dev.md

Tinh feature 1 lan (giong src/pipeline.py buoc 02), roi voi moi cau hinh bo 1 tin hieu:
score = max log1p(z>=0) cua cac tin hieu con lai; xep hang; cham tren gold set dev (chi split dev).
Khong dung nhan eval, khong sua config. Review cua nguoi khong ap dung (do thuan thuat toan).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.features_t02 import DEFECT_FEATURES, badness_scores, raw_features
from src.internal_eval_t02 import FIXTURE, fmt, load_gold

BUDGET, Z_THR = 20, 3.0
OUT = "reports/ablation_dev.md"


def main() -> None:
    imgs = pd.read_csv(FIXTURE / "images.csv")
    feats = pd.DataFrame([raw_features(FIXTURE / p) for p in imgs.path], index=imgs.index)
    df = badness_scores(pd.concat([imgs, feats], axis=1))
    gold = load_gold()
    pos = set(gold.loc[gold.is_defect == 1, "image_id"])
    configs = [("PoC day du (4 tin hieu)", list(DEFECT_FEATURES))] + \
              [(f"bo `{d}`", [k for k in DEFECT_FEATURES if k != d]) for d in DEFECT_FEATURES]
    rows = []
    for name, keep in configs:
        cols = [DEFECT_FEATURES[k] for k in keep]
        z = df[cols].clip(lower=0)
        score = np.log1p(z).max(axis=1)
        rate = float((z.max(axis=1) >= Z_THR).mean())
        pool = df.assign(score=score)[df.image_id.isin(gold.image_id)]
        top = set(pool.sort_values("score", ascending=False, kind="mergesort").image_id.head(BUDGET))
        tp = len(top & pos)
        per = {d: len(top & set(gold.loc[gold.defect_type == d, "image_id"])) for d in DEFECT_FEATURES}
        rows.append((name, fmt(tp, len(pos)), fmt(tp, BUDGET), f"{rate:.0%}",
                     " · ".join(f"{d} {per[d]}/{int((gold.defect_type == d).sum())}" for d in DEFECT_FEATURES)))
    lines = ["# Ablation T02 tren gold set dev (tu gan, B = 20)", "",
             f"Gold: {len(gold)} anh dev, {len(pos)} anh loi. Khong ap review cua nguoi. Nguong RECAPTURE z >= {Z_THR}.", "",
             "| Cau hinh | Recall@20 | Precision@20 | Ty le RECAPTURE (96 anh) | Loi bat duoc trong top-20 theo loai |",
             "|---|---|---|---|---|", *[f"| {' | '.join(r)} |" for r in rows], ""]
    open(OUT, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines)); print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
