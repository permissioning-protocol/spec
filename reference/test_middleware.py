"""
Tests for the Permissioning Protocol reference middleware.

Run:  pytest reference/test_middleware.py -v
"""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware import PermissioningMiddleware, load_manifest

MANIFEST = load_manifest(
    Path(__file__).parent.parent / "examples" / "agent-permissions.example.json"
)

AGENT = {"Agent-Id": "test-agent-001"}
HOST = {"host": "api.example.com"}


@pytest.fixture(scope="module")
def client():
    app = FastAPI()

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def catch_all(full_path: str):
        return {"ok": True}

    app.add_middleware(PermissioningMiddleware, manifest=MANIFEST)
    return TestClient(app, raise_server_exceptions=True)


def test_crm_read_allowed(client):
    """GET /crm/* with Agent-Id is allowed by the crm-read rule."""
    r = client.get("/crm/contacts", headers={**AGENT, **HOST})
    assert r.status_code == 200


def test_crm_write_denied(client):
    """POST /crm/* is denied — no write rule for CRM, default write=deny."""
    r = client.post("/crm/contacts", headers={**AGENT, **HOST})
    assert r.status_code == 403
    assert r.json()["error"] == "forbidden"


def test_email_draft_allowed(client):
    """POST /mail/* with Agent-Action: create:draft matches email-draft-only."""
    r = client.post(
        "/mail/drafts",
        headers={**AGENT, **HOST, "Agent-Action": "create:draft"},
    )
    assert r.status_code == 200


def test_payments_require_approval(client):
    """POST /payments/* returns 202 pending_approval per payments-human-gate."""
    r = client.post("/payments/transfer", headers={**AGENT, **HOST})
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "pending_approval"
    assert body["rule_id"] == "payments-human-gate"
    assert body["approval_type"] == "human"
    assert body["timeout_s"] == 3600


def test_non_agent_passthrough(client):
    """Requests without Agent-Id bypass the middleware entirely."""
    r = client.post("/payments/transfer", headers={**HOST})
    assert r.status_code == 200


def test_default_read_allowed(client):
    """GET to an unlisted resource uses default read: allow."""
    r = client.get("/reports/quarterly", headers={**AGENT, **HOST})
    assert r.status_code == 200


def test_default_write_denied(client):
    """PUT to an unlisted resource uses default write: deny."""
    r = client.put("/config/settings", headers={**AGENT, **HOST})
    assert r.status_code == 403
