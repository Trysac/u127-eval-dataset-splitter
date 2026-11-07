"""CLI entry point for eval_dataset_splitter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from eval_dataset_splitter import SplitError, split

MAX_LINE_LENGTH = 1_000_000


def parse_ratios(ratios_str: str) -> dict[str, float]:
    """Parse comma-separated key=value ratio pairs."""
    ratios: dict[str, float] = {}
    pairs = ratios_str.split(",")
    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue
        if "=" not in pair:
            raise ValueError(f"Invalid ratio format: '{pair}', expected name=value")
        name, val_str = pair.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError("Partition name cannot be empty")
        try:
            ratios[name] = float(val_str.strip())
        except ValueError as exc:
            raise ValueError(f"Invalid float ratio for '{name}': '{val_str}'") from exc
    return ratios


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval-dataset-splitter",
        description="Deterministic, leakage-free dataset splitter.",
    )
    parser.add_argument("input_file", help="Path to input JSONL file")
    parser.add_argument(
        "--ratios",
        required=True,
        help="Comma-separated ratios, e.g. 'train=0.8,test=0.2'",
    )
    parser.add_argument("--seed", required=True, help="Seed string for deterministic hashing")
    parser.add_argument("--out-dir", default=".", help="Output directory for partition files")
    parser.add_argument("--group-by", default=None, help="Field name to group rows by")
    parser.add_argument("--stratify-by", default=None, help="Field name to stratify rows by")
    parser.add_argument("--text-field", default=None, help="Field name to deduplicate text on")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code != 0 else 0

    try:
        ratios = parse_ratios(args.ratios)
    except Exception as exc:
        sys.stderr.write(f"Error parsing ratios: {exc}\n")
        return 2

    input_path = Path(args.input_file)
    if not input_path.exists():
        sys.stderr.write(f"Input file not found: {args.input_file}\n")
        return 2

    rows: list[dict[str, Any]] = []
    try:
        with input_path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                if len(line) > MAX_LINE_LENGTH:
                    sys.stderr.write(f"line {line_no}: exceeds maximum length\n")
                    return 2
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                    if not isinstance(row, dict):
                        sys.stderr.write(f"line {line_no}: invalid JSON\n")
                        return 2
                    rows.append(row)
                except Exception:
                    sys.stderr.write(f"line {line_no}: invalid JSON\n")
                    return 2
    except Exception as exc:
        sys.stderr.write(f"IO error reading {args.input_file}: {exc}\n")
        return 2

    try:
        result = split(
            rows,
            ratios=ratios,
            seed=args.seed,
            group_by=args.group_by,
            stratify_by=args.stratify_by,
            text_field=args.text_field,
        )
    except SplitError as exc:
        sys.stderr.write(f"Split error: {exc}\n")
        return 2

    out_dir = Path(args.out_dir)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        for part_name, part_rows in result.partitions.items():
            part_path = out_dir / f"{part_name}.jsonl"
            with part_path.open("w", encoding="utf-8") as out_f:
                for r in part_rows:
                    out_f.write(json.dumps(r, ensure_ascii=False) + "\n")
    except Exception as exc:
        sys.stderr.write(f"IO error writing partitions: {exc}\n")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
