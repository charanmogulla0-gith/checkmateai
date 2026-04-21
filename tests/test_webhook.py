import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from checkmate.config import settings
from checkmate.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_webhook_rejects_missing_signature(client: TestClient) -> None:
    r = client.post("/webhook", content=b"{}", headers={"X-GitHub-Event": "ping"})
    assert r.status_code == 401


def test_webhook_rejects_bad_signature(client: TestClient) -> None:
    r = client.post(
        "/webhook",
        content=b"{}",
        headers={"X-GitHub-Event": "ping", "X-Hub-Signature-256": "sha256=deadbeef"},
    )
    assert r.status_code == 401


def test_webhook_ignores_non_pr_events(client: TestClient) -> None:
    body = b"{}"
    r = client.post(
        "/webhook",
        content=body,
        headers={"X-GitHub-Event": "ping", "X-Hub-Signature-256": _sign(body)},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"


def test_webhook_ignores_non_interesting_actions(client: TestClient) -> None:
    payload = {"action": "closed", "pull_request": {"number": 1}}
    body = json.dumps(payload).encode()
    r = client.post(
        "/webhook",
        content=body,
        headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": _sign(body)},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"
