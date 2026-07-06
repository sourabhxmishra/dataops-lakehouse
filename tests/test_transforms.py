from pyspark.sql import types as T

from src.transforms.orders import (
    RAW_COLUMNS,
    clean_orders,
    dedupe_latest,
    gold_daily_revenue,
)


def _raw(spark, rows):
    schema = T.StructType([T.StructField(c, T.StringType(), True) for c in RAW_COLUMNS])
    return spark.createDataFrame(rows, schema)


def test_clean_types_and_normalizes(spark):
    df = _raw(spark, [("O-1", "C-1", "2026-06-01", " Placed ", "2", "10.0", None, "usd")])
    row = clean_orders(df).collect()[0]
    assert row["status"] == "placed"
    assert row["currency"] == "USD"
    assert row["quantity"] == 2
    assert row["amount"] == 20.0  # derived from quantity * unit_price
    assert str(row["order_date"]) == "2026-06-01"


def test_dedupe_keeps_latest(spark):
    df = clean_orders(
        _raw(
            spark,
            [
                ("O-1", "C-1", "2026-06-01", "placed", "1", "10.0", "10.0", "USD"),
                ("O-1", "C-1", "2026-06-03", "delivered", "1", "10.0", "10.0", "USD"),
            ],
        )
    )
    out = dedupe_latest(df).collect()
    assert len(out) == 1
    assert out[0]["status"] == "delivered"


def test_gold_daily_revenue(spark):
    df = clean_orders(
        _raw(
            spark,
            [
                ("O-1", "C-1", "2026-06-01", "placed", "2", "10.0", "20.0", "USD"),
                ("O-2", "C-2", "2026-06-01", "placed", "1", "30.0", "30.0", "USD"),
            ],
        )
    )
    row = gold_daily_revenue(df).collect()[0]
    assert row["orders"] == 2
    assert row["revenue"] == 50.0
