"""Deterministic dataset splitter with stratification, grouping, and deduplication."""

from __future__ import annotations

import hashlib
import logging
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

__all__ = [
    "ErrorCode",
    "Leak",
    "SplitError",
    "SplitResult",
    "__version__",
    "check_leakage",
    "split",
]

__version__ = "0.1.0"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

ErrorCode = Literal["invalid_ratios", "missing_field", "too_many_rows", "field_too_large"]

_WHITESPACE_RE = re.compile(r"\s+")


class SplitError(ValueError):
    """Raised when dataset splitting encounters invalid input or constraints."""

    def __init__(
        self,
        message: str,
        code: ErrorCode,
        *,
        row_index: int | None = None,
    ) -> None:
        super().__init__(message[:200])
        self.code = code
        self.row_index = row_index


@dataclass(frozen=True)
class Leak:
    """Describes a key shared across multiple dataset partitions."""

    key: str
    partitions: tuple[str, ...]


@dataclass(frozen=True)
class SplitResult:
    """Result of splitting a dataset into named partitions."""

    partitions: dict[str, list[Mapping[str, Any]]]
    counts: dict[str, dict[str, int]]
    merged_groups: int
    mixed_strata: int


class _DisjointSet:
    """Union-Find data structure with path compression and rank heuristic."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}
        self._rank: dict[str, int] = {}

    def find(self, item: str) -> str:
        if item not in self._parent:
            self._parent[item] = item
            self._rank[item] = 0
            return item
        root = item
        while root != self._parent[root]:
            root = self._parent[root]
        curr = item
        while curr != root:
            nxt = self._parent[curr]
            self._parent[curr] = root
            curr = nxt
        return root

    def union(self, a: str, b: str) -> bool:
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a == root_b:
            return False
        if self._rank[root_a] < self._rank[root_b]:
            self._parent[root_a] = root_b
        elif self._rank[root_a] > self._rank[root_b]:
            self._parent[root_b] = root_a
        else:
            self._parent[root_b] = root_a
            self._rank[root_a] += 1
        return True


def _normalize_text(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.casefold()).strip()


def _validate_ratios(ratios: Mapping[str, float]) -> None:
    if not ratios:
        raise SplitError("ratios mapping cannot be empty", code="invalid_ratios")
    total = 0.0
    has_positive = False
    for part_name, ratio in ratios.items():
        if not isinstance(ratio, (int, float)) or math.isnan(ratio) or math.isinf(ratio):
            raise SplitError(
                f"ratio for partition '{part_name}' must be a finite number",
                code="invalid_ratios",
            )
        if ratio < 0.0:
            raise SplitError(
                f"ratio for partition '{part_name}' must be non-negative",
                code="invalid_ratios",
            )
        if ratio > 0.0:
            has_positive = True
        total += ratio
    if not has_positive or abs(total - 1.0) > 1e-9:
        raise SplitError(
            f"ratios must sum to 1.0 within 1e-9 and contain a positive value (sum={total})",
            code="invalid_ratios",
        )


def split(
    rows: Sequence[Mapping[str, Any]],
    *,
    ratios: Mapping[str, float],
    seed: str,
    group_by: str | None = None,
    stratify_by: str | None = None,
    text_field: str | None = None,
    max_rows: int = 1_000_000,
    max_field_chars: int = 100_000,
) -> SplitResult:
    """Split rows deterministically into partitions by stratum, group, and seed."""
    _validate_ratios(ratios)

    if len(rows) > max_rows:
        raise SplitError(
            f"row count {len(rows)} exceeds maximum {max_rows}",
            code="too_many_rows",
        )

    partition_names = list(ratios.keys())

    # Step 1: initial groups, strata, and text extraction
    initial_group_keys: list[str] = []
    row_strata: list[str] = []
    text_to_group_keys: dict[str, list[str]] = {}

    for idx, row in enumerate(rows):
        if group_by is not None:
            if group_by not in row:
                raise SplitError(
                    f"row {idx} missing group_by field '{group_by}'",
                    code="missing_field",
                    row_index=idx,
                )
            raw_val = row[group_by]
            str_val = str(raw_val)
            if len(str_val) > max_field_chars:
                raise SplitError(
                    f"row {idx} group_by field '{group_by}' exceeds {max_field_chars} characters",
                    code="field_too_large",
                    row_index=idx,
                )
            g_key = str_val
        else:
            g_key = str(idx)
        initial_group_keys.append(g_key)

        if stratify_by is not None:
            if stratify_by not in row:
                raise SplitError(
                    f"row {idx} missing stratify_by field '{stratify_by}'",
                    code="missing_field",
                    row_index=idx,
                )
            raw_strat = row[stratify_by]
            str_strat = str(raw_strat)
            if len(str_strat) > max_field_chars:
                raise SplitError(
                    f"row {idx} stratify_by '{stratify_by}' exceeds {max_field_chars} chars",
                    code="field_too_large",
                    row_index=idx,
                )
            r_strat = str_strat
        else:
            r_strat = ""
        row_strata.append(r_strat)

        if text_field is not None:
            if text_field not in row:
                raise SplitError(
                    f"row {idx} missing text_field '{text_field}'",
                    code="missing_field",
                    row_index=idx,
                )
            raw_text = row[text_field]
            str_text = str(raw_text)
            if len(str_text) > max_field_chars:
                raise SplitError(
                    f"row {idx} text_field '{text_field}' exceeds {max_field_chars} characters",
                    code="field_too_large",
                    row_index=idx,
                )
            norm = _normalize_text(str_text)
            text_to_group_keys.setdefault(norm, []).append(g_key)

    # Step 2: union-find text duplicates across initial groups
    ds = _DisjointSet()
    for g in initial_group_keys:
        ds.find(g)

    merged_groups = 0
    if text_field is not None:
        for g_list in text_to_group_keys.values():
            first = g_list[0]
            for other in g_list[1:]:
                if ds.union(first, other):
                    merged_groups += 1

    # Map each canonical root to its member initial group keys
    root_to_members: dict[str, set[str]] = {}
    for g in initial_group_keys:
        r = ds.find(g)
        root_to_members.setdefault(r, set()).add(g)

    # The canonical group identifier is the smallest member key
    root_to_canonical: dict[str, str] = {
        r: sorted(members)[0] for r, members in root_to_members.items()
    }

    # Map each row to its final group identifier
    row_canonical_groups: list[str] = [root_to_canonical[ds.find(g)] for g in initial_group_keys]

    # Step 3: group stratum is the stratum of its first row in input order
    canonical_first_stratum: dict[str, str] = {}
    canonical_strata_seen: dict[str, set[str]] = {}
    canonical_row_indices: dict[str, list[int]] = {}

    for idx, (c_grp, strat) in enumerate(zip(row_canonical_groups, row_strata, strict=True)):
        if c_grp not in canonical_first_stratum:
            canonical_first_stratum[c_grp] = strat
            canonical_strata_seen[c_grp] = {strat}
            canonical_row_indices[c_grp] = [idx]
        else:
            canonical_strata_seen[c_grp].add(strat)
            canonical_row_indices[c_grp].append(idx)

    mixed_strata = sum(1 for seen in canonical_strata_seen.values() if len(seen) > 1)

    # Organize canonical groups by their assigned stratum
    stratum_to_groups: dict[str, list[str]] = {}
    stratum_row_count: dict[str, int] = {}
    for c_grp, strat in canonical_first_stratum.items():
        stratum_to_groups.setdefault(strat, []).append(c_grp)
        count = len(canonical_row_indices[c_grp])
        stratum_row_count[strat] = stratum_row_count.get(strat, 0) + count

    # Step 4: per stratum (sorted), order groups by sha256(seed + '\x00' + group_key).hexdigest()
    group_partition_assignment: dict[str, str] = {}
    counts: dict[str, dict[str, int]] = {
        p: {s: 0 for s in stratum_to_groups} for p in partition_names
    }

    for strat in sorted(stratum_to_groups.keys()):
        grps = stratum_to_groups[strat]
        sorted_grps = sorted(
            grps,
            key=lambda gk: hashlib.sha256(f"{seed}\x00{gk}".encode()).hexdigest(),
        )

        total_stratum_rows = stratum_row_count[strat]
        assigned_in_stratum: dict[str, int] = {p: 0 for p in partition_names}

        # Step 5: assign each group to partition with largest deficit: target - assigned
        # target = ratio * total_stratum_rows; tie-break by partition mapping order
        for c_grp in sorted_grps:
            grp_size = len(canonical_row_indices[c_grp])
            best_partition = partition_names[0]
            best_deficit = -float("inf")

            for p in partition_names:
                target = ratios[p] * total_stratum_rows
                deficit = target - assigned_in_stratum[p]
                if deficit > best_deficit:
                    best_deficit = deficit
                    best_partition = p

            group_partition_assignment[c_grp] = best_partition
            assigned_in_stratum[best_partition] += grp_size
            counts[best_partition][strat] += grp_size

    # Step 6: rows keep input order within partition
    partitions: dict[str, list[Mapping[str, Any]]] = {p: [] for p in partition_names}
    for row, c_grp in zip(rows, row_canonical_groups, strict=True):
        p = group_partition_assignment[c_grp]
        partitions[p].append(row)

    return SplitResult(
        partitions=partitions,
        counts=counts,
        merged_groups=merged_groups,
        mixed_strata=mixed_strata,
    )


def check_leakage(
    partitions: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    key: str,
) -> list[Leak]:
    """Return any key values that appear across multiple partitions."""
    key_partitions: dict[str, set[str]] = {}
    for part_name, row_list in partitions.items():
        for row in row_list:
            if key in row:
                val = str(row[key])
                key_partitions.setdefault(val, set()).add(part_name)

    leaks: list[Leak] = []
    for k_val in sorted(key_partitions.keys()):
        parts = key_partitions[k_val]
        if len(parts) > 1:
            leaks.append(Leak(key=k_val, partitions=tuple(sorted(parts))))
    return leaks
