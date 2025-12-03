"""
Databricks Genie Spaces API SDK

A Python SDK for managing Databricks Genie Spaces via the Import/Export API.
Enables CI/CD workflows, cross-workspace migrations, and programmatic space management.
"""

from genie_spaces_api.client import GenieSpacesClient
from genie_spaces_api.models import (
    BenchmarkAnswer,
    BenchmarkQuestion,
    Benchmarks,
    ColumnConfig,
    DataSources,
    ExampleQuestionSql,
    GenieSpaceConfig,
    GenieSpaceExport,
    Instructions,
    JoinSource,
    JoinSpec,
    MetricView,
    Parameter,
    SampleQuestion,
    SpaceResponse,
    SqlFunction,
    Table,
    TextInstruction,
)

__version__ = "0.1.0"
__all__ = [
    "GenieSpacesClient",
    "GenieSpaceExport",
    "GenieSpaceConfig",
    "SampleQuestion",
    "DataSources",
    "Table",
    "ColumnConfig",
    "MetricView",
    "Instructions",
    "TextInstruction",
    "ExampleQuestionSql",
    "Parameter",
    "SqlFunction",
    "JoinSpec",
    "JoinSource",
    "Benchmarks",
    "BenchmarkQuestion",
    "BenchmarkAnswer",
    "SpaceResponse",
]
