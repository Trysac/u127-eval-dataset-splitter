# eval-dataset-splitter

[![PyPI version](https://img.shields.io/pypi/v/trysac-eval-dataset-splitter)](https://pypi.org/project/trysac-eval-dataset-splitter/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-eval-dataset-splitter)](LICENSE)
[![CI](https://github.com/Trysac/u127-eval-dataset-splitter/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u127-eval-dataset-splitter/actions/workflows/ci.yml)

Split golden evaluation datasets into train, dev and test partitions by stratum with seeded hashing, group-aware and near-duplicate leakage prevention

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-eval-dataset-splitter
# or
uv add trysac-eval-dataset-splitter
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import eval_dataset_splitter

# normalize() trims surrounding whitespace and lower-cases the text.
print(eval_dataset_splitter.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    eval_dataset_splitter.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
