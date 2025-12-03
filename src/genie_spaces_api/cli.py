"""
Command-line interface for Databricks Genie Spaces management.

Provides commands for exporting, importing, updating, and managing Genie Spaces
via the Databricks REST API.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from genie_spaces_api.client import (
    AuthenticationError,
    GenieSpacesClient,
    GenieSpacesError,
    NotFoundError,
    ValidationError,
)
from genie_spaces_api.models import GenieSpaceExport

app = typer.Typer(
    name="genie",
    help="Databricks Genie Spaces CLI - Manage Genie Spaces via the Import/Export API",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


def get_client(host: str | None, token: str | None) -> GenieSpacesClient:
    """Create a client, handling missing credentials gracefully."""
    try:
        return GenieSpacesClient(host=host, token=token)
    except ValueError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        console.print("\n[dim]Set DATABRICKS_HOST and DATABRICKS_TOKEN environment variables, or use --host and --token flags.[/dim]")
        raise typer.Exit(1)


def handle_error(e: Exception) -> None:
    """Handle errors and display helpful messages."""
    if isinstance(e, AuthenticationError):
        console.print(f"[red]Authentication Failed:[/red] {e}")
        console.print("\n[dim]Check your token and ensure you have 'Can Run' or higher permissions on the space.[/dim]")
    elif isinstance(e, NotFoundError):
        console.print(f"[red]Not Found:[/red] {e}")
        console.print("\n[dim]Verify the space ID exists and you have access to it.[/dim]")
    elif isinstance(e, ValidationError):
        console.print(f"[red]Validation Error:[/red] {e}")
        if e.response:
            console.print(f"[dim]Details: {json.dumps(e.response, indent=2)}[/dim]")
    elif isinstance(e, GenieSpacesError):
        console.print(f"[red]API Error:[/red] {e}")
    else:
        console.print(f"[red]Unexpected Error:[/red] {e}")
    raise typer.Exit(1)


# =============================================================================
# Export Commands
# =============================================================================


@app.command("export")
def export_space(
    space_id: Annotated[str, typer.Argument(help="The ID of the Genie Space to export")],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output file path (default: stdout)"),
    ] = None,
    host: Annotated[
        Optional[str],
        typer.Option("--host", "-h", envvar="DATABRICKS_HOST", help="Databricks workspace URL"),
    ] = None,
    token: Annotated[
        Optional[str],
        typer.Option("--token", "-t", envvar="DATABRICKS_TOKEN", help="Personal access token"),
    ] = None,
    pretty: Annotated[
        bool,
        typer.Option("--pretty/--compact", help="Pretty print JSON output"),
    ] = True,
) -> None:
    """Export a Genie Space to JSON.

    Exports the complete configuration of a Genie Space including tables,
    instructions, sample questions, and benchmarks.

    Examples:

        # Export to stdout
        genie export abc123-def456

        # Export to file
        genie export abc123-def456 -o my-space.json

        # Export with explicit credentials
        genie export abc123 --host https://workspace.cloud.databricks.com --token dapi...
    """
    try:
        client = get_client(host, token)
        space = client.export_space(space_id)
        export = space.get_export()

        if export is None:
            console.print("[red]Error:[/red] Space returned empty configuration")
            raise typer.Exit(1)

        json_output = export.to_json(indent=2 if pretty else None)

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json_output)
            console.print(f"[green]✓[/green] Exported space '[bold]{space.title}[/bold]' to {output}")
            console.print(f"  [dim]Space ID: {space.space_id}[/dim]")
        else:
            if sys.stdout.isatty():
                syntax = Syntax(json_output, "json", theme="monokai", line_numbers=True)
                console.print(syntax)
            else:
                print(json_output)

    except GenieSpacesError as e:
        handle_error(e)


# =============================================================================
# Import Commands
# =============================================================================


@app.command("import")
def import_space(
    file: Annotated[Path, typer.Argument(help="Path to the JSON configuration file")],
    warehouse_id: Annotated[
        str,
        typer.Option("--warehouse", "-w", help="SQL warehouse ID for the new space"),
    ],
    parent_path: Annotated[
        str,
        typer.Option("--path", "-p", help="Workspace path (e.g., /Workspace/Users/user@company.com/Genie Spaces)"),
    ],
    title: Annotated[
        Optional[str],
        typer.Option("--title", help="Display title for the space"),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description for the space"),
    ] = None,
    host: Annotated[
        Optional[str],
        typer.Option("--host", "-h", envvar="DATABRICKS_HOST", help="Databricks workspace URL"),
    ] = None,
    token: Annotated[
        Optional[str],
        typer.Option("--token", "-t", envvar="DATABRICKS_TOKEN", help="Personal access token"),
    ] = None,
) -> None:
    """Import a Genie Space from a JSON file.

    Creates a new Genie Space from an exported configuration file.

    Examples:

        # Import with required options
        genie import my-space.json --warehouse abc123 --path "/Workspace/Users/me/Genie Spaces"

        # Import with custom title
        genie import my-space.json -w abc123 -p "/Workspace/Users/me/Spaces" --title "Production Space"
    """
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    try:
        client = get_client(host, token)
        result = client.import_space_from_file(
            warehouse_id=warehouse_id,
            parent_path=parent_path,
            file_path=file,
            title=title,
            description=description,
        )

        console.print(Panel.fit(
            f"[green]✓ Space created successfully![/green]\n\n"
            f"[bold]Title:[/bold] {result.title}\n"
            f"[bold]Space ID:[/bold] {result.space_id}\n"
            f"[bold]Warehouse:[/bold] {warehouse_id}",
            title="Import Complete",
            border_style="green",
        ))

    except GenieSpacesError as e:
        handle_error(e)


# =============================================================================
# Update Commands
# =============================================================================


@app.command("update")
def update_space(
    space_id: Annotated[str, typer.Argument(help="The ID of the Genie Space to update")],
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Path to the JSON configuration file"),
    ] = None,
    title: Annotated[
        Optional[str],
        typer.Option("--title", help="New display title"),
    ] = None,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="New description"),
    ] = None,
    warehouse_id: Annotated[
        Optional[str],
        typer.Option("--warehouse", "-w", help="New SQL warehouse ID"),
    ] = None,
    host: Annotated[
        Optional[str],
        typer.Option("--host", "-h", envvar="DATABRICKS_HOST", help="Databricks workspace URL"),
    ] = None,
    token: Annotated[
        Optional[str],
        typer.Option("--token", "-t", envvar="DATABRICKS_TOKEN", help="Personal access token"),
    ] = None,
) -> None:
    """Update an existing Genie Space.

    Updates the configuration of an existing Genie Space. You can update
    the full configuration from a file, or just metadata fields.

    Examples:

        # Update from file
        genie update abc123 --file updated-config.json

        # Update just the title
        genie update abc123 --title "New Title"

        # Update warehouse
        genie update abc123 --warehouse new-warehouse-id
    """
    if not file and not title and not description and not warehouse_id:
        console.print("[yellow]Warning:[/yellow] No changes specified. Use --file, --title, --description, or --warehouse.")
        raise typer.Exit(1)

    try:
        client = get_client(host, token)

        serialized_space = None
        if file:
            if not file.exists():
                console.print(f"[red]Error:[/red] File not found: {file}")
                raise typer.Exit(1)
            export = GenieSpaceExport.from_file(str(file))
            serialized_space = export

        result = client.update_space(
            space_id=space_id,
            serialized_space=serialized_space,
            warehouse_id=warehouse_id,
            title=title,
            description=description,
        )

        console.print(Panel.fit(
            f"[green]✓ Space updated successfully![/green]\n\n"
            f"[bold]Title:[/bold] {result.title}\n"
            f"[bold]Space ID:[/bold] {result.space_id}",
            title="Update Complete",
            border_style="green",
        ))

    except GenieSpacesError as e:
        handle_error(e)


# =============================================================================
# Clone Command
# =============================================================================


@app.command("clone")
def clone_space(
    source_id: Annotated[str, typer.Argument(help="The ID of the Genie Space to clone")],
    warehouse_id: Annotated[
        str,
        typer.Option("--warehouse", "-w", help="SQL warehouse ID for the new space"),
    ],
    parent_path: Annotated[
        str,
        typer.Option("--path", "-p", help="Workspace path for the new space"),
    ],
    title: Annotated[
        Optional[str],
        typer.Option("--title", help="Title for the cloned space"),
    ] = None,
    host: Annotated[
        Optional[str],
        typer.Option("--host", "-h", envvar="DATABRICKS_HOST", help="Databricks workspace URL"),
    ] = None,
    token: Annotated[
        Optional[str],
        typer.Option("--token", "-t", envvar="DATABRICKS_TOKEN", help="Personal access token"),
    ] = None,
) -> None:
    """Clone a Genie Space to a new location.

    Creates a copy of an existing Genie Space in a new location, optionally
    with a different warehouse.

    Examples:

        # Clone to same workspace with new title
        genie clone abc123 -w def456 -p "/Workspace/Users/me/Spaces" --title "Dev Copy"

        # Clone to production workspace
        genie clone abc123 -w prod-warehouse -p "/Workspace/Shared/Genie Spaces" \\
            --host https://prod.cloud.databricks.com --token $PROD_TOKEN
    """
    try:
        client = get_client(host, token)
        result = client.clone_space(
            source_space_id=source_id,
            warehouse_id=warehouse_id,
            parent_path=parent_path,
            title=title,
        )

        console.print(Panel.fit(
            f"[green]✓ Space cloned successfully![/green]\n\n"
            f"[bold]New Title:[/bold] {result.title}\n"
            f"[bold]New Space ID:[/bold] {result.space_id}\n"
            f"[bold]Source ID:[/bold] {source_id}",
            title="Clone Complete",
            border_style="green",
        ))

    except GenieSpacesError as e:
        handle_error(e)


# =============================================================================
# Validate Command
# =============================================================================


@app.command("validate")
def validate_config(
    file: Annotated[Path, typer.Argument(help="Path to the JSON configuration file to validate")],
) -> None:
    """Validate a Genie Space configuration file.

    Parses the JSON file and validates it against the GenieSpaceExport schema.
    This is useful for catching errors before attempting to import.

    Examples:

        genie validate my-space.json
    """
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    try:
        export = GenieSpaceExport.from_file(str(file))

        # Build summary
        table = Table(title="Configuration Summary", show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Count", justify="right")

        sample_q_count = len(export.config.sample_questions) if export.config else 0
        table_count = len(export.data_sources.tables) if export.data_sources and export.data_sources.tables else 0
        mv_count = len(export.data_sources.metric_views) if export.data_sources and export.data_sources.metric_views else 0
        text_inst_count = len(export.instructions.text_instructions) if export.instructions and export.instructions.text_instructions else 0
        sql_ex_count = len(export.instructions.example_question_sqls) if export.instructions and export.instructions.example_question_sqls else 0
        func_count = len(export.instructions.sql_functions) if export.instructions and export.instructions.sql_functions else 0
        join_count = len(export.instructions.join_specs) if export.instructions and export.instructions.join_specs else 0
        bench_count = len(export.benchmarks.questions) if export.benchmarks else 0

        table.add_row("Sample Questions", str(sample_q_count))
        table.add_row("Tables", str(table_count))
        table.add_row("Metric Views", str(mv_count))
        table.add_row("Text Instructions", str(text_inst_count))
        table.add_row("SQL Examples", str(sql_ex_count))
        table.add_row("SQL Functions", str(func_count))
        table.add_row("Join Specs", str(join_count))
        table.add_row("Benchmark Questions", str(bench_count))

        console.print(f"[green]✓[/green] Valid configuration file: {file}\n")
        console.print(table)

    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Validation Error:[/red] {e}")
        raise typer.Exit(1)


# =============================================================================
# Info Command
# =============================================================================


@app.command("info")
def show_info(
    space_id: Annotated[str, typer.Argument(help="The ID of the Genie Space")],
    host: Annotated[
        Optional[str],
        typer.Option("--host", "-h", envvar="DATABRICKS_HOST", help="Databricks workspace URL"),
    ] = None,
    token: Annotated[
        Optional[str],
        typer.Option("--token", "-t", envvar="DATABRICKS_TOKEN", help="Personal access token"),
    ] = None,
) -> None:
    """Show information about a Genie Space.

    Displays a summary of the space configuration without exporting the full JSON.

    Examples:

        genie info abc123-def456
    """
    try:
        client = get_client(host, token)
        space = client.export_space(space_id)
        export = space.get_export()

        if export is None:
            console.print("[red]Error:[/red] Space returned empty configuration")
            raise typer.Exit(1)

        # Space metadata
        console.print(Panel.fit(
            f"[bold]Title:[/bold] {space.title}\n"
            f"[bold]Space ID:[/bold] {space.space_id}\n"
            f"[bold]Warehouse:[/bold] {space.warehouse_id or 'N/A'}\n"
            f"[bold]Description:[/bold] {space.description or 'N/A'}",
            title="Space Information",
            border_style="blue",
        ))

        # Tables
        if export.data_sources and export.data_sources.tables:
            table = Table(title="Tables", show_header=True)
            table.add_column("Identifier", style="cyan")
            table.add_column("Columns Configured", justify="right")
            for t in export.data_sources.tables:
                col_count = len(t.column_configs) if t.column_configs else 0
                table.add_row(t.identifier, str(col_count))
            console.print(table)

        # Metric Views
        if export.data_sources and export.data_sources.metric_views:
            table = Table(title="Metric Views", show_header=True)
            table.add_column("Identifier", style="cyan")
            for mv in export.data_sources.metric_views:
                table.add_row(mv.identifier)
            console.print(table)

        # Sample Questions
        if export.config and export.config.sample_questions:
            console.print("\n[bold]Sample Questions:[/bold]")
            for i, sq in enumerate(export.config.sample_questions, 1):
                question_text = " ".join(sq.question)
                console.print(f"  {i}. {question_text}")

    except GenieSpacesError as e:
        handle_error(e)


# =============================================================================
# Version Command
# =============================================================================


@app.command("version")
def show_version() -> None:
    """Show the CLI version."""
    from genie_spaces_api import __version__

    console.print(f"genie-spaces-api version {__version__}")


if __name__ == "__main__":
    app()
