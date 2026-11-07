"""Comprehensive tests for eval_dataset_splitter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from eval_dataset_splitter import (
    Leak,
    SplitError,
    check_leakage,
    split,
)
from eval_dataset_splitter.__main__ import main


def test_acceptance_split_100_rows() -> None:
    rows = [{"id": i, "val": f"item_{i}"} for i in range(100)]
    res1 = split(rows, ratios={"train": 0.8, "test": 0.2}, seed="a")
    assert len(res1.partitions["train"]) == 80
    assert len(res1.partitions["test"]) == 20

    res2 = split(rows, ratios={"train": 0.8, "test": 0.2}, seed="a")
    assert res1.partitions["train"] == res2.partitions["train"]
    assert res1.partitions["test"] == res2.partitions["test"]

    res3 = split(rows, ratios={"train": 0.8, "test": 0.2}, seed="b")
    assert res1.partitions["test"] != res3.partitions["test"]


def test_acceptance_group_by_leakage() -> None:
    rows = [
        {"conv": "g1", "msg": "hello"},
        {"conv": "g1", "msg": "world"},
        {"conv": "g2", "msg": "foo"},
        {"conv": "g3", "msg": "bar"},
    ]
    res = split(rows, ratios={"train": 0.5, "test": 0.5}, seed="seed1", group_by="conv")
    train_convs = {r["conv"] for r in res.partitions["train"]}
    test_convs = {r["conv"] for r in res.partitions["test"]}
    assert train_convs.isdisjoint(test_convs)
    assert check_leakage(res.partitions, key="conv") == []

    leaky_partitions = {
        "train": [{"conv": "g1"}],
        "test": [{"conv": "g1"}],
    }
    leaks = check_leakage(leaky_partitions, key="conv")
    assert leaks == [Leak(key="g1", partitions=("test", "train"))]


def test_acceptance_text_field_dedup() -> None:
    rows = [
        {"id": 1, "prompt": "Hello  World"},
        {"id": 2, "prompt": "hello world"},
        {"id": 3, "prompt": "different text"},
    ]
    res = split(
        rows,
        ratios={"train": 0.5, "test": 0.5},
        seed="seed_xyz",
        group_by="id",
        text_field="prompt",
    )
    assert res.merged_groups == 1
    part_of_1 = None
    part_of_2 = None
    for p_name, r_list in res.partitions.items():
        for r in r_list:
            if r["id"] == 1:
                part_of_1 = p_name
            if r["id"] == 2:
                part_of_2 = p_name
    assert part_of_1 is not None and part_of_1 == part_of_2


def test_acceptance_stratify_by() -> None:
    rows = [{"id": i, "label": "a"} for i in range(50)] + [
        {"id": i + 50, "label": "b"} for i in range(50)
    ]
    res = split(rows, ratios={"train": 0.8, "test": 0.2}, seed="s", stratify_by="label")
    assert res.counts == {"train": {"a": 40, "b": 40}, "test": {"a": 10, "b": 10}}


def test_acceptance_invalid_ratios_and_missing_field() -> None:
    rows: list[dict[str, Any]] = [{"a": 1}, {"a": 2}, {"a": 3}, {"b": 4}]

    with pytest.raises(SplitError) as exc1:
        split(rows, ratios={"train": 0.5, "test": 0.4}, seed="s")
    assert exc1.value.code == "invalid_ratios"

    with pytest.raises(SplitError) as exc2:
        split(rows, ratios={"train": 1.2, "test": -0.2}, seed="s")
    assert exc2.value.code == "invalid_ratios"

    with pytest.raises(SplitError) as exc3:
        split(rows, ratios={}, seed="s")
    assert exc3.value.code == "invalid_ratios"

    with pytest.raises(SplitError) as exc4:
        split(rows, ratios={"train": 0.5, "test": 0.5}, seed="s", group_by="a")
    assert exc4.value.code == "missing_field"
    assert exc4.value.row_index == 3


def test_acceptance_size_limits() -> None:
    with pytest.raises(SplitError) as exc_rows:
        split([{"x": 1}] * 11, ratios={"train": 1.0}, seed="s", max_rows=10)
    assert exc_rows.value.code == "too_many_rows"

    huge_text = "a" * 100_001
    with pytest.raises(SplitError) as exc_field:
        split(
            [{"text": huge_text}],
            ratios={"train": 1.0},
            seed="s",
            text_field="text",
            max_field_chars=100_000,
        )
    assert exc_field.value.code == "field_too_large"

    accepted_text = "a" * 100_000
    res = split(
        [{"text": accepted_text}],
        ratios={"train": 1.0},
        seed="s",
        text_field="text",
        max_field_chars=100_000,
    )
    assert len(res.partitions["train"]) == 1


def test_acceptance_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    in_file = tmp_path / "in.jsonl"
    rows = [{"id": i, "data": f"v_{i}"} for i in range(10)]
    with in_file.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    ret = main(
        [
            str(in_file),
            "--ratios",
            "train=0.8,test=0.2",
            "--seed",
            "a",
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert ret == 0
    train_out = (tmp_path / "train.jsonl").read_text(encoding="utf-8").strip().splitlines()
    test_out = (tmp_path / "test.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(train_out) == 8
    assert len(test_out) == 2

    parsed_train = [json.loads(line) for line in train_out]
    parsed_test = [json.loads(line) for line in test_out]
    recombined = sorted(parsed_train + parsed_test, key=lambda r: r["id"])
    assert recombined == rows

    # Invalid JSON on line 3
    bad_file = tmp_path / "bad.jsonl"
    bad_file.write_text('{"id": 1}\n{"id": 2}\nINVALID_JSON_LINE\n', encoding="utf-8")
    ret_bad = main(
        [
            str(bad_file),
            "--ratios",
            "train=0.8,test=0.2",
            "--seed",
            "a",
            "--out-dir",
            str(tmp_path),
        ]
    )
    assert ret_bad == 2
    _, stderr = capsys.readouterr()
    assert "line 3: invalid JSON" in stderr


def test_edge_cases_and_coverage(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Ratio zero partition
    rows = [{"id": i} for i in range(5)]
    res = split(rows, ratios={"train": 1.0, "val": 0.0}, seed="x")
    assert len(res.partitions["train"]) == 5
    assert len(res.partitions["val"]) == 0
    assert res.counts["val"] == {"": 0}

    # Single row dataset
    res_one = split([{"id": 1}], ratios={"train": 1.0}, seed="x")
    assert len(res_one.partitions["train"]) == 1
    assert res_one.merged_groups == 0
    assert res_one.mixed_strata == 0

    # Mixed strata in one group
    mixed_rows = [
        {"grp": "g1", "lbl": "cat"},
        {"grp": "g1", "lbl": "dog"},
        {"grp": "g2", "lbl": "cat"},
    ]
    res_mixed = split(
        mixed_rows,
        ratios={"train": 0.5, "test": 0.5},
        seed="seed",
        group_by="grp",
        stratify_by="lbl",
    )
    assert res_mixed.mixed_strata == 1

    # Unicode handling and whitespace normalization
    unicode_rows = [
        {"text": "café   au   lait\n"},
        {"text": "CAFÉ au LAIT"},
    ]
    res_uni = split(
        unicode_rows,
        ratios={"train": 1.0},
        seed="seed",
        text_field="text",
    )
    assert res_uni.merged_groups == 1

    # Missing stratify or text field
    with pytest.raises(SplitError) as err_strat:
        split([{"strat": "val"}, {}], ratios={"train": 1.0}, seed="s", stratify_by="strat")
    assert err_strat.value.code == "missing_field"
    assert err_strat.value.row_index == 1

    with pytest.raises(SplitError) as err_txt:
        split([{"a": 1}], ratios={"train": 1.0}, seed="s", text_field="txt")
    assert err_txt.value.code == "missing_field"
    assert err_txt.value.row_index == 0

    # Field too large for stratify_by and group_by
    with pytest.raises(SplitError) as err_grp_large:
        split(
            [{"grp": "a" * 101}],
            ratios={"train": 1.0},
            seed="s",
            group_by="grp",
            max_field_chars=100,
        )
    assert err_grp_large.value.code == "field_too_large"

    with pytest.raises(SplitError) as err_strat_large:
        split(
            [{"strat": "a" * 101}],
            ratios={"train": 1.0},
            seed="s",
            stratify_by="strat",
            max_field_chars=100,
        )
    assert err_strat_large.value.code == "field_too_large"

    # CLI non-existent file
    assert main(["non_existent_file.jsonl", "--ratios", "train=1.0", "--seed", "s"]) == 2

    # CLI invalid ratio format
    assert main([str(tmp_path / "in.jsonl"), "--ratios", "bad_ratio", "--seed", "s"]) == 2
    assert main([str(tmp_path / "in.jsonl"), "--ratios", "train=abc", "--seed", "s"]) == 2

    # CLI line too long
    long_line_file = tmp_path / "long.jsonl"
    long_line_file.write_text("{" + "a" * 1_000_005 + "}\n", encoding="utf-8")
    assert main([str(long_line_file), "--ratios", "train=1.0", "--seed", "s"]) == 2

    # CLI non-dict JSON
    list_json_file = tmp_path / "list.jsonl"
    list_json_file.write_text("[1, 2, 3]\n", encoding="utf-8")
    assert main([str(list_json_file), "--ratios", "train=1.0", "--seed", "s"]) == 2

    # Empty lines in input JSONL are ignored
    empty_lines_file = tmp_path / "empty.jsonl"
    empty_lines_file.write_text("\n{" + '"x": 1' + "}\n\n", encoding="utf-8")
    assert (
        main(
            [
                str(empty_lines_file),
                "--ratios",
                "train=1.0",
                "--seed",
                "s",
                "--out-dir",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )
