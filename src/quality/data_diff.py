"""Data-diff for pull requests — summarize how a PR changes the *data*, not just the code.

    python -m src.quality.data_diff <baseline.csv> <current.csv>

Prints a Markdown report — row-count delta, per-`status` and per-`currency` distribution shifts
(flagging brand-new values), null/empty-cell changes, and the amount total — that a CI job posts
as a comment on the PR. A reviewer sees the data impact of a change at a glance, so a suspicious
new `status` or a jump in null keys is obvious *before* merge.

Intentionally dependency-free (stdlib only) so the PR comment is near-instant; the same idea scales
to Spark for large feeds.
"""
from __future__ import annotations

import csv
import sys
from collections import Counter

DIST_COLUMNS = ("status", "currency")


def load(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def dist(rows: list[dict], col: str) -> Counter:
    return Counter((r.get(col) or "").strip() for r in rows)


def null_count(rows: list[dict], col: str) -> int:
    return sum(1 for r in rows if not (r.get(col) or "").strip())


def amount_total(rows: list[dict], col: str = "amount") -> float:
    total = 0.0
    for r in rows:
        try:
            total += float(r.get(col) or 0)
        except ValueError:
            pass
    return total


def _delta(a: int, b: int) -> str:
    d = b - a
    return f"+{d}" if d > 0 else str(d) if d < 0 else "0"


def _table(title: str, base: Counter, curr: Counter) -> list[str]:
    out = [f"**{title}**", "", "| value | main | PR | Δ |", "|---|--:|--:|--:|"]
    for k in sorted(set(base) | set(curr)):
        a, b = base.get(k, 0), curr.get(k, 0)
        note = " — new ⚠️" if a == 0 and b else " — gone" if b == 0 and a else ""
        out.append(f"| `{k or '∅ empty'}`{note} | {a} | {b} | {_delta(a, b)} |")
    out.append("")
    return out


def report(baseline: list[dict], current: list[dict], path: str) -> str:
    out = [
        f"## 📊 Data-diff — `{path}`",
        "",
        f"**Rows:** {len(baseline)} → {len(current)}  (**{_delta(len(baseline), len(current))}**)",
        "",
    ]
    for col in DIST_COLUMNS:
        out += _table(col, dist(baseline, col), dist(current, col))

    columns = list(current[0].keys()) if current else list(baseline[0].keys()) if baseline else []
    nulls = [(c, null_count(baseline, c), null_count(current, c)) for c in columns]
    nulls = [(c, a, b) for c, a, b in nulls if a or b]
    if nulls:
        out += ["**Null / empty cells**", "", "| column | main | PR |", "|---|--:|--:|"]
        out += [f"| `{c}` | {a} | {b} |" for c, a, b in nulls]
        out.append("")

    out.append(f"**Σ amount:** {amount_total(baseline):,.2f} → {amount_total(current):,.2f}")
    return "\n".join(out)


def main(baseline_path: str, current_path: str) -> int:
    print(report(load(baseline_path), load(current_path), "data/orders.csv"))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python -m src.quality.data_diff <baseline.csv> <current.csv>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
