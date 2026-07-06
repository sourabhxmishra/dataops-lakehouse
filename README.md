# 🛡️ DataOps — CI/CD Lakehouse with Data-Quality Gates

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
![IaC](https://img.shields.io/badge/IaC-Bicep%20%2B%20Terraform-blue)
![Tested](https://img.shields.io/badge/tested-PySpark-orange)
![Data quality](https://img.shields.io/badge/data--quality-gated-brightgreen)

> **Broken data can't reach prod — the pipeline gates it.**
> Every push runs `ruff` + **PySpark unit tests** + a **data-quality gate**. A pull request that
> introduces bad *data* — not just bad code — is **blocked**. At runtime, bad rows are
> **quarantined** with the reason they failed, never silently shipped. Promotion flows
> **dev → test → prod** behind GitHub environment approvals.

📖 **Docs:** [Step-by-step build](docs/WALKTHROUGH.md) · [Case study & lessons learned](docs/CASE-STUDY.md)

---

## 🗺️ Architecture

```mermaid
flowchart LR
    PR["🔀 Pull Request"] --> CI

    subgraph CI["✅ CI — quality gate · GitHub Actions"]
        direction TB
        L["ruff lint"] --> U["pytest<br/>PySpark transforms"] --> GE["data-quality<br/>expectations"]
    end

    CI -->|pass| M["🟢 merge to main"]
    CI -->|fail| X["❌ blocked"]

    M --> DEV["deploy dev"] --> A1{{"approval"}} --> TEST["deploy test"] --> A2{{"approval"}} --> PROD["deploy prod"]

    subgraph RUN["🛡️ Runtime gate"]
        DQ["quality split"]
        Q[("🗃️ quarantine<br/>bad rows + reasons")]
    end
    PROD --> DQ -->|clean| GOOD["🥇 gold"]
    DQ -->|invalid| Q

    classDef ok fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef bad fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    class M,GOOD ok;
    class X,Q bad;
```

---

## 🛡️ What's gated

| Stage | Check | On failure |
|-------|-------|-----------|
| PR / push | `ruff` lint | block merge |
| PR / push | `pytest` — PySpark transforms | block merge |
| PR / push | **data-quality gate** on the feed | **block merge** |
| PR / push | Bicep build + Terraform validate | block merge |
| Deploy | environment approval (test, prod) | pause for review |
| Runtime | expectation split | **quarantine** bad rows |

---

## 🧠 Why it's senior (not a toy)

| Concern | How it's handled |
|---------|------------------|
| **Test the data, not just the code** | a green build can still fail because the *data* is wrong — the gate runs the same expectations CI checks and runtime enforces |
| **Unit-testing Spark** | pure `DataFrame → DataFrame` transforms + a local `SparkSession` fixture keep tests fast and CI-friendly |
| **Deterministic parsing** | the feed is read as **strings** so a bad number stays bad (it can be *caught*), instead of silently parsing to `null` |
| **Honest null semantics** | a null predicate result counts as **invalid**, never "unknown" — no bad row slips through on a null |
| **Quarantine, not fail-closed** | one bad upstream day doesn't stop delivery — good rows flow, bad rows are isolated and countable |
| **Promotion with approvals** | GitHub **environments** gate `test` and `prod` — a clean audit trail for every change |
| **Portable IaC** | the same infra in **Bicep _and_ Terraform**, both validated in CI |

---

## ✅ Proof — the gate in action

### ❌ A PR with broken data is blocked *(the money shot)*
A pull request adds rows with a bad status, a null customer, and a negative amount. The code is
fine — but the **data-quality gate fails**, so the PR can't merge.

![CI red — the data-quality gate blocks a bad-data PR](docs/img/ci-red-gate.png)

### ✅ Clean data passes every gate
On `main`, lint + PySpark tests + the data-quality gate + Bicep/Terraform validation are all green.

![CI green — all gates pass](docs/img/ci-green.png)

### 🗃️ Runtime quarantine — bad rows isolated with reasons
At runtime the batch is split: clean rows go to gold; bad rows go to quarantine tagged with the
exact expectations they failed.

![Quarantine split — clean vs quarantined with reasons](docs/img/quarantine.png)

### 🔐 dev → test → prod behind approvals
`test` and `prod` require a reviewer to approve before a deployment proceeds.

![GitHub environments with required approvals](docs/img/environments.png)

---

## 🔎 The gate, in code

Expectations are plain predicates that are **True when a row is valid** — shared by CI (block) and
runtime (quarantine):

```python
def orders_suite():
    return [
        Expectation("order_id_not_null",      "order_id",   not_null("order_id")),
        Expectation("quantity_positive",      "quantity",   positive("quantity")),
        Expectation("amount_non_negative",    "amount",     non_negative("amount")),
        Expectation("status_in_set",          "status",     in_set("status", ORDER_STATUSES)),
        Expectation("currency_in_set",        "currency",   in_set("currency", CURRENCIES)),
    ]
```

The **CI gate** runs the suite and exits non-zero on any violation (that's what blocks the PR). The
**runtime quarantine** uses the same suite to tag and split each batch:

```python
clean, quarantined = split(batch, orders_suite())   # clean → gold, bad → quarantine (+ _dq_reasons)
```

---

## 🧱 Tech stack

PySpark (unit-tested transforms + quality engine) · `pytest` + `ruff` · GitHub Actions (CI/CD +
environment approvals) · **Bicep + Terraform** IaC · Azure Databricks + ADLS Gen2 medallion (the
deploy target)

---

## 📁 Repo structure

```text
dataops-lakehouse/
├── .github/workflows/
│   ├── ci.yml                  # PR/push: ruff + pytest + data-quality gate + IaC validate
│   └── cd.yml                  # manual promotion: dev → test → prod (environment approvals)
├── src/
│   ├── transforms/orders.py    # pure, testable PySpark transforms
│   └── quality/
│       ├── expectations.py     # tiny GE-style expectation engine (shared by CI + runtime)
│       ├── quarantine.py       # split a batch → clean vs quarantined (+ reasons)
│       ├── gate.py             # CI gate — exits non-zero on any violation
│       └── demo.py             # runtime quarantine demo (clean vs quarantined)
├── tests/                      # pytest — local SparkSession fixture
│   ├── conftest.py
│   ├── test_transforms.py
│   └── test_quality.py
├── infra/
│   ├── main.bicep + modules/   # env-parameterized (dev/test/prod)
│   └── terraform/              # same infra, Terraform variant
├── data/orders.csv             # the feed (data-as-code — a bad-data PR fails CI)
├── requirements.txt · pyproject.toml
└── README.md
```

---

## ▶️ Run it locally

```bash
pip install -r requirements.txt
ruff check src tests
pytest -q                                  # PySpark unit tests
python -m src.quality.gate data/orders.csv # the data-quality gate (exit code = pass/fail)
python -m src.quality.demo                 # runtime quarantine split
```

> Requires Python 3.11/3.12 + Java 17 (for Spark). CI runs exactly these steps on every push.

---

## 💸 Cost

**$0.** The entire pipeline — tests, the data-quality gate, the quarantine split, and IaC
validation — runs on **GitHub Actions**. The Bicep/Terraform is proven by **building and
validating** in CI; nothing is deployed to Azure just to prove it works. For a DataOps project the
CI/CD *is* the deliverable.

---

## 🎓 What I learned

- **Test the data, not just the code.** Schema-valid garbage is the sneakiest bug — a gate that
  runs data expectations in CI turns "someone noticed days later" into "the PR was blocked."
- **Read raw, validate typed.** Parsing the feed as strings keeps bad values *catchable* instead of
  silently coercing them to `null`.
- **Quarantine beats fail-closed.** Isolating bad rows (with reasons) keeps good data flowing while
  making the bad data countable and triageable.
- **One expectation suite, two enforcers.** Sharing the predicates between the CI gate and the
  runtime split guarantees what you test is what you enforce.
- **Keep the badge honest.** CD is `workflow_dispatch` so the repo stays green without cloud
  credentials, while still shipping a faithful dev→test→prod promotion with approvals.

---

## 🗺️ Roadmap

- [x] Pure, unit-tested PySpark transforms
- [x] GE-style expectation engine (shared by CI gate + runtime quarantine)
- [x] CI: ruff + pytest + data-quality gate + Bicep/Terraform validate
- [x] CD: dev → test → prod with environment approvals
- [x] Proof: bad-data PR blocked · clean PR green · quarantine split ✅
- [ ] **Next** — data-diff on PRs · a Slack summary of the gate results · Great Expectations / Databricks DQX at scale
