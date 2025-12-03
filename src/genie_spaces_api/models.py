"""
Pydantic models for the Databricks Genie Spaces Import/Export API.

These models match the GenieSpaceExport schema used for serializing and deserializing
Genie Space configurations for import/export operations.
"""

from __future__ import annotations

import json
import uuid
from typing import Literal

from pydantic import BaseModel, Field


def generate_id() -> str:
    """Generate a UUID without dashes for use as an ID."""
    return uuid.uuid4().hex


# =============================================================================
# Sample Questions
# =============================================================================


class SampleQuestion(BaseModel):
    """A sample question displayed to users in the Genie Space UI."""

    id: str = Field(default_factory=generate_id, description="UUID without dashes, unique within space")
    question: list[str] = Field(
        description="The text of the question. Split at newlines for cleaner diffs."
    )

    @classmethod
    def from_text(cls, question: str, id: str | None = None) -> SampleQuestion:
        """Create a SampleQuestion from a single string."""
        return cls(
            id=id or generate_id(),
            question=question.split("\n") if "\n" in question else [question],
        )


# =============================================================================
# Space Configuration
# =============================================================================


class GenieSpaceConfig(BaseModel):
    """Generic space-level configuration.

    Note: Warehouse ID, display name, and description are sent as separate fields
    in the wrapping CRUD API call, not within this serialized blob.
    """

    sample_questions: list[SampleQuestion] = Field(
        default_factory=list, description="Sample questions to guide end-users"
    )


# =============================================================================
# Data Sources - Tables and Metric Views
# =============================================================================


class ColumnConfig(BaseModel):
    """Configuration for a single column within a table."""

    column_name: str = Field(description="The name of the column")
    description: list[str] | None = Field(
        default=None, description="Overridden description for the column"
    )
    synonyms: list[str] | None = Field(
        default=None, description="List of synonyms for the column name"
    )
    exclude: bool | None = Field(
        default=None, description="If true, column is excluded from LLM context"
    )
    get_example_values: bool | None = Field(
        default=None, description="If true, fetch example values and column statistics"
    )
    build_value_dictionary: bool | None = Field(
        default=None, description="If true, create a value dictionary (index) for this column"
    )

    @classmethod
    def create(
        cls,
        column_name: str,
        description: str | None = None,
        synonyms: list[str] | None = None,
        exclude: bool = False,
        get_example_values: bool = False,
        build_value_dictionary: bool = False,
    ) -> ColumnConfig:
        """Factory method for creating column configs with sensible defaults."""
        return cls(
            column_name=column_name,
            description=[description] if description else None,
            synonyms=synonyms,
            exclude=exclude if exclude else None,
            get_example_values=get_example_values if get_example_values else None,
            build_value_dictionary=build_value_dictionary if build_value_dictionary else None,
        )


class Table(BaseModel):
    """Configuration for a single Unity Catalog table."""

    identifier: str = Field(
        description="Full three-level identifier (e.g., 'catalog.schema.table')"
    )
    description: list[str] | None = Field(
        default=None, description="User-provided description of the table"
    )
    column_configs: list[ColumnConfig] | None = Field(
        default=None, description="Column-specific configurations, ordered by column name"
    )

    @classmethod
    def create(
        cls,
        identifier: str,
        description: str | None = None,
        column_configs: list[ColumnConfig] | None = None,
    ) -> Table:
        """Factory method for creating table configs."""
        return cls(
            identifier=identifier,
            description=[description] if description else None,
            column_configs=column_configs,
        )


class MetricView(BaseModel):
    """Configuration for a single Unity Catalog metric view."""

    identifier: str = Field(
        description="Full three-level identifier (e.g., 'catalog.schema.metric_view')"
    )
    description: list[str] | None = Field(
        default=None, description="User-provided description of the metric view"
    )

    @classmethod
    def create(cls, identifier: str, description: str | None = None) -> MetricView:
        """Factory method for creating metric view configs."""
        return cls(
            identifier=identifier,
            description=[description] if description else None,
        )


class DataSources(BaseModel):
    """Defines what data the space can access."""

    tables: list[Table] | None = Field(
        default=None, description="UC tables in the order they were added"
    )
    metric_views: list[MetricView] | None = Field(
        default=None, description="UC metric views in the order they were added"
    )


# =============================================================================
# Instructions - Text, SQL Examples, Functions, and Joins
# =============================================================================


class TextInstruction(BaseModel):
    """Generic instructions containing unformatted content."""

    id: str = Field(default_factory=generate_id, description="UUID without dashes")
    content: list[str] | None = Field(
        default=None, description="Instruction content, split at newlines"
    )

    @classmethod
    def from_text(cls, content: str, id: str | None = None) -> TextInstruction:
        """Create a TextInstruction from a single string."""
        return cls(
            id=id or generate_id(),
            content=content.split("\n") if content else None,
        )


class Parameter(BaseModel):
    """Defines a parameter for a parameterized SQL query."""

    name: str = Field(description="Parameter name used in the query")
    type_hint: str = Field(description="Data type hint (e.g., 'STRING', 'INTEGER', 'DATE')")
    description: list[str] | None = Field(
        default=None, description="Description of the parameter's purpose"
    )

    @classmethod
    def create(cls, name: str, type_hint: str, description: str | None = None) -> Parameter:
        """Factory method for creating parameters."""
        return cls(
            name=name,
            type_hint=type_hint,
            description=[description] if description else None,
        )


class ExampleQuestionSql(BaseModel):
    """An example question paired with its ground-truth SQL query."""

    id: str = Field(default_factory=generate_id, description="UUID without dashes")
    question: list[str] = Field(description="Natural language question")
    sql: list[str] = Field(description="Ground-truth SQL query")
    parameters: list[Parameter] | None = Field(
        default=None, description="Parameters used in the SQL query"
    )
    usage_guidance: list[str] | None = Field(
        default=None, description="Guidance on how to use this example"
    )

    @classmethod
    def create(
        cls,
        question: str,
        sql: str,
        parameters: list[Parameter] | None = None,
        usage_guidance: str | None = None,
        id: str | None = None,
    ) -> ExampleQuestionSql:
        """Factory method for creating SQL examples."""
        return cls(
            id=id or generate_id(),
            question=[question],
            sql=sql.split("\n"),
            parameters=parameters,
            usage_guidance=[usage_guidance] if usage_guidance else None,
        )


class SqlFunction(BaseModel):
    """A reference to a SQL function that can be used in generated SQL."""

    id: str = Field(default_factory=generate_id, description="UUID without dashes")
    identifier: str = Field(
        description="Full three-level identifier (e.g., 'catalog.schema.function')"
    )


class JoinSource(BaseModel):
    """A table or metric view used in a join specification."""

    identifier: str = Field(description="Table/metric view identifier")
    alias: str = Field(description="Alias to use for the table/metric view")


class JoinSpec(BaseModel):
    """Pre-defined join specification between two tables or metric views."""

    id: str = Field(default_factory=generate_id, description="UUID without dashes")
    left: JoinSource = Field(description="Left table/metric view in the join")
    right: JoinSource = Field(description="Right table/metric view in the join")
    sql: list[str] = Field(description="SQL for the join condition")
    comment: list[str] | None = Field(
        default=None, description="Description of the join's purpose"
    )

    @classmethod
    def create(
        cls,
        left_identifier: str,
        left_alias: str,
        right_identifier: str,
        right_alias: str,
        join_condition: str,
        comment: str | None = None,
        id: str | None = None,
    ) -> JoinSpec:
        """Factory method for creating join specifications."""
        return cls(
            id=id or generate_id(),
            left=JoinSource(identifier=left_identifier, alias=left_alias),
            right=JoinSource(identifier=right_identifier, alias=right_alias),
            sql=[join_condition],
            comment=[comment] if comment else None,
        )


class Instructions(BaseModel):
    """Instructions, tools, and examples scoped to the whole space."""

    text_instructions: list[TextInstruction] | None = Field(
        default=None, description="High-level text instructions for the LLM"
    )
    example_question_sqls: list[ExampleQuestionSql] | None = Field(
        default=None, description="Example questions with their correct SQL"
    )
    sql_functions: list[SqlFunction] | None = Field(
        default=None, description="SQL functions available for generated queries"
    )
    join_specs: list[JoinSpec] | None = Field(
        default=None, description="Pre-defined join specifications"
    )


# =============================================================================
# Benchmarks
# =============================================================================


class BenchmarkAnswer(BaseModel):
    """Ground-truth answer for a benchmark question."""

    format: Literal["SQL"] = Field(default="SQL", description="Answer format (only SQL supported)")
    content: list[str] = Field(description="Answer content, split at newlines")

    @classmethod
    def from_sql(cls, sql: str) -> BenchmarkAnswer:
        """Create a BenchmarkAnswer from a SQL string."""
        return cls(format="SQL", content=sql.split("\n"))


class BenchmarkQuestion(BaseModel):
    """A benchmark question for evaluating space quality."""

    id: str = Field(default_factory=generate_id, description="UUID without dashes")
    question: list[str] = Field(description="Natural language question")
    answer: list[BenchmarkAnswer] = Field(description="Ground-truth answers (currently one)")

    @classmethod
    def create(cls, question: str, sql_answer: str, id: str | None = None) -> BenchmarkQuestion:
        """Factory method for creating benchmark questions."""
        return cls(
            id=id or generate_id(),
            question=[question],
            answer=[BenchmarkAnswer.from_sql(sql_answer)],
        )


class Benchmarks(BaseModel):
    """Collection of benchmark questions for evaluating space quality."""

    questions: list[BenchmarkQuestion] = Field(default_factory=list)


# =============================================================================
# Top-Level Export Schema
# =============================================================================


class GenieSpaceExport(BaseModel):
    """Top-level container for a serialized Genie Space.

    This schema is used for import/export operations and differs from the direct
    fields exposed in the REST API.
    """

    version: int = Field(default=1, description="Export schema version for backward compatibility")
    config: GenieSpaceConfig | None = Field(
        default=None, description="Generic space-level configuration"
    )
    data_sources: DataSources | None = Field(
        default=None, description="Data sources the space can access"
    )
    instructions: Instructions | None = Field(
        default=None, description="Instructions and tools scoped to the space"
    )
    benchmarks: Benchmarks | None = Field(
        default=None, description="Benchmarks for evaluating space quality"
    )

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string, excluding None values."""
        return self.model_dump_json(exclude_none=True, indent=indent)

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_json(cls, json_str: str) -> GenieSpaceExport:
        """Parse from JSON string."""
        return cls.model_validate_json(json_str)

    @classmethod
    def from_dict(cls, data: dict) -> GenieSpaceExport:
        """Parse from dictionary."""
        return cls.model_validate(data)

    @classmethod
    def from_file(cls, path: str) -> GenieSpaceExport:
        """Load from a JSON file."""
        with open(path) as f:
            return cls.from_json(f.read())

    def to_file(self, path: str, indent: int = 2) -> None:
        """Save to a JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json(indent=indent))


# =============================================================================
# API Response Models
# =============================================================================


class SpaceResponse(BaseModel):
    """Response from the Genie Spaces API."""

    space_id: str = Field(description="Unique identifier for the space")
    title: str = Field(description="Display title of the space")
    description: str | None = Field(default=None, description="Space description")
    warehouse_id: str | None = Field(default=None, description="SQL warehouse ID")
    serialized_space: str | None = Field(
        default=None, description="JSON string of GenieSpaceExport"
    )

    def get_export(self) -> GenieSpaceExport | None:
        """Parse the serialized_space into a GenieSpaceExport object."""
        if self.serialized_space:
            return GenieSpaceExport.from_json(self.serialized_space)
        return None
