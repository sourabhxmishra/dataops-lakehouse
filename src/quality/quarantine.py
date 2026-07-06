"""Runtime quality gate: split a batch into clean rows and quarantined rows.

Clean rows continue to silver/gold; quarantined rows are written aside tagged with the
exact expectations they failed, so bad data is isolated and countable — never silently
shipped into a report.
"""
from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from src.quality.expectations import Expectation


def annotate(df: DataFrame, suite: list[Expectation]) -> DataFrame:
    """Add `_dq_reasons` (array of failed expectation names) and `_dq_valid` (bool)."""
    reasons = F.array_compact(F.array(*[F.when(~e.valid_col(), F.lit(e.name)) for e in suite]))
    return df.withColumn("_dq_reasons", reasons).withColumn("_dq_valid", F.size("_dq_reasons") == 0)


def split(df: DataFrame, suite: list[Expectation]) -> tuple[DataFrame, DataFrame]:
    """Return `(clean, quarantined)` — clean rows drop the DQ columns; bad rows keep reasons."""
    annotated = annotate(df, suite)
    clean = annotated.where("_dq_valid").drop("_dq_reasons", "_dq_valid")
    quarantined = annotated.where("NOT _dq_valid")
    return clean, quarantined
