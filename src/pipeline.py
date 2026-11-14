"""T02 Raw QC Triage — PoC pipeline (5 steps, one command).

    python -m src.main --config configs/lab.yaml --track t02 --output out/poc --run-name poc --offline --seed 42

01 load     images.csv + provenance check (manifest sha256)
02 process  4 label-free badness signals (blur / dark / glare / compression), each normalised in its
            fair slice: sharpness per camera (cam_B is softer), brightness per light (night is dark by design)
03 rank     top-B (B=20) by score -> review_queue.csv + contact_sheet.html
04 review   reviewer decisions (out/poc/review_queue_reviewed.csv) -> overrides + audit_log.jsonl
05 decide   GO / HOLD / REWORK for the batch, with reason_code + owner

All thresholds are frozen in configs/tracks/t02.yaml / configs/lab.yaml BEFORE any evaluation.
Never reads fixtures/*/gt/.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common.contact_sheet import render_contact_sheet
from .common.context import RunContext
from .common.decision import Decision, write_decision
from .common.manifest import verify_manifest
from .common.review import load_review_decisions, make_review_queue, write_review_queue
from .features_t02 import DEFECT_FEATURES, badness_scores, raw_features
from .metrics.tracks import get_track

ACTIONS = {"KEEP", "RECAPTURE"}
DEFECTS = {"none", "blur", "glare", "dark", "compression"}


# ---------------------------------------------------------------- 01 load
def load(ctx: RunContext) -> dict:
    manifest = ctx.input_dir / "manifest.csv"
    problems = verify_manifest(manifest) if manifest.exists() else [{"problem": "no_manifest"}]
    if problems:
        ctx.audit.log(actor="pipeline", action="provenance_problems", item_id=str(manifest), after=problems[:20])
        if ctx.config.get("strict_provenance", True):
            raise ValueError(f"provenance check failed ({len(problems)} problems), first: {problems[:3]}")
    images = pd.read_csv(ctx.input_dir / "images.csv")
    need = {"image_id", "path", "camera_id", "light", "split"}
    if not need.issubset(images.columns):
        raise ValueError(f"images.csv missing columns {sorted(need - set(images.columns))}")
    missing = [p for p in images.path if not (ctx.input_dir / p).exists()]
    if missing:
        raise FileNotFoundError(f"{len(missing)} image files missing, first: {missing[:3]}")
    ctx.audit.log(actor="pipeline", action="load", item_id="images.csv", after={"n_images": len(images)})
    return {"images": images}


# ---------------------------------------------------------------- 02 process
def process(ctx: RunContext, data: dict) -> pd.DataFrame:
    images = data["images"]
    feats = pd.DataFrame([raw_features(ctx.input_dir / p) for p in images.path], index=images.index)
    df = badness_scores(pd.concat([images, feats], axis=1))

    cols = list(DEFECT_FEATURES.values())
    z = df[cols].clip(lower=0)
    # log1p puts the four signals on a comparable scale (a 270-sigma dark image and a 10-sigma blur
    # are both "certainly defective"; only the order inside each signal matters).
    comp = np.log1p(z)
    df["score"] = comp.max(axis=1).round(6)
    inv = {v: k for k, v in DEFECT_FEATURES.items()}
    df["pred_defect_type"] = comp.idxmax(axis=1).map(inv)

    z_thr = float(ctx.param("recapture_z", 3.0))
    df.loc[z.max(axis=1) < z_thr, "pred_defect_type"] = "none"
    df["pred_action"] = np.where(df.pred_defect_type == "none", "KEEP", "RECAPTURE")
    df["reason"] = df.apply(lambda r: f"{r.pred_defect_type} (z={max(r[c] for c in cols):.1f})", axis=1)
    df["slice"] = df.camera_id + "/" + df.light
    ctx.stats["n_recapture"] = int((df.pred_action == "RECAPTURE").sum())
    return df


# ---------------------------------------------------------------- 03 rank
def rank(ctx: RunContext, scored: pd.DataFrame) -> pd.DataFrame:
    budget = int(ctx.param("budget", 20))
    q = make_review_queue(scored, id_col="image_id", score_col="score", budget=budget, reason_col="reason",
                          action_col="pred_action", slice_col="slice", evidence_col="path")
    write_review_queue(q, ctx.out("review_queue.csv"))
    render_contact_sheet(q, ctx.out("contact_sheet.html"), image_root=ctx.input_dir,
                         title=f"T02 Raw QC — top-{budget} review queue")
    return q


# ---------------------------------------------------------------- 04 review
def review(ctx: RunContext, scored: pd.DataFrame, queue: pd.DataFrame) -> pd.DataFrame:
    """Apply human decisions. Meaning for T02:

    approve  -> keep the pipeline's suggestion
    reject   -> the image is fine: pred_action=KEEP, pred_defect_type=none
    edit     -> override_value = a defect type (blur/glare/dark/compression) -> RECAPTURE with that type,
                or `none` -> KEEP
    escalate -> HOLD the batch decision until a second reviewer looks
    skip     -> no change
    Raw scores are never changed; the diff lives in audit_log.jsonl.
    """
    final = scored.copy()
    reviewed_path = ctx.output_dir / "review_queue_reviewed.csv"
    if not reviewed_path.exists():
        ctx.stats["n_reviewed"] = 0
        return final
    reviewed = load_review_decisions(reviewed_path)
    ctx.stats["n_reviewed"] = len(reviewed)
    ctx.stats["n_escalated"] = int((reviewed.reviewer_decision == "escalate").sum())
    idx = final.set_index("image_id").index
    for r in reviewed.itertuples(index=False):
        if r.item_id not in idx:
            continue
        m = final.image_id == r.item_id
        before = final.loc[m, ["pred_action", "pred_defect_type"]].iloc[0].to_dict()
        if r.reviewer_decision == "reject":
            after = {"pred_action": "KEEP", "pred_defect_type": "none"}
        elif r.reviewer_decision == "edit":
            v = str(r.override_value).strip().lower()
            if v not in DEFECTS:
                raise ValueError(f"edit on {r.item_id}: override_value must be one of {sorted(DEFECTS)}, got {v!r}")
            after = {"pred_action": "KEEP" if v == "none" else "RECAPTURE", "pred_defect_type": v}
        else:
            ctx.audit.log(actor=r.reviewer, action=f"review:{r.reviewer_decision}", item_id=r.item_id,
                          before=before, after=before, reason=r.review_note)
            continue
        final.loc[m, ["pred_action", "pred_defect_type"]] = [after["pred_action"], after["pred_defect_type"]]
        ctx.audit.log(actor=r.reviewer, action=f"override:{r.reviewer_decision}", item_id=r.item_id,
                      before=before, after=after, reason=r.review_note)
    return final


# ---------------------------------------------------------------- 05 decide
def decide(ctx: RunContext, final: pd.DataFrame) -> Decision:
    owner = ctx.config.get("owner", "TODO-owner")
    rate = float((final.pred_action == "RECAPTURE").mean())
    max_rate = float(ctx.param("max_recapture_rate", 0.15))
    metrics = {"n_images": len(final), "recapture_rate": round(rate, 4), "max_recapture_rate": max_rate,
               "n_reviewed": ctx.stats.get("n_reviewed", 0)}
    if ctx.stats.get("n_reviewed", 0) == 0:
        return Decision("HOLD", "REVIEW_PENDING", "Top-B queue not reviewed by a human yet", owner, "t02", metrics=metrics)
    if ctx.stats.get("n_escalated", 0):
        return Decision("HOLD", "ESCALATED_ITEMS", "A reviewer escalated items; second review needed", owner, "t02", metrics=metrics)
    if rate > max_rate:
        return Decision("REWORK", "RECAPTURE_RATE_HIGH",
                        f"{rate:.0%} of images need recapture (> {max_rate:.0%}); recapture before release", owner, "t02", metrics=metrics)
    return Decision("GO", "QC_PASSED", f"Recapture rate {rate:.0%} within limit; flagged images excluded", owner, "t02", metrics=metrics)


def run(ctx: RunContext) -> None:
    if ctx.track != "t02":
        raise NotImplementedError(f"this group's pipeline implements t02 only (got {ctx.track})")
    spec = get_track(ctx.track)
    data = load(ctx)
    scored = process(ctx, data)
    ctx.stats["n_items"] = len(scored)
    queue = rank(ctx, scored)
    final = review(ctx, scored, queue)
    cols = spec.pred_columns + ["pred_defect_type", "pred_action", "reason", "camera_id", "light", "split"]
    final.sort_values("score", ascending=False)[cols].to_csv(ctx.out(spec.pred_file), index=False)
    write_decision(decide(ctx, final), ctx.out("decision.json"), ctx.out("decision_log.csv"))
