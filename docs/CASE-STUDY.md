# 📝 Case Study — Broken data can't reach prod

**TL;DR** — I wrapped a lakehouse in a real DataOps pipeline: PySpark transforms are unit-tested,
a **data-quality gate** validates the *data itself* on every push, and promotion flows
**dev → test → prod** behind approvals. A pull request that introduces bad data is **blocked**; at
runtime, bad rows are **quarantined** with the reason they failed — never silently shipped. The
whole thing runs on GitHub Actions, so the proof is a green vs red pipeline.

## 🎯 The problem

Most data pipelines test the *code* but never the *data*. A schema-valid file full of garbage —
a negative amount, a typo'd status, a null key — sails straight through to a dashboard, and someone
notices days later after a number looks wrong. I wanted failed **data** to block the release, exactly
like a failing unit test blocks a merge.

## 🧭 The design

- **Code quality:** `ruff` + `pytest` over pure `DataFrame → DataFrame` PySpark transforms. A
  session-scoped local `SparkSession` fixture keeps the tests fast and CI-friendly — genuine
  unit-testing of Spark, no cluster required.
- **Data quality:** a tiny Great-Expectations-style engine. Each expectation is a predicate that's
  True when a row is valid (`not_null`, `positive`, `non_negative`, `in_set`). A **CI gate** runs the
  suite and exits non-zero on any violation.
- **Runtime quarantine:** the *same* suite tags each row with the expectations it failed and splits
  the batch — clean rows to gold, invalid rows to a quarantine table with `_dq_reasons`.
- **Promotion:** env-parameterized IaC (Bicep, plus a Terraform variant) deploys per environment;
  GitHub **environments** add manual approval gates for `test` and `prod`.

## ⚖️ The tradeoffs

- **Strictness vs. throughput:** a hard gate can block delivery on a bad upstream day — so runtime
  uses **quarantine, not fail-closed**: good rows keep flowing while bad rows are isolated.
- **Custom engine vs. Great Expectations/DQX:** I shipped a tiny, dependency-light engine so CI is
  fast and the semantics are obvious; the same shape maps directly onto GE or Databricks DQX at
  scale.
- **CI gate vs. runtime gate:** CI catches bad data *before* deploy; the runtime split catches what
  only shows up in real data. I use both, backed by one suite.
- **Bicep vs. Terraform:** shipped both to show portability; each is validated in CI.

## 🛠️ The real problems I hit (and fixed)

1. **Silent coercion hid bad data.** Reading the CSV with an inferred/typed schema quietly turned a
   bad number into `null`, so the gate couldn't see it. **Fix:** read the feed **as strings** and
   validate after typing — a bad value stays catchable.
2. **Nulls slipped through range checks.** `amount >= 0` is *null* (not False) when `amount` is null,
   so `~predicate` wouldn't flag it. **Fix:** `coalesce(predicate, false)` — a null result counts as
   **invalid**, never "unknown."
3. **Unit-testing Spark in CI.** Spark needs a JVM. **Fix:** `actions/setup-java` (Temurin 17) + a
   `local[1]` SparkSession fixture — fast, deterministic tests on every push.
4. **A red badge with no cloud creds.** A `push`-triggered CD would fail (no `AZURE_CREDENTIALS`) and
   redden the repo. **Fix:** CD is `workflow_dispatch` with environment approvals — a faithful
   promotion that keeps the badge honest.

## 📈 The outcome

- A pull request that adds a bad status, a null customer, and a negative amount is **blocked** by the
  data-quality gate — the code was fine, the *data* wasn't.
- Clean data passes lint + PySpark tests + the gate + Bicep/Terraform validation — all green.
- At runtime, a mixed batch splits cleanly: good rows to gold, bad rows to quarantine tagged with the
  exact expectations they failed.
- `test` and `prod` deployments require a reviewer — a clean audit trail for every change.

## 🎓 What I learned

- **Test the data, not just the code** — it's the sneakiest class of bug, and the cheapest to gate.
- **Read raw, validate typed** keeps bad values catchable instead of silently null.
- **Quarantine over fail-closed** keeps delivery moving while isolating the bad rows.
- **One suite, two enforcers** (CI + runtime) means what you test is exactly what you ship.

## 🔭 What I'd add next

Data-diff on PRs (row-count and distribution deltas), a Slack summary of the gate results, and
swapping the tiny engine for Great Expectations / Databricks DQX on a live medallion.

---

*Repo: <https://github.com/sourabhxmishra/dataops-lakehouse>*
