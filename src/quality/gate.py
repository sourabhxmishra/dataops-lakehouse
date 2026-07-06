"""CI data-quality gate — fail the build when broken data would reach the lakehouse.

    python -m src.quality.gate data/orders.csv

Reads the feed, applies the standard transforms, runs the expectation suite plus a
uniqueness check, prints a report, and exits non-zero on any violation. This is what
blocks a pull request that introduces bad data — the code can be perfect and the merge
still fails because the *data* is wrong.
"""
from __future__ import annotations

import os
import sys

from pyspark.sql import SparkSession

from src.quality import slack
from src.quality.expectations import duplicate_keys, orders_suite, run_suite
from src.transforms.orders import clean_orders, read_orders_csv


def _run_context() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    ref = os.environ.get("GITHUB_REF_NAME", "")
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    return f" <{server}/{repo}/actions/runs/{run_id}|{repo}@{ref}>" if repo and run_id else ""


def _notify_slack(path, total, results, dups, violations):
    if not violations:
        text = f"✅ *Data-quality gate PASSED* — `{path}` ({total} rows).{_run_context()}"
    else:
        failed = [r.name for r in results if not r.passed] + (["order_id_unique"] if dups else [])
        text = (
            f"🛑 *Data-quality gate FAILED* — `{path}`: {violations} violation(s) "
            f"[{', '.join(failed)}].{_run_context()}"
        )
    print(f"Slack notification: {'sent' if slack.notify(text) else 'skipped (no SLACK_WEBHOOK_URL)'}")


def main(path: str) -> int:
    spark = (
        SparkSession.builder.master("local[1]")
        .appName("dq-gate")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")

    df = clean_orders(read_orders_csv(spark, path))
    total = df.count()
    results = run_suite(df, orders_suite())
    dups = duplicate_keys(df, "order_id")

    print(f"\nData-quality gate — {path}  ({total} rows)")
    print("-" * 54)
    for r in results:
        print(f"  {r.name:<26} {r.column:<12} " + ("PASS" if r.passed else f"FAIL ({r.failed})"))
    print(f"  {'order_id_unique':<26} {'order_id':<12} " + ("PASS" if dups == 0 else f"FAIL ({dups})"))
    print("-" * 54)

    violations = sum(r.failed for r in results) + dups
    _notify_slack(path, total, results, dups, violations)
    spark.stop()
    if violations:
        print(f"GATE FAILED — {violations} violation(s). Broken data blocked from prod.\n")
        return 1
    print("GATE PASSED — all expectations met.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "data/orders.csv"))
