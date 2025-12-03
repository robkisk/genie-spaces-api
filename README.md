# Databricks Genie Spaces API SDK

A Python SDK and CLI for managing **Databricks Genie Spaces** via the Import/Export API. This toolkit enables CI/CD workflows, cross-workspace migrations, and programmatic management of Genie Spaces.

> ⚠️ **Pre-Private Preview**: This API is currently in pre-private preview. It is not intended for production use and is provided AS-IS without formal SLA support.

## Features

- **Export** Genie Spaces as serialized JSON configurations
- **Import** new Genie Spaces from configurations
- **Update** existing Genie Spaces programmatically
- **Clone** spaces across workspaces
- **Validate** configurations before deployment
- **CI/CD Integration** with GitHub Actions examples

---

## Getting Started

Follow these step-by-step instructions to set up and use the Genie Spaces API SDK.

### Prerequisites

Before you begin, ensure you have:

1. **Python 3.10 or higher** installed
2. **uv** package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
3. **Databricks workspace** with Genie enabled (AWS or non-GFM Azure)
4. **Personal Access Token** with "Can Run" or higher permissions on Genie Spaces

### Step 1: Install uv

[uv](https://docs.astral.sh/uv/) is a fast Python package manager. Install it first:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify installation:
```bash
uv --version
```

### Step 2: Clone or Download the Project

```bash
# Clone the repository
git clone https://github.com/your-org/genie-spaces-api.git
cd genie-spaces-api

# Or if you received this as a zip file, extract and navigate to it
cd genie-spaces-api
```

### Step 3: Install Dependencies

```bash
# Install all dependencies (creates .venv automatically)
uv sync
```

This creates a `.venv` directory and installs all required packages:
- `httpx` - HTTP client
- `pydantic` - Data validation
- `typer` - CLI framework
- `rich` - Terminal formatting
- `python-dotenv` - Environment variables

### Step 4: Configure Databricks Credentials

**Option A: Environment Variables (Recommended for CLI)**

```bash
# Add to your shell profile (~/.zshrc, ~/.bashrc, etc.)
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="dapi_your_token_here"

# Reload your shell or run:
source ~/.zshrc
```

**Option B: Create a `.env` File (Good for Development)**

```bash
# Copy the example file
cp .env.example .env

# Edit with your credentials
```

Then edit `.env`:
```env
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=dapi_your_token_here
```

**Option C: Pass Credentials Directly (Good for Scripts)**

```bash
genie export <space-id> \
    --host "https://your-workspace.cloud.databricks.com" \
    --token "dapi_your_token"
```

### Step 5: Verify Installation

When you ran `uv sync`, uv automatically:
1. Created a `.venv` virtual environment
2. Installed the `genie-spaces-api` package in editable mode
3. Generated the `genie` CLI executable at `.venv/bin/genie`

The CLI is defined in `pyproject.toml` as an entry point:
```toml
[project.scripts]
genie = "genie_spaces_api.cli:app"
```

This maps the `genie` command to the Typer application in `src/genie_spaces_api/cli.py`.

```bash
# Check CLI is working
uv run genie --help

# Validate the example configuration
uv run genie validate examples/sales_analytics_space.json
```

You should see:
```
✓ Valid configuration file: examples/sales_analytics_space.json

     Configuration Summary
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Component           ┃ Count ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Sample Questions    │     4 │
│ Tables              │     3 │
│ ...                 │   ... │
└─────────────────────┴───────┘
```

### Step 6: Find Your Databricks IDs

**Finding Your Space ID:**

Open a Genie Space in your browser. The space ID is in the URL:
```
https://your-workspace.cloud.databricks.com/genie/spaces/01234567-89ab-cdef-0123-456789abcdef
                                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                        This is the space ID
```

**Finding Your Warehouse ID:**

Navigate to SQL Warehouses in Databricks. The warehouse ID is in the URL:
```
https://your-workspace.cloud.databricks.com/sql/warehouses/abc123def456?o=...
                                                           ^^^^^^^^^^^^
                                                           This is the warehouse ID
```

Or use the Databricks CLI:
```bash
databricks warehouses list
```

---

## Usage Guide

### CLI Commands

All CLI commands are run with `uv run genie` (or just `genie` if installed globally).

#### Export a Genie Space

```bash
# Export to stdout (for piping or quick inspection)
uv run genie export <space-id>

# Export to a file
uv run genie export <space-id> -o my-space.json

# Export with explicit credentials
uv run genie export <space-id> \
    --host "https://workspace.cloud.databricks.com" \
    --token "dapi_xxx" \
    -o my-space.json
```

#### Import a New Space

```bash
uv run genie import my-space.json \
    --warehouse <warehouse-id> \
    --path "/Workspace/Users/you@company.com/Genie Spaces" \
    --title "My Analytics Space"
```

#### Update an Existing Space

```bash
# Update configuration from file
uv run genie update <space-id> --file updated-config.json

# Update just the title
uv run genie update <space-id> --title "New Title"

# Update the warehouse
uv run genie update <space-id> --warehouse <new-warehouse-id>
```

#### Clone a Space

```bash
uv run genie clone <source-space-id> \
    --warehouse <target-warehouse-id> \
    --path "/Workspace/Shared/Genie Spaces" \
    --title "Cloned Analytics Space"
```

#### Validate a Configuration File

```bash
uv run genie validate my-space.json
```

#### Show Space Information

```bash
uv run genie info <space-id>
```

### Python SDK Usage

```python
from genie_spaces_api import GenieSpacesClient, GenieSpaceExport

# Initialize client (reads from environment variables)
client = GenieSpacesClient()

# Or with explicit credentials
client = GenieSpacesClient(
    host="https://your-workspace.cloud.databricks.com",
    token="dapi_your_token"
)

# Export a space
space = client.export_space("space-id-here")
export = space.get_export()

# Access configuration details
print(f"Space: {space.title}")
for table in export.data_sources.tables:
    print(f"  Table: {table.identifier}")

# Save to file
export.to_file("my-space.json")

# Import a new space
new_space = client.import_space_from_file(
    warehouse_id="abc123def456",
    parent_path="/Workspace/Users/user@company.com/Genie Spaces",
    file_path="my-space.json",
    title="Production Analytics Space"
)
print(f"Created space: {new_space.space_id}")

# Clone a space
cloned = client.clone_space(
    source_space_id="source-id",
    warehouse_id="prod-warehouse-id",
    parent_path="/Workspace/Shared/Genie Spaces",
    title="Production Copy"
)
```

---

## Development Setup

If you want to modify the SDK or contribute to it:

### Step 1: Clone and Install with Dev Dependencies

```bash
git clone https://github.com/your-org/genie-spaces-api.git
cd genie-spaces-api

# Install all dependencies including dev tools
uv sync --all-extras
```

### Step 2: Run Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_models.py
```

### Step 3: Code Quality Checks

```bash
# Run linter
uv run ruff check src/

# Auto-fix linting issues
uv run ruff check src/ --fix

# Type checking
uv run mypy src/
```

### Step 4: Build the Package

```bash
# Build wheel and source distribution
uv build

# Output will be in dist/
ls dist/
# genie_spaces_api-0.1.0-py3-none-any.whl
# genie_spaces_api-0.1.0.tar.gz
```

### Step 5: Install Locally (for testing in other projects)

```bash
# Install the built wheel in another project
uv add /path/to/genie-spaces-api/dist/genie_spaces_api-0.1.0-py3-none-any.whl

# Or install from source in editable mode
uv add --editable /path/to/genie-spaces-api
```

---

## Project Structure

```
genie-spaces-api/
├── src/genie_spaces_api/    # Main package
│   ├── __init__.py          # Package exports
│   ├── models.py            # Pydantic models (GenieSpaceExport schema)
│   ├── client.py            # HTTP client for API calls
│   └── cli.py               # Typer CLI application
├── examples/                 # Example configurations
│   ├── sales_analytics_space.json    # Full-featured example
│   ├── minimal_space.json            # Minimal template
│   └── programmatic_space_builder.py # Build configs in Python
├── tests/                    # Unit tests
│   ├── test_models.py        # Model tests
│   └── test_client.py        # Client tests with mocks
├── docs/                     # Documentation
│   └── QUICKSTART.md         # Quick reference guide
├── .github/workflows/        # CI/CD templates
│   └── deploy-genie-space.yml
├── pyproject.toml           # Package configuration
├── .env.example             # Environment template
└── README.md                # This file
```

---

## API Reference

### REST Endpoints

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Export Space | GET | `/api/2.0/genie/spaces/{space_id}?include_serialized_space=true` |
| Import Space | POST | `/api/2.0/genie/spaces` |
| Update Space | PATCH | `/api/2.0/genie/spaces/{space_id}` |

### Export Space (cURL)

```bash
curl -X GET \
  "https://<workspace>.cloud.databricks.com/api/2.0/genie/spaces/{space_id}?include_serialized_space=true" \
  -H "Authorization: Bearer <token>"
```

### Import Space (cURL)

```bash
curl -X POST \
  "https://<workspace>.cloud.databricks.com/api/2.0/genie/spaces" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "warehouse_id": "abc123def456",
    "parent_path": "/Workspace/Users/user@company.com/Genie Spaces",
    "serialized_space": "<exported_json_string>",
    "title": "My Space",
    "description": "Space description"
  }'
```

### Update Space (cURL)

```bash
curl -X PATCH \
  "https://<workspace>.cloud.databricks.com/api/2.0/genie/spaces/{space_id}" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "serialized_space": "<updated_json_string>",
    "title": "Updated Title"
  }'
```

---

## Configuration Schema

The `GenieSpaceExport` schema defines the structure of exported/imported Genie Spaces:

```json
{
  "version": 1,
  "config": {
    "sample_questions": [
      {
        "id": "unique_uuid_without_dashes",
        "question": ["What is the total revenue by region?"]
      }
    ]
  },
  "data_sources": {
    "tables": [
      {
        "identifier": "catalog.schema.table_name",
        "description": ["Table description"],
        "column_configs": [
          {
            "column_name": "order_id",
            "description": ["Primary key"],
            "synonyms": ["id", "orderid"],
            "exclude": false,
            "get_example_values": true,
            "build_value_dictionary": true
          }
        ]
      }
    ],
    "metric_views": [
      {
        "identifier": "catalog.schema.metric_view",
        "description": ["Metric view description"]
      }
    ]
  },
  "instructions": {
    "text_instructions": [
      {
        "id": "unique_uuid",
        "content": ["Always format currency with $ symbol"]
      }
    ],
    "example_question_sqls": [
      {
        "id": "unique_uuid",
        "question": ["Top N products by revenue"],
        "sql": ["SELECT product, SUM(revenue) FROM sales GROUP BY 1 ORDER BY 2 DESC LIMIT :n"],
        "parameters": [
          {
            "name": "n",
            "type_hint": "INTEGER",
            "description": ["Number of products to return"]
          }
        ],
        "usage_guidance": ["Use for top-N product queries"]
      }
    ],
    "sql_functions": [
      {
        "id": "unique_uuid",
        "identifier": "catalog.schema.custom_function"
      }
    ],
    "join_specs": [
      {
        "id": "unique_uuid",
        "left": {"identifier": "catalog.schema.orders", "alias": "o"},
        "right": {"identifier": "catalog.schema.customers", "alias": "c"},
        "sql": ["o.customer_id = c.id"],
        "comment": ["Join orders to customers"]
      }
    ]
  },
  "benchmarks": {
    "questions": [
      {
        "id": "unique_uuid",
        "question": ["What was total revenue last quarter?"],
        "answer": [
          {
            "format": "SQL",
            "content": ["SELECT SUM(revenue) FROM sales WHERE date >= DATE_ADD(CURRENT_DATE, -90)"]
          }
        ]
      }
    ]
  }
}
```

---

## Building Configurations Programmatically

```python
from genie_spaces_api import (
    GenieSpaceExport,
    GenieSpaceConfig,
    SampleQuestion,
    DataSources,
    Table,
    ColumnConfig,
    Instructions,
    TextInstruction,
    ExampleQuestionSql,
    Parameter,
)

# Build a configuration programmatically
config = GenieSpaceExport(
    version=1,
    config=GenieSpaceConfig(
        sample_questions=[
            SampleQuestion.from_text("What is total revenue by region?"),
            SampleQuestion.from_text("Show me the top 10 customers by spend"),
        ]
    ),
    data_sources=DataSources(
        tables=[
            Table.create(
                identifier="sales.analytics.orders",
                description="All customer orders",
                column_configs=[
                    ColumnConfig.create(
                        column_name="order_id",
                        description="Unique order identifier",
                        synonyms=["id", "order_number"],
                        get_example_values=True,
                    ),
                    ColumnConfig.create(
                        column_name="customer_id",
                        description="Customer reference",
                        build_value_dictionary=True,
                    ),
                ]
            ),
        ]
    ),
    instructions=Instructions(
        text_instructions=[
            TextInstruction.from_text(
                "Always use ISO date format (YYYY-MM-DD) in queries.\n"
                "Format currency values with $ and two decimal places."
            ),
        ],
        example_question_sqls=[
            ExampleQuestionSql.create(
                question="What are the top N products by revenue?",
                sql="""SELECT
    product_name,
    SUM(unit_price * quantity) as revenue
FROM sales.analytics.orders
GROUP BY product_name
ORDER BY revenue DESC
LIMIT :limit_n""",
                parameters=[
                    Parameter.create("limit_n", "INTEGER", "Number of products to return"),
                ],
                usage_guidance="Use this template for any top-N product queries",
            ),
        ],
    ),
)

# Export to file
config.to_file("my-space-config.json")

# Or get JSON string
json_str = config.to_json(indent=2)
```

See `examples/programmatic_space_builder.py` for a complete example.

---

## CI/CD Integration

### GitHub Actions

See [`.github/workflows/deploy-genie-space.yml`](.github/workflows/deploy-genie-space.yml) for a complete example.

```yaml
name: Deploy Genie Space

on:
  push:
    branches: [main]
    paths: ['genie-spaces/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Setup Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv tool install genie-spaces-api

      - name: Validate configuration
        run: uvx genie-spaces-api validate genie-spaces/production.json

      - name: Deploy to production
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
        run: |
          uvx genie-spaces-api update ${{ vars.SPACE_ID }} \
            --file genie-spaces/production.json
```

---

## Troubleshooting

### Common Issues

**"Databricks host is required"**
```
ValueError: Databricks host is required. Provide 'host' parameter or set DATABRICKS_HOST.
```
→ Set the `DATABRICKS_HOST` environment variable or use `--host` flag.

**"Authentication failed"**
```
AuthenticationError: Authentication failed. Check your token and permissions.
```
→ Verify your token is valid and has "Can Run" or higher permissions on the space.

**"Resource not found"**
```
NotFoundError: Resource not found: Space not found
```
→ Check the space ID is correct (copy from URL) and you have access to it.

**"Invalid configuration"**
```
ValidationError: Invalid configuration
```
→ Run `genie validate` first. Ensure all table identifiers exist in the target workspace.

### Getting Help

- Check the [docs/QUICKSTART.md](docs/QUICKSTART.md) for quick reference
- Review examples in `examples/` directory
- Open an issue on GitHub

---

## Important Notes

### Cross-Workspace Migrations

When importing a space to a different workspace:

1. **Table Access**: All referenced tables must be accessible in the target workspace
2. **Warehouse ID**: Update the warehouse ID to a valid warehouse in the target workspace
3. **Permissions**: Object-level permissions do NOT transfer; you must reconfigure them
4. **Functions**: SQL functions must exist in the target catalog

### What's NOT Included in Exports

- Conversation history
- Object-level permissions
- Audit logs
- User-specific settings

### Limitations

- Only SQL answer format is currently supported for benchmarks
- One text instruction is supported per space
- The API is in pre-private preview and may change

---

## Resources

- [Databricks Genie Documentation](https://docs.databricks.com/en/genie/index.html)
- [Databricks REST API Reference](https://docs.databricks.com/api/workspace/introduction)
- [Unity Catalog Documentation](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- [uv Package Manager](https://docs.astral.sh/uv/)

## License

Apache-2.0
