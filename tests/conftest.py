import pytest


@pytest.fixture(scope="session")
def spark():
    """A fast, local single-core SparkSession shared across the test session."""
    from pyspark.sql import SparkSession  # lazy import so non-Spark tests run without pyspark

    session = (
        SparkSession.builder.master("local[1]")
        .appName("dataops-tests")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()
