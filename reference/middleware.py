"""
Permissioning Protocol v0.1 — Reference Middleware (FastAPI / ASGI)

Loads an agent-permissions manifest, reads the Agent-Id request header,
and enforces allow / deny / require_approval with first-match-wins rules.

Spec: https://permissioning.ai/spec/v0.1
"""

from __future__ import annotations

import fnmatch
import json
import logging
import time
from pathlib import Path
from typing import Optional

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# HTTP method → action class per §3.2
_METHOD_ACTION: dict[str, str] = {
    "GET": "read",
    "HEAD": "read",
    "OPTIONS": "read",
    "POST": "write",
    "PUT": "write",
    "PATCH": "write",
    "DELETE": "delete",
}

# Verbs that are specialisations of "write" for default-resolution purposes
_WRITE_SUBTYPES = {"create", "update", "upsert", "replace"}


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------


def load_manifest(source: str | Path) -> dict:
    """Load a permissioning manifest from a local file path or HTTPS URL."""
    s = str(source)
    if s.startswith("http://") or s.startswith("https://"):
        resp = httpx.get(s, timeout=10)
        resp.raise_for_status()
        return resp.json()
    return json.loads(Path(s).read_text())


# ---------------------------------------------------------------------------
# Request classification
# ---------------------------------------------------------------------------


def classify_action(request: Request) -> str:
    """
    Return the semantic action for this request.

    Prefers the Agent-Action header (e.g. 'create:draft') so agents can
    express fine-grained intent beyond what an HTTP method carries.
    Falls back to HTTP-method mapping.
    """
    explicit = request.headers.get("Agent-Action", "").strip().lower()
    if explicit:
        return explicit
    return _METHOD_ACTION.get(request.method.upper(), "execute")


def resource_from_request(request: Request) -> str:
    """Build 'host/path' resource string used for rule matching."""
    host = (request.headers.get("host") or request.url.hostname or "").split(":")[0]
    path = request.url.path.rstrip("/") or "/"
    return f"{host}{path}"


# ---------------------------------------------------------------------------
# Rule matching (first-match-wins)
# ---------------------------------------------------------------------------


def _action_matches(rule_actions: list[str], request_action: str) -> bool:
    """
    True when the request action satisfies at least one rule action.

    Matching hierarchy (most specific first):
      exact:        rule='create:draft'  req='create:draft'  → match
      action class: rule='create'        req='create:draft'  → match
      parent class: rule='write'         req='create:draft'  → match
                    (create / update / upsert / replace ⊂ write)
    """
    action_class = request_action.split(":")[0]
    parent = "write" if action_class in _WRITE_SUBTYPES else None

    for ra in rule_actions:
        if ra == request_action or ra == action_class:
            return True
        if parent and ra == parent:
            return True
    return False


def find_rule(manifest: dict, resource: str, action: str) -> Optional[dict]:
    """Return the first matching rule, or None."""
    for rule in manifest.get("rules", []):
        if fnmatch.fnmatch(resource, rule.get("resource", "")) and _action_matches(
            rule.get("actions", []), action
        ):
            return rule
    return None


def resolve_effect(manifest: dict, resource: str, action: str) -> tuple[str, Optional[dict]]:
    """Return (effect, matched_rule | None)."""
    rule = find_rule(manifest, resource, action)
    if rule:
        return rule["effect"], rule

    action_class = action.split(":")[0]
    lookup_class = "write" if action_class in _WRITE_SUBTYPES else action_class
    defaults = manifest.get("default", {})
    effect = defaults.get(lookup_class) or defaults.get(action_class, "deny")
    return effect, None


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


def _audit(
    manifest: dict,
    request: Request,
    agent_id: str,
    action: str,
    resource: str,
    effect: str,
    rule: Optional[dict],
) -> None:
    if not manifest.get("audit", {}).get("required"):
        return
    entry = {
        "agent_id": agent_id,
        "principal": request.headers.get("Agent-Principal"),
        "action": action,
        "resource": resource,
        "effect": effect,
        "rule_id": rule.get("id") if rule else None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task_context": request.headers.get("Agent-Task-Context"),
    }
    logger.info("permissioning_audit %s", json.dumps(entry))


# ---------------------------------------------------------------------------
# ASGI middleware
# ---------------------------------------------------------------------------


class PermissioningMiddleware(BaseHTTPMiddleware):
    """
    Enforce Permissioning Protocol v0.1 for FastAPI / Starlette apps.

    Requests without an Agent-Id header are passed through untouched —
    the protocol governs agent traffic only.

    Effects:
      allow            request continues normally
      deny             403 Forbidden
      require_approval 202 Accepted; agent must await out-of-band approval
      rate_limit       429 Too Many Requests

    Usage::

        from fastapi import FastAPI
        from middleware import PermissioningMiddleware, load_manifest

        app = FastAPI()
        app.add_middleware(
            PermissioningMiddleware,
            manifest=load_manifest(".well-known/agent-permissions.json"),
        )
    """

    def __init__(self, app: ASGIApp, *, manifest: dict) -> None:
        super().__init__(app)
        self.manifest = manifest

    async def dispatch(self, request: Request, call_next):
        agent_id = request.headers.get("Agent-Id")
        if not agent_id:
            return await call_next(request)

        resource = resource_from_request(request)
        action = classify_action(request)
        effect, rule = resolve_effect(self.manifest, resource, action)

        _audit(self.manifest, request, agent_id, action, resource, effect, rule)

        if effect == "allow":
            return await call_next(request)

        if effect == "deny":
            return JSONResponse(
                status_code=403,
                content={
                    "error": "forbidden",
                    "detail": "agent action denied by permissioning manifest",
                    "rule_id": rule["id"] if rule else None,
                    "agent_id": agent_id,
                    "resource": resource,
                    "action": action,
                },
            )

        if effect == "require_approval":
            approval_cfg = (rule or {}).get("approval", {})
            return JSONResponse(
                status_code=202,
                content={
                    "status": "pending_approval",
                    "rule_id": rule["id"] if rule else None,
                    "approval_type": approval_cfg.get("type"),
                    "timeout_s": approval_cfg.get("timeout_s"),
                    "agent_id": agent_id,
                    "resource": resource,
                    "action": action,
                },
            )

        if effect == "rate_limit":
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limited",
                    "rule_id": rule["id"] if rule else None,
                    "agent_id": agent_id,
                },
            )

        logger.warning("permissioning: unknown effect=%r for agent=%r; denying", effect, agent_id)
        return JSONResponse(
            status_code=403,
            content={"error": "forbidden", "detail": f"unrecognised effect: {effect!r}"},
        )
