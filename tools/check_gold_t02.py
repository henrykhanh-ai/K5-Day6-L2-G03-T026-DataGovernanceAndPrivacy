"""Kiem tra gold set T02 cua member B + phan tich nguong recapture_z (CHI tren split dev).

    python -m tools.check_gold_t02                       # doc reports/dev_gold_labels.csv
    python -m tools.check_gold_t02 --gold path/to.csv

1) Leakage: moi image_id trong gold phai thuoc split dev; group_id dev/eval khong duoc chong nhau.
2) Chat luong nhan: so dong da gan, defect_type hop le, labeler.
3) Sweep nguong z tren dev: precision / recall / FP so voi gold, va ty le recapture du kien.
   Ty le recapture toan batch chi de doi chieu voi max_recapture_rate - KHONG dung nhan eval.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

FIX = Path("fixtures/t02_raw_qc")
DEFECTS = {"none", "blur", "glare", "dark", "compression"}
Z_RE = re.compile(r"z=([-+]?\d+(?:\.\d+)?)")


def leakage(gold: pd.DataFrame, imgs: pd.DataFrame, man: pd.DataFrame) -> bool:
    split = imgs.set_index("image_id")["split"]
    unknown = sorted(set(gold.image_id) - set(split.index))
    in_eval = sorted(i for i in gold.image_id if split.get(i) == "eval")
    m = man[man.split.isin(["dev", "eval"])]
    cross = sorted(set(m[m.split == "dev"].group_id) & set(m[m.split == "eval"].group_id))
    print("== 1. LEAKAGE ==")
    print(f"  dong trong gold: {len(gold)} | thuoc dev: {sum(split.get(i) == 'dev' for i in gold.image_id)}"
          f" | thuoc EVAL: {len(in_eval)} | khong ton tai: {len(unknown)}")
    if in_eval:
        print(f"  !! CO ANH EVAL TRONG GOLD: {in_eval}")
    if unknown:
        print(f"  !! image_id khong co trong fixture: {unknown}")
    print(f"  group_id chong dev/eval trong manifest: {cross or 'khong'}")
    ok = not in_eval and not unknown
    print("  => " + ("SACH: chi dung split dev" if ok else "LOI: gold dung sai split"))
    return ok


def quality(gold: pd.DataFrame) -> pd.DataFrame:
    g = gold.copy()
    g["defect_type"] = g.defect_type.fillna("").str.strip().str.lower()
    lab = g[g.defect_type != ""]
    bad = sorted(set(lab.defect_type) - DEFECTS)
    no_name = int((lab.get("labeler", pd.Series("", index=lab.index)).fillna("").str.strip() == "").sum())
    print("\n== 2. CHAT LUONG NHAN ==")
    print(f"  da gan: {len(lab)}/{len(g)} (yeu cau ~30) | thieu labeler: {no_name} | defect_type la: {bad or 'khong'}")
    print("  phan bo: " + ", ".join(f"{k}={v}" for k, v in lab.defect_type.value_counts().items()))
    if "light" in lab:
        print("  theo light: " + ", ".join(f"{k}={v}" for k, v in lab.light.value_counts().items()))
    return lab[lab.defect_type.isin(DEFECTS)].assign(is_defect=lambda d: (d.defect_type != "none").astype(int))


def sweep(lab: pd.DataFrame, run: Path, cur_z: float, max_rate: float) -> None:
    rr = pd.read_csv(run)
    rr["z"] = rr["reason"].astype(str).map(lambda s: max([float(x) for x in Z_RE.findall(s)] or [0.0]))
    d = lab.merge(rr[["image_id", "z", "pred_action"]], on="image_id", how="left")
    print(f"\n== 3. SWEEP NGUONG recapture_z (dev, n={len(d)}, so loi that={int(d.is_defect.sum())}) ==")
    print(f"  {'z':>5} {'TP':>3} {'FP':>3} {'FN':>3} {'prec':>5} {'recall':>6} {'rate_dev':>8} {'rate_batch':>10}")
    for z in [2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0]:
        p = (d.z >= z).astype(int)
        tp = int(((p == 1) & (d.is_defect == 1)).sum()); fp = int(((p == 1) & (d.is_defect == 0)).sum())
        fn = int(((p == 0) & (d.is_defect == 1)).sum())
        prec = tp / (tp + fp) if tp + fp else float("nan"); rec = tp / (tp + fn) if tp + fn else float("nan")
        rate_b = (rr.z >= z).mean()
        flag = " <= hien tai" if abs(z - cur_z) < 1e-9 else ""
        flag += "  (vuot max)" if rate_b > max_rate else ""
        print(f"  {z:>5.1f} {tp:>3} {fp:>3} {fn:>3} {prec:>5.2f} {rec:>6.2f} {p.mean():>8.2f} {rate_b:>10.2f}{flag}")
    print(f"  max_recapture_rate = {max_rate:.2f}. Chon nguong tren DEV, ghi bang nay lam evidence; khong nhin eval.")
    fp_rows = d[(d.z >= cur_z) & (d.is_defect == 0)]
    if len(fp_rows):
        print(f"  Anh 'none' bi flag o z={cur_z} (ung vien failure case): {', '.join(fp_rows.image_id)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="reports/dev_gold_labels.csv")
    ap.add_argument("--run", default="out/poc/ranked_review.csv")
    ap.add_argument("--z", type=float, default=3.0)
    ap.add_argument("--max-rate", type=float, default=0.15)
    a = ap.parse_args()
    if not Path(a.gold).exists():
        sys.exit(f"Chua co {a.gold} - doi B push/gui file.")
    gold = pd.read_csv(a.gold, dtype=str)
    imgs = pd.read_csv(FIX / "images.csv"); man = pd.read_csv(FIX / "manifest.csv", dtype=str)
    clean = leakage(gold, imgs, man)
    lab = quality(gold)
    sweep(lab[lab.image_id.isin(imgs.loc[imgs.split == "dev", "image_id"])], Path(a.run), a.z, a.max_rate)
    if not clean:
        sys.exit(2)


if __name__ == "__main__":
    main()
