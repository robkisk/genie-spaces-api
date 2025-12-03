# Quickstart Guide

A quick reference for common Genie Spaces API operations. For detailed setup instructions, see the main [README](../README.md).

---

## TL;DR - Fastest Path to Running

```bash
# 1. Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and setup
git clone https://github.com/your-org/genie-spaces-api.git
cd genie-spaces-api
uv sync

# 3. Set credentials
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="dapi_your_token"

# 4. Test it works
uv run genie validate examples/sales_analytics_space.json

# 5. Export your first space
uv run genie export <your-space-id> -o my-space.json
```

---

## Command Cheat Sheet

### Export
```bash
# To file
uv run genie export <space-id> -o output.json

# To stdout (for piping)
uv run genie export <space-id>
```

### Import
```bash
uv run genie import config.json \
    --warehouse <warehouse-id> \
    --path "/Workspace/Users/me@company.com/Genie Spaces" \
    --title "My Space"
```

### Update
```bash
# Update config from file
uv run genie update <space-id> --file config.json

# Update just metadata
uv run genie update <space-id> --title "New Title"
```

### Clone
```bash
uv run genie clone <source-id> \
    --warehouse <target-warehouse-id> \
    --path "/Workspace/Shared/Genie Spaces" \
    --title "Cloned Space"
```

### Validate
```bash
uv run genie validate my-config.json
```

### Info
```bash
uv run genie info <space-id>
```

---

## Finding IDs

### Space ID
From URL: `https://workspace.com/genie/spaces/`**`01234567-89ab-cdef-0123-456789abcdef`**

### Warehouse ID
From URL: `https://workspace.com/sql/warehouses/`**`abc123def456`**`?o=...`

Or via CLI:
```bash
databricks warehouses list
```

---

## Python SDK Quick Examples

```python
from genie_spaces_api import GenieSpacesClient

# Initialize (reads DATABRICKS_HOST/TOKEN from environment)
client = GenieSpacesClient()

# Export
space = client.export_space("space-id")
space.get_export().to_file("backup.json")

# Import
new_space = client.import_space_from_file(
    warehouse_id="abc123",
    parent_path="/Workspace/Users/me/Spaces",
    file_path="config.json"
)

# Clone
cloned = client.clone_space(
    source_space_id="source-id",
    warehouse_id="target-warehouse",
    parent_path="/Workspace/Shared/Spaces"
)
```

---

## Build Configuration Programmatically

```python
from genie_spaces_api import (
    GenieSpaceExport, GenieSpaceConfig, SampleQuestion,
    DataSources, Table, ColumnConfig
)

config = GenieSpaceExport(
    version=1,
    config=GenieSpaceConfig(
        sample_questions=[
            SampleQuestion.from_text("What is total revenue?")
        ]
    ),
    data_sources=DataSources(
        tables=[
            Table.create(
                identifier="catalog.schema.orders",
                column_configs=[
                    ColumnConfig.create("order_id", synonyms=["id"])
                ]
            )
        ]
    )
)

config.to_file("my-space.json")
```

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| `Databricks host is required` | Set `DATABRICKS_HOST` env var or use `--host` |
| `Authentication failed` | Check token is valid and has "Can Run" permissions |
| `Resource not found` | Verify space ID (copy from URL) |
| `Invalid configuration` | Run `genie validate` first |

---

## Useful Links

- [Full README](../README.md) - Complete documentation
- [Examples](../examples/) - Sample configurations
- [Databricks Genie Docs](https://docs.databricks.com/en/genie/index.html)
- [uv Documentation](https://docs.astral.sh/uv/)
