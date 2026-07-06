"""A tiny, dependency-free Great-Expectations-style engine for Spark DataFrames.

Each `Expectation` carries a predicate `Column` that is True when a row is VALID; a
null predicate result (e.g. a null value in a range check) is treated as invalid. The
CI gate (block on failure) and the runtime quarantine (split bad rows) share the same
expectations, so what CI checks is exactly what runtime enforces.
"""
from __future__ import annotations

from dataclasses import dataclass

from pyspark.sql import Column, DataFrame
from pyspark.sql import functions as F

ORDER_STATUSES = ("placed", "shipped", "delivered", "cancelled", "returned")
CURRENCIES = ("USD", "EUR", "GBP")


# --- predicates: return a Column that is True when the row is VALID ---
def not_null(col: str) -> Column:
    return F.col(col).isNotNull()


def positive(col: str) -> Column:
    return F.col(col) > 0


def non_negative(col: str) -> Column:
    return F.col(col) >= 0


def in_set(col: str, allowed) -> Column:
    return F.col(col).isin(list(allowed))


@dataclass(frozen=True)
class Expectation:
    name: str
    column: str
    predicate: Column

    def valid_col(self) -> Column:
        # a null predicate result counts as invalid, not "unknown"
        return F.coalesce(self.predicate, F.lit(False))

    def failed_count(self, df: DataFrame) -> int:
        return df.where(~self.valid_col()).count()


@dataclass(frozen=True)
class ExpectationResult:
    name: str
    column: str
    failed: int

    @property
    def passed(self) -> bool:
        return self.failed == 0


def orders_suite() -> list[Expectation]:
    """The hard expectations for the orders feed — a violation blocks or quarantines."""
    return [
        Expectation("order_id_not_null", "order_id", not_null("order_id")),
        Expectation("customer_id_not_null", "customer_id", not_null("customer_id")),
        Expectation("quantity_positive", "quantity", positive("quantity")),
        Expectation("unit_price_non_negative", "unit_price", non_negative("unit_price")),
        Expectation("amount_non_negative", "amount", non_negative("amount")),
        Expectation("status_in_set", "status", in_set("status", ORDER_STATUSES)),
        Expectation("currency_in_set", "currency", in_set("currency", CURRENCIES)),
    ]


def run_suite(df: DataFrame, suite: list[Expectation]) -> list[ExpectationResult]:
    return [ExpectationResult(e.name, e.column, e.failed_count(df)) for e in suite]


def duplicate_keys(df: DataFrame, key: str = "order_id") -> int:
    """Count key values that appear more than once (a uniqueness expectation)."""
    return df.groupBy(key).count().where(F.col("count") > 1).count()
