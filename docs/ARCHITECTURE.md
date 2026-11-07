# Architecture

## Pipeline

1. **Validation**: Checks `ratios` sum, non-negativity, and input size constraints.
2. **Group Identification**: Rows are grouped by key. If `text_field` is set, strings are normalized (casefold, whitespace collapse) and unified using Disjoint Set Union (union-find) to merge similar text.
3. **Stratum Association**: Groups inherit the stratum of their first observed row.
4. **Partition Assignment**: Per stratum, groups are ordered by `sha256(seed + \x00 + group_key)`. Groups are assigned to the partition with the maximum `(target_ratio * total_stratum_rows) - assigned_count`.
5. **Output**: Rows are returned in original input order within their partitions.
