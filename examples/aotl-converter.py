#!/usr/bin/env python3
# Example: converting an existing tool's permission config into a protocol manifest.
# Reads an AOTL-style project_manifest.json and emits a v0.1 agent-permissions.json.
# The AOTL sample below is fictional — no real paths or content from any private repo.
# Run: python3 examples/aotl-converter.py | python3 -m json.tool
"""
Maps two AOTL concepts onto the Permissioning Protocol:
  protected_paths        -> deny rules for read + write
  agent_policy.approvals -> require_approval rules

Sample AOTL project_manifest.json (fictional, inlined for a self-contained demo):

{
  "project": "demo-service",
  "protected_paths": ["config/prod/**", "**/*.key"],
  "agent_policy": {
    "approvals": [
      { "path": "infra/**", "actions": ["write", "execute"], "approver": "human", "timeout_s": 1800 },
      { "path": "db/migrations/**", "actions": ["execute"], "approver": "human", "timeout_s": 3600 }
    ]
  }
}
"""

from __future__ import annotations

import json
import re
from datetime import date

SAMPLE_AOTL = {
    "project": "demo-service",
    "protected_paths": ["config/prod/**", "**/*.key"],
    "agent_policy": {
        "approvals": [
            {"path": "infra/**", "actions": ["write", "execute"],
             "approver": "human", "timeout_s": 1800},
            {"path": "db/migrations/**", "actions": ["execute"],
             "approver": "human", "timeout_s": 3600},
        ]
    },
}


def _rule_id(prefix: str, resource: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", resource.lower()).strip("-")
    return f"{prefix}-{slug}" or prefix


def convert(aotl: dict) -> dict:
    rules: list[dict] = []

    # protected_paths -> deny read + write (deny wins via first-match-wins,
    # so these are emitted before any broader allow rules).
    for path in aotl.get("protected_paths", []):
        rules.append({
            "id": _rule_id("protect", path),
            "resource": path,
            "actions": ["read", "write"],
            "effect": "deny",
        })

    # agent_policy.approvals -> require_approval
    for item in aotl.get("agent_policy", {}).get("approvals", []):
        rules.append({
            "id": _rule_id("approve", item["path"]),
            "resource": item["path"],
            "actions": item.get("actions", ["write"]),
            "effect": "require_approval",
            "approval": {
                "type": item.get("approver", "human"),
                "timeout_s": item.get("timeout_s", 3600),
            },
        })

    return {
        "_comment": "Generated from an AOTL project_manifest.json by examples/aotl-converter.py. "
                    "Filesystem globs are a v0.1 extension under discussion (spec §6).",
        "permissioning_version": "0.1",
        "owner": aotl.get("project", "unknown"),
        "updated": date.today().isoformat(),
        "default": {"read": "allow", "write": "deny", "execute": "deny"},
        "rules": rules,
        "audit": {
            "required": True,
            "fields": ["agent_id", "action", "resource", "timestamp", "task_context"],
        },
    }


if __name__ == "__main__":
    print(json.dumps(convert(SAMPLE_AOTL), indent=2))
