# Deterministic Leakage-Free Dataset Splitting with Union-Find Duplicate Merging

Status: accepted (generated, pending human review)

## Context

Golden dataset evaluation requires determinism across environments without relying on external dependencies like numpy or scikit-learn. Splitting must guarantee that near-identical prompts or rows from the same group never leak across splits while respecting stratum balance.

## Decision

Implement deterministic splitting using SHA-256 seeded hashing and a Disjoint Set Union (union-find) data structure in standard library Python. Ratios and string sizes are validated strictly, and groups are allocated using largest-deficit assignment within each stratum.

## Consequences

Zero runtime dependencies, exact deterministic outputs across Python versions, group-leakage prevention, and bounded memory usage with strict size guards.
