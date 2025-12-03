"""Tests for Pydantic models."""

import json

import pytest

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
    JoinSpec,
    MetricView,
    Parameter,
    SampleQuestion,
    SqlFunction,
    Table,
    TextInstruction,
)


class TestSampleQuestion:
    """Tests for SampleQuestion model."""

    def test_from_text_simple(self):
        """Test creating a sample question from simple text."""
        sq = SampleQuestion.from_text("What is the total revenue?")
        assert sq.question == ["What is the total revenue?"]
        assert len(sq.id) == 32  # UUID without dashes

    def test_from_text_multiline(self):
        """Test creating a sample question from multiline text."""
        sq = SampleQuestion.from_text("Line 1\nLine 2\nLine 3")
        assert sq.question == ["Line 1", "Line 2", "Line 3"]

    def test_from_text_with_custom_id(self):
        """Test creating with a custom ID."""
        sq = SampleQuestion.from_text("Question", id="custom123")
        assert sq.id == "custom123"


class TestColumnConfig:
    """Tests for ColumnConfig model."""

    def test_create_minimal(self):
        """Test creating minimal column config."""
        col = ColumnConfig.create("order_id")
        assert col.column_name == "order_id"
        assert col.description is None
        assert col.synonyms is None

    def test_create_full(self):
        """Test creating column config with all options."""
        col = ColumnConfig.create(
            column_name="order_id",
            description="Primary key",
            synonyms=["id", "orderid"],
            exclude=False,
            get_example_values=True,
            build_value_dictionary=True,
        )
        assert col.column_name == "order_id"
        assert col.description == ["Primary key"]
        assert col.synonyms == ["id", "orderid"]
        assert col.get_example_values is True
        assert col.build_value_dictionary is True


class TestTable:
    """Tests for Table model."""

    def test_create_minimal(self):
        """Test creating minimal table config."""
        table = Table.create("catalog.schema.table")
        assert table.identifier == "catalog.schema.table"
        assert table.description is None
        assert table.column_configs is None

    def test_create_with_columns(self):
        """Test creating table with column configs."""
        table = Table.create(
            identifier="sales.prod.orders",
            description="Order data",
            column_configs=[
                ColumnConfig.create("order_id", description="Primary key"),
                ColumnConfig.create("customer_id"),
            ],
        )
        assert table.identifier == "sales.prod.orders"
        assert table.description == ["Order data"]
        assert len(table.column_configs) == 2


class TestExampleQuestionSql:
    """Tests for ExampleQuestionSql model."""

    def test_create_simple(self):
        """Test creating simple SQL example."""
        ex = ExampleQuestionSql.create(
            question="What is total revenue?",
            sql="SELECT SUM(amount) FROM orders",
        )
        assert ex.question == ["What is total revenue?"]
        assert "SELECT SUM(amount) FROM orders" in ex.sql

    def test_create_with_parameters(self):
        """Test creating SQL example with parameters."""
        ex = ExampleQuestionSql.create(
            question="Top N products",
            sql="SELECT * FROM products LIMIT :n",
            parameters=[
                Parameter.create("n", "INTEGER", "Number of results"),
            ],
            usage_guidance="Use for top-N queries",
        )
        assert len(ex.parameters) == 1
        assert ex.parameters[0].name == "n"
        assert ex.parameters[0].type_hint == "INTEGER"
        assert ex.usage_guidance == ["Use for top-N queries"]


class TestJoinSpec:
    """Tests for JoinSpec model."""

    def test_create(self):
        """Test creating join specification."""
        join = JoinSpec.create(
            left_identifier="sales.orders",
            left_alias="o",
            right_identifier="sales.customers",
            right_alias="c",
            join_condition="o.customer_id = c.id",
            comment="Join for customer details",
        )
        assert join.left.identifier == "sales.orders"
        assert join.left.alias == "o"
        assert join.right.identifier == "sales.customers"
        assert join.right.alias == "c"
        assert join.sql == ["o.customer_id = c.id"]
        assert join.comment == ["Join for customer details"]


class TestBenchmarkQuestion:
    """Tests for BenchmarkQuestion model."""

    def test_create(self):
        """Test creating benchmark question."""
        bq = BenchmarkQuestion.create(
            question="Total revenue?",
            sql_answer="SELECT SUM(revenue) FROM sales",
        )
        assert bq.question == ["Total revenue?"]
        assert len(bq.answer) == 1
        assert bq.answer[0].format == "SQL"


class TestGenieSpaceExport:
    """Tests for GenieSpaceExport model."""

    def test_empty_export(self):
        """Test creating empty export."""
        export = GenieSpaceExport()
        assert export.version == 1
        assert export.config is None
        assert export.data_sources is None

    def test_to_json(self):
        """Test JSON serialization."""
        export = GenieSpaceExport(
            config=GenieSpaceConfig(
                sample_questions=[SampleQuestion.from_text("Test question")]
            )
        )
        json_str = export.to_json()
        data = json.loads(json_str)
        assert data["version"] == 1
        assert "sample_questions" in data["config"]

    def test_from_json(self):
        """Test JSON deserialization."""
        json_str = """
        {
            "version": 1,
            "config": {
                "sample_questions": [
                    {"id": "abc123", "question": ["Test?"]}
                ]
            }
        }
        """
        export = GenieSpaceExport.from_json(json_str)
        assert export.version == 1
        assert len(export.config.sample_questions) == 1

    def test_roundtrip(self):
        """Test JSON roundtrip serialization."""
        original = GenieSpaceExport(
            version=1,
            config=GenieSpaceConfig(
                sample_questions=[
                    SampleQuestion.from_text("Question 1"),
                    SampleQuestion.from_text("Question 2"),
                ]
            ),
            data_sources=DataSources(
                tables=[
                    Table.create(
                        "catalog.schema.table",
                        description="Test table",
                        column_configs=[
                            ColumnConfig.create("col1", synonyms=["c1"]),
                        ],
                    )
                ],
                metric_views=[
                    MetricView.create("catalog.schema.mv", description="Test MV"),
                ],
            ),
            instructions=Instructions(
                text_instructions=[
                    TextInstruction.from_text("Instruction content"),
                ],
                example_question_sqls=[
                    ExampleQuestionSql.create("Q?", "SELECT 1"),
                ],
            ),
            benchmarks=Benchmarks(
                questions=[
                    BenchmarkQuestion.create("Benchmark Q", "SELECT 2"),
                ]
            ),
        )

        # Roundtrip
        json_str = original.to_json()
        restored = GenieSpaceExport.from_json(json_str)

        # Verify structure
        assert restored.version == original.version
        assert len(restored.config.sample_questions) == 2
        assert len(restored.data_sources.tables) == 1
        assert len(restored.data_sources.metric_views) == 1
        assert len(restored.instructions.text_instructions) == 1
        assert len(restored.instructions.example_question_sqls) == 1
        assert len(restored.benchmarks.questions) == 1

    def test_to_dict_excludes_none(self):
        """Test that to_dict excludes None values."""
        export = GenieSpaceExport(
            config=GenieSpaceConfig(sample_questions=[])
        )
        data = export.to_dict()
        assert "data_sources" not in data
        assert "instructions" not in data
        assert "benchmarks" not in data


class TestCompleteConfiguration:
    """Integration tests for complete configurations."""

    def test_full_configuration(self):
        """Test building a complete configuration."""
        config = GenieSpaceExport(
            version=1,
            config=GenieSpaceConfig(
                sample_questions=[
                    SampleQuestion.from_text("What is total revenue?"),
                    SampleQuestion.from_text("Top customers?"),
                ]
            ),
            data_sources=DataSources(
                tables=[
                    Table.create(
                        "sales.prod.orders",
                        description="Orders table",
                        column_configs=[
                            ColumnConfig.create(
                                "order_id",
                                description="PK",
                                synonyms=["id"],
                                get_example_values=True,
                            ),
                            ColumnConfig.create(
                                "customer_id",
                                build_value_dictionary=True,
                            ),
                        ],
                    ),
                ],
                metric_views=[
                    MetricView.create(
                        "sales.analytics.revenue_mv",
                        description="Daily revenue",
                    ),
                ],
            ),
            instructions=Instructions(
                text_instructions=[
                    TextInstruction.from_text("Use DATE for dates"),
                ],
                example_question_sqls=[
                    ExampleQuestionSql.create(
                        question="Top N products",
                        sql="SELECT * FROM products LIMIT :n",
                        parameters=[
                            Parameter.create("n", "INTEGER", "Limit"),
                        ],
                    ),
                ],
                sql_functions=[
                    SqlFunction(id="f1", identifier="sales.udfs.calc"),
                ],
                join_specs=[
                    JoinSpec.create(
                        "orders", "o",
                        "customers", "c",
                        "o.cust_id = c.id",
                    ),
                ],
            ),
            benchmarks=Benchmarks(
                questions=[
                    BenchmarkQuestion.create(
                        "Revenue last month?",
                        "SELECT SUM(amount) FROM orders WHERE date > ...",
                    ),
                ]
            ),
        )

        # Serialize and verify
        json_str = config.to_json()
        data = json.loads(json_str)

        assert data["version"] == 1
        assert len(data["config"]["sample_questions"]) == 2
        assert len(data["data_sources"]["tables"]) == 1
        assert len(data["data_sources"]["metric_views"]) == 1
        assert len(data["instructions"]["text_instructions"]) == 1
        assert len(data["instructions"]["example_question_sqls"]) == 1
        assert len(data["instructions"]["sql_functions"]) == 1
        assert len(data["instructions"]["join_specs"]) == 1
        assert len(data["benchmarks"]["questions"]) == 1
