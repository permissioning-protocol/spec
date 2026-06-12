"""
Permissioning Protocol v0.1 — Filesystem Guard (reference)

Enforces a permissioning manifest whose resources are filesystem globs —
a v0.1 extension under discussion (spec §6, open question 3). Governs a
coding agent's file operations: every check(), allow or deny, is appended
to a JSON-lines audit log.

Stdlib only. Spec: https://permissioning.ai/spec/v0.1
"""

from __future__ import annotations

import fnmatch
import json
import time
from pathlib import Path
from typing import Optional


def load_manifest(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def _path_matches(pattern: str, path: str) -> bool:
    """
    Glob match for filesystem resources.

    fnmatch alone fails patterns like '**/.env' against a root-level
    '.env' (the '**/' demands a separator), so the path is also tried
    with a './' prefix, making '**/x' mean 'x at any depth, root included'.
    """
    norm = path.replace("\\", "/").lstrip("/")
    if norm.startswith("./"):
        norm = norm[2:]
    return fnmatch.fnmatch(norm, pattern) or fnmatch.fnmatch("./" + norm, pattern)


def _action_matches(rule_actions: list[str], action: str) -> bool:
    action_class = action.split(":")[0]
    return any(ra == action or ra == action_class for ra in rule_actions)


class FsGuard:
    """
    Usage::

        guard = FsGuard("examples/coding-agent.permissions.json", "audit.jsonl")
        decision = guard.check("write", "src/app.py",
                               agent_id="claude-code", task_context="fix bug #12")
        if decision["effect"] != "allow":
            ...  # refuse, or await approval
    """

    def __init__(self, manifest_path: str | Path, audit_log_path: str | Path) -> None:
        self.manifest = load_manifest(manifest_path)
        self.audit_log_path = Path(audit_log_path)

    def check(self, action: str, path: str, agent_id: str, task_context: str) -> dict:
        """Return {effect, rule_id, audit_record}; logs every decision."""
        effect, rule = self._resolve(action, path)
        record = {
            "agent_id": agent_id,
            "action": action,
            "resource": path,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "task_context": task_context,
            "effect": effect,
            "rule_id": rule.get("id") if rule else None,
        }
        with self.audit_log_path.open("a") as f:
            f.write(json.dumps(record) + "\n")
        return {"effect": effect, "rule_id": record["rule_id"], "audit_record": record}

    def _resolve(self, action: str, path: str) -> tuple[str, Optional[dict]]:
        for rule in self.manifest.get("rules", []):
            if _path_matches(rule.get("resource", ""), path) and _action_matches(
                rule.get("actions", []), action
            ):
                return rule["effect"], rule
        defaults = self.manifest.get("default", {})
        return defaults.get(action.split(":")[0], "deny"), None


if __name__ == "__main__":
    import tempfile

    manifest = Path(__file__).parent.parent / "examples" / "coding-agent.permissions.json"
    audit_log = Path(tempfile.mkdtemp()) / "audit.jsonl"
    guard = FsGuard(manifest, audit_log)

    AGENT = "claude-code/fable-5"
    TASK = "PP-002: dogfood manifests + first enforced coding-agent session"

    session = [
        ("read", "src/app.py"),
        ("read", ".env"),
        ("write", "src/app.py"),
        ("write", "spec/v0.1.md"),
        ("delete", "tests/old.py"),
    ]

    for action, path in session:
        d = guard.check(action, path, agent_id=AGENT, task_context=TASK)
        print(f"{action:<7} {path:<22} -> {d['effect']:<16} (rule: {d['rule_id']})")

    print("\n--- audit log ---")
    print(audit_log.read_text(), end="")
