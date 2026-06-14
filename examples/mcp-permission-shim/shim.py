#!/usr/bin/env python3
"""
Permissioning Protocol — MCP-shaped permission enforcement shim (P013).

Accepts an MCP-shaped JSON-RPC `tools/call` payload, maps the tool name to a
semantic (action, resource) pair via tool_map.json, resolves it against an
agent-permissions.json manifest with first-match-wins / deny-by-default
semantics, and returns a structured decision plus an audit record.

This is an MCP-SHAPED demo shim. It is NOT a full MCP server, gateway, or
compliance layer: it only consumes a `tools/call`-shaped object. It does not
implement MCP initialization, capability negotiation, transports, or the full
method set. It evaluates rule effects only (no `conditions`), and performs no
identity/auth/crypto. The top-level `agent_id` field is a demo convention.

Reuses the resolution CONCEPT from reference/fs_guard.py (first-match-wins,
deny-by-default, glob resource match, action-class match) rather than importing
it, so the audit record can carry MCP-specific fields (tool, reason).

stdlib only.

Run a single payload from stdin:
    echo '{"jsonrpc":"2.0","id":"x","method":"tools/call",
           "params":{"name":"payments.transfer","arguments":{}},
           "agent_id":"demo-agent"}' | python3 shim.py
"""

from __future__ import annotations

import fnmatch
import json
import sys
import time
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
MANIFEST_PATH = HERE / "agent-permissions.json"
TOOL_MAP_PATH = HERE / "tool_map.json"


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def load_manifest(path: str | Path = MANIFEST_PATH) -> dict:
    return load_json(path)


def load_tool_map(path: str | Path = TOOL_MAP_PATH) -> dict:
    raw = load_json(path)
    # Keep only object entries (skip the leading "_comment" string).
    return {k: v for k, v in raw.items() if isinstance(v, dict)}


def map_tool(tool_name: str, tool_map: dict) -> Optional[tuple[str, str]]:
    """Return (action, resource) for a tool name, or None if unmapped."""
    entry = tool_map.get(tool_name)
    if not entry:
        return None
    return entry.get("action", "execute"), entry.get("resource", "")


def _action_matches(rule_actions: list[str], action: str) -> bool:
    action_class = action.split(":")[0]
    return any(ra == action or ra == action_class for ra in rule_actions)


def resolve(manifest: dict, action: str, resource: str) -> tuple[str, Optional[str]]:
    """First-match-wins resolution; falls back to per-action-class default."""
    for rule in manifest.get("rules", []):
        if fnmatch.fnmatch(resource, rule.get("resource", "")) and _action_matches(
            rule.get("actions", []), action
        ):
            return rule["effect"], rule.get("id")
    defaults = manifest.get("default", {})
    return defaults.get(action.split(":")[0], "deny"), None


def decide(payload: dict, manifest: dict, tool_map: dict) -> dict:
    """Map an MCP-shaped tools/call payload to a structured permission decision."""
    call_id = payload.get("id")
    agent_id = payload.get("agent_id") or "unknown-agent"
    method = payload.get("method")
    params = payload.get("params") or {}
    tool = params.get("name")
    arguments = params.get("arguments") or {}

    base = {
        "id": call_id,
        "agent_id": agent_id,
        "tool": tool,
        "arguments": arguments,
        "action": None,
        "resource": None,
        "effect": "deny",
        "rule_id": None,
        "reason": "",
    }

    if method != "tools/call":
        base["reason"] = f"unsupported method {method!r}; shim only handles 'tools/call' -> deny"
        return base

    if not tool:
        base["reason"] = "missing params.name (tool name) -> deny"
        return base

    mapped = map_tool(tool, tool_map)
    if mapped is None:
        base["action"] = "execute"
        base["resource"] = f"mcp://unknown/{tool}"
        base["effect"] = "deny"
        base["rule_id"] = None
        base["reason"] = f"tool {tool!r} not in tool_map -> deny by default"
        return base

    action, resource = mapped
    effect, rule_id = resolve(manifest, action, resource)
    base["action"] = action
    base["resource"] = resource
    base["effect"] = effect
    base["rule_id"] = rule_id
    if rule_id:
        base["reason"] = f"matched rule {rule_id!r} ({effect})"
    else:
        base["reason"] = f"no rule matched; default {effect} for action {action!r}"
    return base


def audit_record(decision: dict) -> dict:
    """Build the audit record (the fields a decision must log)."""
    return {
        "agent_id": decision["agent_id"],
        "tool": decision["tool"],
        "action": decision["action"],
        "resource": decision["resource"],
        "effect": decision["effect"],
        "rule_id": decision["rule_id"],
        "reason": decision["reason"],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "task_context": None,
    }


def audit_line(decision: dict) -> str:
    return "permissioning_mcp_audit " + json.dumps(audit_record(decision))


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        print("error: no JSON payload on stdin", file=sys.stderr)
        return 2
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON payload: {exc}", file=sys.stderr)
        return 2

    manifest = load_manifest()
    tool_map = load_tool_map()
    decision = decide(payload, manifest, tool_map)

    print(json.dumps({k: v for k, v in decision.items() if k != "arguments"}, indent=2))
    print(audit_line(decision), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
