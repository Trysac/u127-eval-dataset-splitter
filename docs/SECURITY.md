# Security Model

## Threat Model & Defenses

- **Unbounded Resource Usage**: The code defends against memory exhaustion by enforcing `max_rows` (default 1,000,000) and `max_field_chars` (default 100,000) per field.
- **Malformed Inputs**: The CLI restricts JSONL line length to 1,000,000 characters to mitigate buffer/parsing issues.
- **Logging**: The application utilizes `logging.NullHandler` by default. Row content is never logged to avoid data leakage into sensitive logs.
- **Insecure Hashing**: Python's `hash()` is non-deterministic across processes. The library strictly uses `hashlib.sha256` for partition assignment to ensure cross-runtime stability.