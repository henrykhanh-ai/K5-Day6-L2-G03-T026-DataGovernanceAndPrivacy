"""Group tests for the T02 PoC: one success path, edge/failure cases, unit checks of the signals."""
import json

import numpy as np
import pandas as pd
import pytest

from src import main as runner
from src.features_t02 import blockiness, local_glare


def _run(out, *extra):
    return runner.main(["--config", "configs/lab.yaml", "--track", "t02", "--output", str(out),
                        "--run-name", "poc", "--offline", "--seed", "42", *extra])


def test_poc_end_to_end_success(tmp_path):
    out = tmp_path / "poc"
    assert _run(out) == 0
    pred = pd.read_csv(out / "ranked_review.csv")
    assert {"image_id", "score"} <= set(pred.columns)
    assert len(pred) == 96 and pred.image_id.is_unique
    assert set(pred.pred_action) <= {"KEEP", "RECAPTURE"}
    q = pd.read_csv(out / "review_queue.csv")
    assert len(q) == 20 and (out / "contact_sheet.html").exists()
    d = json.loads((out / "decision.json").read_text(encoding="utf-8"))
    assert d["status"] == "HOLD" and d["reason_code"] == "REVIEW_PENDING"     # nobody reviewed yet
    # reproducible: same seed -> byte-identical ranking
    out2 = tmp_path / "poc2"
    assert _run(out2) == 0
    assert (out / "ranked_review.csv").read_text() == (out2 / "ranked_review.csv").read_text()


def test_night_images_are_not_flagged_dark_just_for_being_night(tmp_path):
    out = tmp_path / "poc"
    assert _run(out) == 0
    pred = pd.read_csv(out / "ranked_review.csv")
    night = pred[pred.light == "night"]
    # brightness is normalised per light slice -> most night images must survive as KEEP
    assert (night.pred_action == "KEEP").mean() >= 0.5


def test_review_overrides_apply_and_are_audited(tmp_path):
    out = tmp_path / "poc"
    assert _run(out) == 0
    q = pd.read_csv(out / "review_queue.csv", dtype=str).fillna("")
    q.loc[0, ["reviewer", "reviewer_decision", "review_note"]] = ["tester", "reject", "looks fine"]
    q.loc[1, ["reviewer", "reviewer_decision", "override_value"]] = ["tester", "edit", "blur"]
    q.to_csv(out / "review_queue_reviewed.csv", index=False)
    assert _run(out) == 0
    pred = pd.read_csv(out / "ranked_review.csv").set_index("image_id")
    assert pred.loc[q.item_id[0], "pred_action"] == "KEEP"
    assert pred.loc[q.item_id[1], "pred_defect_type"] == "blur"
    events = [json.loads(l) for l in (out / "audit_log.jsonl").read_text(encoding="utf-8").splitlines()]
    assert sum(e["action"].startswith("override:") for e in events) >= 2
    d = json.loads((out / "decision.json").read_text(encoding="utf-8"))
    assert d["status"] in {"GO", "REWORK"} and d["owner"]


def test_review_without_reviewer_name_fails_loudly(tmp_path):
    out = tmp_path / "poc"
    assert _run(out) == 0
    q = pd.read_csv(out / "review_queue.csv", dtype=str).fillna("")
    q.loc[0, "reviewer_decision"] = "reject"            # decision but no reviewer -> must not pass silently
    q.to_csv(out / "review_queue_reviewed.csv", index=False)
    assert _run(out) != 0


def test_missing_image_file_fails_loudly(tmp_path):
    import shutil
    src = tmp_path / "fx"
    shutil.copytree("fixtures/t02_raw_qc", src)
    (src / "images" / "img_00_0.jpg").unlink()
    rc = runner.main(["--config", "configs/lab.yaml", "--track", "t02", "--input", str(src),
                      "--output", str(tmp_path / "o"), "--offline", "--seed", "42"])
    assert rc != 0


def test_signal_units():
    rng = np.random.default_rng(0)
    smooth = rng.normal(128, 5, (64, 64)).astype(np.float32)
    blocky = np.kron(rng.normal(128, 40, (8, 8)), np.ones((8, 8))).astype(np.float32)
    assert blockiness(blocky, 8) > 3 * blockiness(smooth, 8)
    img = np.full((80, 80), 100.0, dtype=np.float32)
    img[:10, :10] = 255
    assert local_glare(img) == pytest.approx(1.0)
    assert local_glare(np.full((80, 80), 100.0, dtype=np.float32)) == 0.0
