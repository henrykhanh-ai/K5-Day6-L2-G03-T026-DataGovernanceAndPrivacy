"""Tests for the reviewer slice table (member C): success path + bad input."""
import pandas as pd
import pytest

from src.review_slices_t02 import build, confirmed, main, report

COLS = ["rank", "item_id", "score", "reason", "suggested_action", "slice", "evidence_path",
        "reviewer", "reviewer_decision", "override_value", "review_note", "reviewed_at"]


def _write(path, rows):
    pd.DataFrame([dict(zip(COLS, r)) for r in rows], columns=COLS).to_csv(path, index=False)


def test_decision_mapping():
    assert confirmed("approve", "") is True
    assert confirmed("reject", "") is False
    assert confirmed("edit", "glare") is True
    assert confirmed("edit", "none") is False          # edit to `none` = image is fine
    assert confirmed("escalate", "") is None           # undecided rows are excluded from the rate
    with pytest.raises(ValueError):
        confirmed("edit", "rain")                      # not a T02 defect type


def test_slice_table_counts_and_wilson(tmp_path):
    f = tmp_path / "reviewed.csv"
    _write(f, [
        (1, "img_23_3", 5.9, "dark (z=365)", "RECAPTURE", "", "", "An", "approve", "", "", ""),
        (2, "img_02_3", 5.6, "dark (z=277)", "RECAPTURE", "", "", "An", "reject", "", "ok", ""),
        (3, "img_17_2", 4.3, "glare (z=77)", "RECAPTURE", "", "", "An", "edit", "blur", "", ""),
        (4, "img_08_3", 5.5, "dark (z=261)", "RECAPTURE", "", "", "An", "escalate", "", "", ""),
    ])
    df = build(f)
    assert df.confirmed.tolist() == [True, False, True, None]
    text = report(df)
    assert "2/3 = 0.67" in text                          # escalate excluded from the denominator
    assert "| pred_defect_type | dark | 3 |" in text      # slice N counts every queued image
    assert "95% CI" in text


def test_unknown_image_and_missing_file_fail_loudly(tmp_path):
    f = tmp_path / "reviewed.csv"
    _write(f, [(1, "img_99_9", 1.0, "dark (z=1)", "RECAPTURE", "", "", "An", "approve", "", "", "")])
    with pytest.raises(ValueError):
        build(f)
    assert main(["--reviewed", str(tmp_path / "nope.csv"), "--out", str(tmp_path / "o.md")]) == 2
