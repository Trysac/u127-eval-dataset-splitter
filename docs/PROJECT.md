# Project Record

## Objective

Split golden evaluation datasets into train, dev, and test partitions by stratum with seeded hashing, group-aware and near-duplicate leakage prevention.

## Scope

- Public API: `split`, `check_leakage`, `SplitResult`, `Leak`, `SplitError`.
- CLI interface: `eval-dataset-splitter` entry point.
- Input validation and deterministic partitioning.

## Out of Scope

- K-fold cross-validation.
- Temporal or sequence-based splitting strategies.
- Embedding-based deduplication.

## Effort Metrics

| Metric | Value |
|---|---|
| Tokens (input / output) | 1605791 / 18648 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.3082 |

## Factory run u127 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 4216 | 9931 | 0 | 0 | 0.0202 |
| fix-1 | gemini-3.8-flash | no | 57916 | 1191 | 0 | 341497 | 0.0735 |
| fix-2 | gemini-3.8-flash | no | 13460 | 240 | 0 | 9123 | 0.0117 |
| audit | gemini-3.1-flash-lite | no | 44603 | 286 | 0 | 159026 | 0.0156 |
| fix-3 | gemini-3.8-flash | no | 90430 | 5339 | 0 | 711126 | 0.1412 |
| docs | gemini-3.1-flash-lite | no | 174394 | 1661 | 0 | 0 | 0.0461 |

Total: $0.3082. Prices: Anthropic list prices.
