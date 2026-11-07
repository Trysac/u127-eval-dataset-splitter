# eval-dataset-splitter

Deterministic, leakage-free evaluation dataset splitting with stratification, group-awareness, and near-duplicate text clustering.

## The Problem

Standard random shuffling of evaluation datasets causes leakage: rows belonging to the same conversation, user session, or near-identical prompts land across train and test partitions, inflating benchmark metrics. Additionally, using Python's default random functions leads to reproducibility issues across different runtime environments.

`eval-dataset-splitter` solves this by assigning groups deterministically using seeded SHA-256 hashing, preserving stratification, and identifying leaks mechanically.

## Usage

```python
from eval_dataset_splitter import check_leakage, split

rows = [{"conv": "c1", "prompt": "Hello world"}, {"conv": "c2", "prompt": "hello  world"}]
result = split(
    rows, ratios={"train": 0.5, "test": 0.5}, seed="s", group_by="conv", text_field="prompt"
)
leaks = check_leakage(result.partitions, key="conv")
assert leaks == []
print(f"Merged groups: {result.merged_groups}")
```

## API Summary

### `split`
Deterministically partitions data.
- **Parameters**: `rows` (Sequence), `ratios` (Mapping), `seed` (str), `group_by` (optional), `stratify_by` (optional), `text_field` (optional).
- **Limits**: `max_rows` (1M), `max_field_chars` (100k).
- **Errors**: `SplitError` (codes: `invalid_ratios`, `missing_field`, `too_many_rows`, `field_too_large`).

### `check_leakage`
Returns a list of `Leak` objects for identifiers found in multiple partitions.

## Why not scikit-learn?

Scikit-learn's `train_test_split` or `GroupShuffleSplit` requires NumPy, does not support text-duplicate merging (grouping normalized variations of the same prompt) and leakage checking in a single pass.

## Documentation
- [Security](docs/SECURITY.md)