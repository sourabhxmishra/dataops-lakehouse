from pyspark.sql import types as T

from src.quality.expectations import duplicate_keys, orders_suite, run_suite
from src.quality.quarantine import split
from src.transforms.orders import RAW_COLUMNS, clean_orders

GOOD = ("O-1", "C-1", "2026-06-01", "placed", "2", "10.0", "20.0", "USD")


def _orders(spark, rows):
    schema = T.StructType([T.StructField(c, T.StringType(), True) for c in RAW_COLUMNS])
    return clean_orders(spark.createDataFrame(rows, schema))


def test_suite_passes_clean_data(spark):
    df = _orders(spark, [GOOD])
    assert all(r.passed for r in run_suite(df, orders_suite()))


def test_suite_flags_bad_rows(spark):
    df = _orders(
        spark,
        [
            GOOD,
            ("O-2", "C-2", "2026-06-01", "teleported", "1", "10.0", "10.0", "USD"),  # bad status
            ("O-3", None, "2026-06-01", "placed", "0", "10.0", "0.0", "USD"),  # null cust + qty 0
            ("O-4", "C-4", "2026-06-01", "placed", "1", "-5.0", "-5.0", "USD"),  # neg price + amount
        ],
    )
    failed = {r.name: r.failed for r in run_suite(df, orders_suite())}
    assert failed["status_in_set"] == 1
    assert failed["customer_id_not_null"] == 1
    assert failed["quantity_positive"] == 1
    assert failed["unit_price_non_negative"] == 1
    assert failed["amount_non_negative"] == 1


def test_quarantine_splits_and_labels(spark):
    df = _orders(
        spark,
        [GOOD, ("O-2", "C-2", "2026-06-01", "teleported", "1", "10.0", "10.0", "USD")],
    )
    clean, bad = split(df, orders_suite())
    assert clean.count() == 1
    assert bad.count() == 1
    assert "status_in_set" in bad.collect()[0]["_dq_reasons"]


def test_duplicate_keys_detected(spark):
    df = _orders(spark, [GOOD, ("O-1", "C-9", "2026-06-02", "shipped", "1", "5.0", "5.0", "USD")])
    assert duplicate_keys(df, "order_id") == 1
