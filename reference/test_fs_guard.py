"""
Tests for the filesystem guard against examples/coding-agent.permissions.json.

Run:  pytest reference/test_fs_guard.py -v
"""
import json
from pathlib import Path

import pytest

from fs_guard import FsGuard

MANIFEST = Path(__file__).parent.parent / "examples" / "coding-agent.permissions.json"


@pytest.fixture()
def guard(tmp_path):
    return FsGuard(MANIFEST, tmp_path / "audit.jsonl")


def _check(guard, action, path):
    return guard.check(action, path, agent_id="test-agent", task_context="unit test")


def test_env_read_denied(guard):
    """Reading .env is denied at any depth, including repo root."""
    assert _check(guard, "read", ".env")["effect"] == "deny"
    assert _check(guard, "read", "backend/.env")["rule_id"] == "deny-read-env"


def test_src_write_allowed(guard):
    """Writes inside src/ match allow-write-src."""
    d = _check(guard, "write", "src/app.py")
    assert d["effect"] == "allow"
    assert d["rule_id"] == "allow-write-src"


def test_out_of_scope_write_denied(guard):
    """A write outside src/tests/docs/README.md falls to default write: deny."""
    d = _check(guard, "write", "spec/v0.1.md")
    assert d["effect"] == "deny"
    assert d["rule_id"] is None


def test_delete_requires_approval(guard):
    """Any delete hits the human gate."""
    d = _check(guard, "delete", "tests/old.py")
    assert d["effect"] == "require_approval"
    assert d["rule_id"] == "delete-human-gate"


def test_default_fallback(guard):
    """Unmatched read allowed by default; execute denied by default."""
    assert _check(guard, "read", "Makefile")["effect"] == "allow"
    assert _check(guard, "execute", "scripts/deploy.sh")["effect"] == "deny"


def test_audit_log_written_for_allow_and_deny(guard):
    """Both allowed and denied decisions land in the audit log with context."""
    _check(guard, "read", "Makefile")
    _check(guard, "read", ".env")
    lines = [json.loads(l) for l in guard.audit_log_path.read_text().splitlines()]
    assert [e["effect"] for e in lines] == ["allow", "deny"]
    assert all(e["task_context"] == "unit test" for e in lines)
    assert all(e["agent_id"] == "test-agent" for e in lines)
