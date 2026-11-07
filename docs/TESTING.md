# Testing

## Files

- `tests/test_eval_dataset_splitter.py`: Covers the full acceptance suite.

## Coverage

- 100-row splits: Verification of partition counts and reproducibility with identical seeds.
- Group leakage: Validation that `group_by` constraints are respected; `check_leakage` detection.
- Text deduplication: Using union-find to ensure near-duplicates share partitions.
- Stratification: Ensuring label distribution matches requested ratios.
- Validation: Testing `SplitError` conditions (invalid ratios, missing fields).
- Limits: Verification of `too_many_rows` and `field_too_large` error triggers.
- CLI: Testing input/output file handling and standard error reporting for invalid JSON.