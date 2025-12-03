# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python SDK and CLI for managing Databricks Genie Spaces via the Import/Export API. Enables CI/CD workflows, cross-workspace migrations, and programmatic space management.

> **Pre-Private Preview**: This API is in pre-private preview and may change.

## Common Commands

```bash
# Install dependencies (creates .venv automatically)
uv sync

# Run tests
uv run pytest
uv run pytest -v                    # verbose
uv run pytest tests/test_models.py  # single file
uv run pytest -k "test_export"      # pattern match

# Linting and type checking
uv run ruff check src/
uv run ruff check src/ --fix
uv run mypy src/

# Build package
uv build

# CLI commands (via uv run)
uv run genie --help
uv run genie validate examples/sales_analytics_space.json
uv run genie export <space-id> -o output.json
uv run genie import config.json --warehouse <id> --path "/Workspace/..."
```

## Architecture

### Core Modules (`src/genie_spaces_api/`)

- **models.py**: Pydantic models matching the `GenieSpaceExport` JSON schema from the Databricks API. Key model hierarchy:
  - `GenieSpaceExport` (top-level) → `GenieSpaceConfig`, `DataSources`, `Instructions`, `Benchmarks`
  - `DataSources` → `Table`, `MetricView`, `ColumnConfig`
  - `Instructions` → `TextInstruction`, `ExampleQuestionSql`, `SqlFunction`, `JoinSpec`
  - Most models have factory methods (`.create()`, `.from_text()`) for convenient instantiation

- **client.py**: `GenieSpacesClient` wraps httpx for REST API calls. Key methods:
  - `export_space()` / `export_space_to_file()` - GET with `include_serialized_space=true`
  - `import_space()` / `import_space_from_file()` - POST to create new space
  - `update_space()` / `update_space_from_file()` - PATCH existing space
  - `clone_space()` - combines export + import
  - Custom exceptions: `GenieSpacesError`, `AuthenticationError`, `NotFoundError`, `ValidationError`

- **cli.py**: Typer CLI application exposing: `export`, `import`, `update`, `clone`, `validate`, `info`, `version`

### API Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Export | GET | `/api/2.0/genie/spaces/{space_id}?include_serialized_space=true` |
| Import | POST | `/api/2.0/genie/spaces` |
| Update | PATCH | `/api/2.0/genie/spaces/{space_id}` |

### CLI Entry Point

Defined in `pyproject.toml`:
```toml
[project.scripts]
genie = "genie_spaces_api.cli:app"
```

`uv sync` generates `.venv/bin/genie` which calls the Typer `app` object.

## Schema Notes

- All IDs are UUIDs without dashes (32 hex chars)
- Text fields (descriptions, instructions, SQL) are stored as `list[str]` split on newlines for cleaner diffs
- `serialized_space` in API requests/responses is a JSON string, not an object
- Warehouse ID, title, and description are separate API fields, not in the serialized blob

## Testing

Tests use `pytest` with `respx` for HTTP mocking. Test files mirror source structure:
- `tests/test_models.py` - Pydantic model validation and serialization
- `tests/test_client.py` - API client with mocked responses

## Dependencies

Managed exclusively with `uv` (no pip). Core: httpx, pydantic, typer, rich, python-dotenv.
