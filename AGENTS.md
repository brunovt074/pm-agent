# PM Agent

## Validation

```bash
ruff check src tests && pytest
```

## Architecture

Hexagonal — domain NEVER imports infrastructure.
Ports = `typing.Protocol`. Adapters implement structurally.
Use cases = pure functions returning frozen dataclasses.
Container = only file importing both domain and infrastructure.
