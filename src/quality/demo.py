"""Runtime quarantine demo — show the split on a batch that contains bad rows.

    python -m src.quality.demo

Loads the clean feed, appends a few deliberately-bad rows (as a flaky upstream might
send), runs the quality split, and prints how many rows ship to gold vs get isolated
in quarantine — with the exact reason each bad row was held back. This is the runtime
counterpart to the CI gate: bad rows are quarantined, not shipped.
"""
from __future__ import annotations

from pyspark.sql import SparkSession

from src.quality.expectations import orders_suite
from src.quality.quarantine import split
from src.transforms.orders import clean_orders, read_orders_csv

# id, customer, date, status, qty, unit_price, amount, currency
BAD_ROWS = [
    ("O-9001", "C-01", "2026-06-06", "teleported", "1", "10.00", "10.00", "USD"),  # bad status
    ("O-9002", None, "2026-06-06", "placed", "2", "10.00", "20.00", "USD"),  # null customer
    ("O-9003", "C-02", "2026-06-06", "placed", "-3", "10.00", "-30.00", "USD"),  # neg qty + amount
    ("O-9004", "C-03", "2026-06-06", "shipped", "1", "10.00", "10.00", "BTC"),  # bad currency
]


def main() -> int:
    spark = (
        SparkSession.builder.master("local[1]")
        .appName("quarantine-demo")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    feed = read_orders_csv(spark, "data/orders.csv")
    bad = spark.createDataFrame(BAD_ROWS, feed.schema)
    batch = clean_orders(feed.unionByName(bad))
    clean, quarantined = split(batch, orders_suite())

    print(f"\nRuntime quality gate — batch of {batch.count()} rows")
    print("-" * 60)
    print(f"  clean       -> gold        : {clean.count()}")
    print(f"  quarantined -> quarantine  : {quarantined.count()}")
    print("-" * 60)
    quarantined.select(
        "order_id", "status", "currency", "quantity", "amount", "_dq_reasons"
    ).show(truncate=False)
    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
