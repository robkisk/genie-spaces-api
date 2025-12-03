#!/usr/bin/env python3
"""
Example: Building a Genie Space Configuration Programmatically

This script demonstrates how to use the genie-spaces-api SDK to build
a Genie Space configuration from scratch using Python code.

Run with: uv run python examples/programmatic_space_builder.py
"""

from genie_spaces_api import (
    Benchmarks,
    BenchmarkQuestion,
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


def build_ecommerce_analytics_space() -> GenieSpaceExport:
    """Build a complete e-commerce analytics Genie Space configuration."""

    # Define sample questions that will appear in the UI
    sample_questions = [
        SampleQuestion.from_text("What is our total revenue this month?"),
        SampleQuestion.from_text("Who are our top 10 customers by lifetime value?"),
        SampleQuestion.from_text("What products have the highest return rate?"),
        SampleQuestion.from_text("Show me daily order trends for the last 30 days"),
    ]

    # Define tables with column configurations
    orders_table = Table.create(
        identifier="ecommerce.prod.orders",
        description="All e-commerce orders including status and shipping info",
        column_configs=[
            ColumnConfig.create(
                column_name="order_id",
                description="Unique order identifier (UUID)",
                synonyms=["id", "order_number"],
                get_example_values=True,
            ),
            ColumnConfig.create(
                column_name="customer_id",
                description="Reference to the customer who placed the order",
                synonyms=["cust_id", "buyer_id"],
                build_value_dictionary=True,
            ),
            ColumnConfig.create(
                column_name="order_date",
                description="Timestamp when order was placed (UTC)",
                synonyms=["date", "created_at", "purchase_date"],
            ),
            ColumnConfig.create(
                column_name="status",
                description="Order status: pending, processing, shipped, delivered, returned, cancelled",
                synonyms=["order_status", "state"],
                build_value_dictionary=True,
                get_example_values=True,
            ),
            ColumnConfig.create(
                column_name="total_amount",
                description="Total order value in USD including tax and shipping",
                synonyms=["total", "order_total", "amount"],
            ),
            ColumnConfig.create(
                column_name="shipping_address_id",
                description="Reference to shipping address",
                exclude=True,  # Exclude PII-related columns
            ),
        ],
    )

    customers_table = Table.create(
        identifier="ecommerce.prod.customers",
        description="Customer master data with account information",
        column_configs=[
            ColumnConfig.create(
                column_name="customer_id",
                description="Unique customer identifier",
                synonyms=["id", "cust_id"],
            ),
            ColumnConfig.create(
                column_name="email",
                description="Customer email address",
                exclude=True,  # Exclude PII
            ),
            ColumnConfig.create(
                column_name="segment",
                description="Customer segment: Bronze, Silver, Gold, Platinum",
                synonyms=["tier", "level", "customer_type"],
                build_value_dictionary=True,
                get_example_values=True,
            ),
            ColumnConfig.create(
                column_name="acquisition_channel",
                description="How the customer was acquired",
                synonyms=["channel", "source"],
                build_value_dictionary=True,
            ),
            ColumnConfig.create(
                column_name="created_at",
                description="When customer account was created",
                synonyms=["signup_date", "registration_date"],
            ),
        ],
    )

    products_table = Table.create(
        identifier="ecommerce.prod.products",
        description="Product catalog with pricing and inventory",
        column_configs=[
            ColumnConfig.create(
                column_name="product_id",
                description="Unique product identifier",
                synonyms=["id", "sku", "item_id"],
            ),
            ColumnConfig.create(
                column_name="name",
                description="Product display name",
                synonyms=["product_name", "title"],
            ),
            ColumnConfig.create(
                column_name="category",
                description="Product category",
                synonyms=["product_category", "type"],
                build_value_dictionary=True,
                get_example_values=True,
            ),
            ColumnConfig.create(
                column_name="price",
                description="Current selling price in USD",
                synonyms=["unit_price", "cost"],
            ),
        ],
    )

    # Define metric views
    metric_views = [
        MetricView.create(
            identifier="ecommerce.analytics.daily_sales_mv",
            description="Pre-aggregated daily sales metrics by category and segment",
        ),
        MetricView.create(
            identifier="ecommerce.analytics.customer_ltv_mv",
            description="Customer lifetime value calculations, updated weekly",
        ),
    ]

    # Define text instructions
    text_instruction = TextInstruction.from_text(
        """## Data Conventions
- All timestamps are in UTC
- Monetary values are in USD
- Fiscal year starts January 1st

## Query Guidelines
- Use DATE_TRUNC for period aggregations
- Always exclude cancelled orders unless specifically asked
- Customer segments: Bronze < $100/yr, Silver $100-500, Gold $500-2000, Platinum > $2000

## Response Formatting
- Format currency with $ and 2 decimal places
- Use percentages with 1 decimal place
- Format large numbers with thousands separators"""
    )

    # Define SQL examples
    sql_examples = [
        ExampleQuestionSql.create(
            question="What are the top N products by revenue in a date range?",
            sql="""SELECT
    p.name as product_name,
    p.category,
    COUNT(DISTINCT o.order_id) as order_count,
    SUM(oi.quantity * oi.unit_price) as total_revenue
FROM ecommerce.prod.orders o
JOIN ecommerce.prod.order_items oi ON o.order_id = oi.order_id
JOIN ecommerce.prod.products p ON oi.product_id = p.product_id
WHERE o.order_date BETWEEN :start_date AND :end_date
  AND o.status NOT IN ('cancelled', 'returned')
GROUP BY p.name, p.category
ORDER BY total_revenue DESC
LIMIT :limit_n""",
            parameters=[
                Parameter.create("start_date", "DATE", "Start of date range (inclusive)"),
                Parameter.create("end_date", "DATE", "End of date range (inclusive)"),
                Parameter.create("limit_n", "INTEGER", "Number of products to return"),
            ],
            usage_guidance="Use for top-N product analysis. Adjust ORDER BY for different metrics.",
        ),
        ExampleQuestionSql.create(
            question="Calculate customer cohort retention rates",
            sql="""WITH cohorts AS (
    SELECT
        customer_id,
        DATE_TRUNC('month', MIN(order_date)) as cohort_month
    FROM ecommerce.prod.orders
    WHERE status NOT IN ('cancelled')
    GROUP BY customer_id
),
activity AS (
    SELECT
        c.cohort_month,
        DATE_TRUNC('month', o.order_date) as activity_month,
        COUNT(DISTINCT o.customer_id) as active_customers
    FROM cohorts c
    JOIN ecommerce.prod.orders o ON c.customer_id = o.customer_id
    WHERE o.status NOT IN ('cancelled')
    GROUP BY c.cohort_month, DATE_TRUNC('month', o.order_date)
)
SELECT
    cohort_month,
    activity_month,
    MONTHS_BETWEEN(activity_month, cohort_month) as months_since_cohort,
    active_customers,
    FIRST_VALUE(active_customers) OVER (PARTITION BY cohort_month ORDER BY activity_month) as cohort_size,
    ROUND(active_customers * 100.0 / FIRST_VALUE(active_customers) OVER (PARTITION BY cohort_month ORDER BY activity_month), 1) as retention_pct
FROM activity
ORDER BY cohort_month, activity_month""",
            usage_guidance="Template for cohort analysis. Adjust time granularity as needed.",
        ),
    ]

    # Define SQL functions
    sql_functions = [
        SqlFunction(id="func1", identifier="ecommerce.udfs.calculate_ltv"),
        SqlFunction(id="func2", identifier="ecommerce.udfs.categorize_customer"),
    ]

    # Define join specifications
    join_specs = [
        JoinSpec.create(
            left_identifier="ecommerce.prod.orders",
            left_alias="o",
            right_identifier="ecommerce.prod.customers",
            right_alias="c",
            join_condition="o.customer_id = c.customer_id",
            comment="Join orders to customers for segmentation and demographics",
        ),
        JoinSpec.create(
            left_identifier="ecommerce.prod.orders",
            left_alias="o",
            right_identifier="ecommerce.prod.order_items",
            right_alias="oi",
            join_condition="o.order_id = oi.order_id",
            comment="Join orders to line items for product-level analysis",
        ),
    ]

    # Define benchmark questions
    benchmarks = Benchmarks(
        questions=[
            BenchmarkQuestion.create(
                question="What was total revenue last month?",
                sql_answer="""SELECT SUM(total_amount) as total_revenue
FROM ecommerce.prod.orders
WHERE order_date >= DATE_TRUNC('month', DATE_ADD(CURRENT_DATE, -30))
  AND order_date < DATE_TRUNC('month', CURRENT_DATE)
  AND status NOT IN ('cancelled', 'returned')""",
            ),
            BenchmarkQuestion.create(
                question="How many unique customers made purchases this week?",
                sql_answer="""SELECT COUNT(DISTINCT customer_id) as unique_customers
FROM ecommerce.prod.orders
WHERE order_date >= DATE_TRUNC('week', CURRENT_DATE)
  AND status NOT IN ('cancelled')""",
            ),
            BenchmarkQuestion.create(
                question="What is the average order value by customer segment?",
                sql_answer="""SELECT
    c.segment,
    AVG(o.total_amount) as avg_order_value,
    COUNT(DISTINCT o.order_id) as order_count
FROM ecommerce.prod.orders o
JOIN ecommerce.prod.customers c ON o.customer_id = c.customer_id
WHERE o.status NOT IN ('cancelled', 'returned')
GROUP BY c.segment
ORDER BY avg_order_value DESC""",
            ),
        ]
    )

    # Assemble the complete configuration
    return GenieSpaceExport(
        version=1,
        config=GenieSpaceConfig(sample_questions=sample_questions),
        data_sources=DataSources(
            tables=[orders_table, customers_table, products_table],
            metric_views=metric_views,
        ),
        instructions=Instructions(
            text_instructions=[text_instruction],
            example_question_sqls=sql_examples,
            sql_functions=sql_functions,
            join_specs=join_specs,
        ),
        benchmarks=benchmarks,
    )


def main():
    """Build and export the configuration."""
    print("Building e-commerce analytics Genie Space configuration...")

    # Build the configuration
    config = build_ecommerce_analytics_space()

    # Export to file
    output_path = "examples/ecommerce_analytics_space.json"
    config.to_file(output_path)
    print(f"✓ Configuration exported to: {output_path}")

    # Print summary
    print("\n📊 Configuration Summary:")
    print(f"  - Sample Questions: {len(config.config.sample_questions)}")
    print(f"  - Tables: {len(config.data_sources.tables)}")
    print(f"  - Metric Views: {len(config.data_sources.metric_views)}")
    print(f"  - Text Instructions: {len(config.instructions.text_instructions)}")
    print(f"  - SQL Examples: {len(config.instructions.example_question_sqls)}")
    print(f"  - SQL Functions: {len(config.instructions.sql_functions)}")
    print(f"  - Join Specs: {len(config.instructions.join_specs)}")
    print(f"  - Benchmarks: {len(config.benchmarks.questions)}")

    # Show a preview
    print("\n📝 JSON Preview (first 500 chars):")
    print(config.to_json()[:500] + "...")


if __name__ == "__main__":
    main()
