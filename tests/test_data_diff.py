from src.quality.data_diff import amount_total, dist, null_count, report

BASE = [
    {"order_id": "O-1", "customer_id": "C-1", "status": "placed", "currency": "USD",
     "quantity": "1", "unit_price": "10", "amount": "10"},
    {"order_id": "O-2", "customer_id": "C-2", "status": "shipped", "currency": "USD",
     "quantity": "1", "unit_price": "20", "amount": "20"},
]
CURR = BASE + [
    {"order_id": "O-3", "customer_id": "", "status": "teleported", "currency": "BTC",
     "quantity": "1", "unit_price": "10", "amount": "10"},
]


def test_dist_counts_status():
    d = dist(CURR, "status")
    assert d["placed"] == 1
    assert d["teleported"] == 1


def test_null_count_flags_empty_customer():
    assert null_count(BASE, "customer_id") == 0
    assert null_count(CURR, "customer_id") == 1


def test_amount_total():
    assert amount_total(BASE) == 30.0
    assert amount_total(CURR) == 40.0


def test_report_flags_new_values_and_row_delta():
    r = report(BASE, CURR, "data/orders.csv")
    assert "2 → 3" in r  # row-count delta
    assert "teleported" in r  # new status surfaced
    assert "BTC" in r  # new currency surfaced
    assert "new" in r  # new-value tag present
