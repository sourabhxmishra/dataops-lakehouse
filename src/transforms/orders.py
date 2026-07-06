"""Pure, unit-testable PySpark transforms for the orders feed.

Every function is a `DataFrame -> DataFrame` with no side effects, so it runs the same
in a local SparkSession (CI/pytest) as it does on Databricks.
"""
from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql import types as T

RAW_COLUMNS = [
    "order_id",
    "customer_id",
    "order_date",
    "status",
    "quantity",
    "unit_price",
    "amount",
    "currency",
]


def read_orders_csv(spark: SparkSession, path: str) -> DataFrame:
    """Read the raw feed as all-strings; `clean_orders` does the typing.

    Reading as strings keeps parsing deterministic across environments and lets the
    data-quality gate see raw values (a bad number stays a bad number, not a null).
    """
    schema = T.StructType([T.StructField(c, T.StringType(), True) for c in RAW_COLUMNS])
    return spark.read.option("header", True).schema(schema).csv(path)


def clean_orders(df: DataFrame) -> DataFrame:
    """Trim, normalize casing, type the columns, and derive `amount` when missing."""
    quantity = F.col("quantity").cast(T.IntegerType())
    unit_price = F.col("unit_price").cast(T.DoubleType())
    return (
        df.withColumn("order_id", F.trim("order_id"))
        .withColumn("customer_id", F.trim("customer_id"))
        .withColumn("status", F.lower(F.trim("status")))
        .withColumn("currency", F.upper(F.trim("currency")))
        .withColumn("order_date", F.to_date("order_date"))
        .withColumn("quantity", quantity)
        .withColumn("unit_price", unit_price)
        .withColumn(
            "amount",
            F.coalesce(F.col("amount").cast(T.DoubleType()), F.round(quantity * unit_price, 2)),
        )
    )


def dedupe_latest(df: DataFrame, key: str = "order_id") -> DataFrame:
    """Keep one row per key — the latest by `order_date` — so re-runs are idempotent."""
    w = Window.partitionBy(key).orderBy(F.col("order_date").desc_nulls_last())
    return df.withColumn("_rn", F.row_number().over(w)).where(F.col("_rn") == 1).drop("_rn")


def gold_daily_revenue(df: DataFrame) -> DataFrame:
    """Business mart: revenue and order count per day and status."""
    return (
        df.groupBy("order_date", "status")
        .agg(F.round(F.sum("amount"), 2).alias("revenue"), F.count(F.lit(1)).alias("orders"))
        .orderBy("order_date", "status")
    )
