from src.quality.slack import notify


def test_notify_skips_without_webhook(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    assert notify("hello") is False


def test_notify_rejects_non_slack_url(monkeypatch):
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    # a non-Slack host must be refused (SSRF guard), even if passed explicitly
    assert notify("hello", webhook="https://evil.example.com/hook") is False
