"""Image-quality features for T02 Raw QC Triage (no labels needed).

Each feature is a "badness" signal: higher = more likely defective.
  blur         : low Laplacian variance (sharpness)          -> blur
  dark         : low mean brightness / many dark pixels       -> dark
  glare_local  : a small tile that is almost fully saturated  -> glare (local, e.g. on a plate)
  blockiness   : gradient jumps on 8/16-px block borders      -> compression
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .common.image_ops import brightness_stats, laplacian_variance, load_rgb, to_gray

DEFECT_FEATURES = {"blur": "f_blur", "dark": "f_dark", "glare": "f_glare", "compression": "f_block"}


def blockiness(gray: np.ndarray, block: int) -> float:
    """Mean |gradient| on block borders divided by mean |gradient| elsewhere (≈1 for natural images)."""
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    cols = np.arange(gx.shape[1])
    rows = np.arange(gy.shape[0])
    on_x = (cols % block) == block - 1
    on_y = (rows % block) == block - 1
    border = np.concatenate([gx[:, on_x].ravel(), gy[on_y, :].ravel()])
    inner = np.concatenate([gx[:, ~on_x].ravel(), gy[~on_y, :].ravel()])
    return float(border.mean() / (inner.mean() + 1e-6))


def local_glare(gray: np.ndarray, tiles: int = 8) -> float:
    """Largest fraction of near-white pixels in any tile of a tiles×tiles grid."""
    H, W = gray.shape
    best = 0.0
    for i in range(tiles):
        for j in range(tiles):
            t = gray[i * H // tiles:(i + 1) * H // tiles, j * W // tiles:(j + 1) * W // tiles]
            best = max(best, float((t > 245).mean()))
    return best


def raw_features(path: str | Path) -> dict:
    img = load_rgb(path)
    g = to_gray(img)
    b = brightness_stats(img)
    return {
        "lap_var": laplacian_variance(img),
        "mean": b["mean"],
        "frac_dark": b["frac_dark"],
        "frac_sat": b["frac_saturated"],
        "glare_tile": local_glare(g),
        "block8": blockiness(g, 8),
        "block16": blockiness(g, 16),
    }


def robust_z(x: pd.Series, groups: pd.Series) -> pd.Series:
    """(x - median) / (1.4826·MAD) inside each group; falls back to the global spread for tiny groups."""
    out = pd.Series(0.0, index=x.index)
    gmad = 1.4826 * (x - x.median()).abs().median() + 1e-9
    for _, idx in x.groupby(groups).groups.items():
        v = x.loc[idx]
        med = v.median()
        mad = 1.4826 * (v - med).abs().median()
        scale = mad if (len(v) >= 6 and mad > 1e-9) else gmad
        out.loc[idx] = (v - med) / scale
    return out


def badness_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Turn raw features into per-defect badness z-scores, normalised within the right slice.

    - sharpness is compared inside each camera (cam_B has softer optics -> no false blur alarms)
    - brightness is compared inside each `light` slice (night is dark by design -> not a defect)
    - glare / blockiness are compared over all images
    """
    out = df.copy()
    out["f_blur"] = -robust_z(np.log(out.lap_var + 1.0), out.camera_id)
    out["f_dark"] = -robust_z(out["mean"], out.light) + robust_z(out.frac_dark, out.light).clip(lower=0) * 0.5
    out["f_glare"] = robust_z(out.glare_tile, pd.Series("all", index=out.index))
    out["f_block"] = robust_z(out[["block8", "block16"]].max(axis=1), pd.Series("all", index=out.index))
    return out
