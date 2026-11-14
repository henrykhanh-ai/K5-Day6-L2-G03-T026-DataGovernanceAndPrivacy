"""T02 baseline required by docs/tracks/T02.md: ONE global Laplacian-variance threshold.

Score = -log(Laplacian variance): the least sharp image is reviewed first. No slice normalisation,
no other signal. Same pool / budget / seed as the PoC.

    python -m src.main --track t02 --pipeline src.baselines.t02_laplacian --output out/baseline --run-name baseline --offline --seed 42
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..common.context import RunContext
from ..common.decision import Decision, write_decision
from ..common.image_ops import laplacian_variance, load_rgb
from ..common.review import make_review_queue, write_review_queue
from ..metrics.tracks import get_track


def run(ctx: RunContext) -> None:
    spec = get_track(ctx.track)
    images = pd.read_csv(ctx.input_dir / "images.csv")
    lap = np.array([laplacian_variance(load_rgb(ctx.input_dir / p)) for p in images.path])
    images["score"] = -np.log(lap + 1.0)
    thr = np.median(images["score"])          # single global cut, no labels
    images["pred_action"] = np.where(images["score"] > thr, "RECAPTURE", "KEEP")
    images["reason"] = "low global sharpness"
    ctx.stats["n_items"] = len(images)
    q = make_review_queue(images, "image_id", "score", int(ctx.param("budget", 20)), reason_col="reason",
                          action_col="pred_action", evidence_col="path")
    write_review_queue(q, ctx.out("review_queue.csv"))
    images.sort_values("score", ascending=False)[["image_id", "score", "pred_action"]].to_csv(ctx.out(spec.pred_file), index=False)
    write_decision(Decision("HOLD", "BASELINE_ONLY", "Global Laplacian baseline: comparison only, never release on it",
                            ctx.config.get("owner", "baseline"), "t02"), ctx.out("decision.json"), ctx.out("decision_log.csv"))
