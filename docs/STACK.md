# Stack

## Used

| Tool | Why |
|---|---|
| Python >= 3.10 | Modern typing support. |
| uv | Fast, reproducible environments. |
| hatchling | Standards-based build backend. |
| ruff | Consolidated linting and formatting. |
| mypy (strict) | Strong typing, verified by `py.typed`. |
| pytest + pytest-cov | Test runner and branch coverage. |
| gitleaks | Secret scanning. |

## Discarded

| Tool | Why not |
|---|---|
| Poetry | Slower; `uv` handles dependency groups efficiently. |
| black + isort + flake8 | Replaced by `ruff`. |
| tox / nox | CI handles the OS matrix; single gate script suffices locally. |