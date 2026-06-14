# Case Study 001 — First Enforced Coding-Agent Session

*2026-06-12 · Permissioning Protocol v0.1*

## Problem

For a year, the author's coding agents have operated under prose rules embedded in task packets: "do not read `.env`", "allowed edits: only these files", "deletions need sign-off." Those rules were enforced by nothing but agent attention — a well-behaved model follows them, a confused or misaligned one silently doesn't, and there is no record either way. The rules were policy in intent but not in mechanism.

## What changed

The same rules now exist as a v0.1 permissioning manifest and are checked mechanically. Every file operation passes through a guard that resolves it against first-match-wins rules and writes the decision — allow *and* deny — to an append-only audit log. The agent's stated task travels with every entry.

## The manifest

[`examples/coding-agent.permissions.json`](../examples/coding-agent.permissions.json) — deny-read on secrets (`**/.env`, `**/secrets/**`, `**/*.pem`, `.git` objects, dependency dirs), write allowed only in `src/**`, `tests/**`, `docs/**`, `README.md`, every delete gated behind human approval, defaults `read: allow / write: deny / execute: deny`.

Enforcement: [`reference/fs_guard.py`](../reference/fs_guard.py) (~120 lines, stdlib-only). Tests: [`reference/test_fs_guard.py`](../reference/test_fs_guard.py).

## The audit log

Output of `python3 reference/fs_guard.py`, captured verbatim:

```
read    src/app.py             -> allow            (rule: None)
read    .env                   -> deny             (rule: deny-read-env)
write   src/app.py             -> allow            (rule: allow-write-src)
write   spec/v0.1.md           -> deny             (rule: None)
delete  tests/old.py           -> require_approval (rule: delete-human-gate)

--- audit log ---
{"agent_id": "claude-code/fable-5", "action": "read", "resource": "src/app.py", "timestamp": "2026-06-12T12:04:09Z", "task_context": "PP-002: dogfood manifests + first enforced coding-agent session", "effect": "allow", "rule_id": null}
{"agent_id": "claude-code/fable-5", "action": "read", "resource": ".env", "timestamp": "2026-06-12T12:04:09Z", "task_context": "PP-002: dogfood manifests + first enforced coding-agent session", "effect": "deny", "rule_id": "deny-read-env"}
{"agent_id": "claude-code/fable-5", "action": "write", "resource": "src/app.py", "timestamp": "2026-06-12T12:04:09Z", "task_context": "PP-002: dogfood manifests + first enforced coding-agent session", "effect": "allow", "rule_id": "allow-write-src"}
{"agent_id": "claude-code/fable-5", "action": "write", "resource": "spec/v0.1.md", "timestamp": "2026-06-12T12:04:09Z", "task_context": "PP-002: dogfood manifests + first enforced coding-agent session", "effect": "deny", "rule_id": null}
{"agent_id": "claude-code/fable-5", "action": "delete", "resource": "tests/old.py", "timestamp": "2026-06-12T12:04:09Z", "task_context": "PP-002: dogfood manifests + first enforced coding-agent session", "effect": "require_approval", "rule_id": "delete-human-gate"}
```

The denied `.env` read is the line that matters: a rule that lived in prose for a year produced its first mechanical denial, attributed and timestamped.

## Honest limits

- This guards at the **check-point**, not the OS layer. An agent whose file operations are not routed through `FsGuard.check()` is not constrained by it. It is the "agent runtime" row of the spec's enforcement table (§4) — the weakest layer, still useful for liability and logging.
- Filesystem globs as `resource` values are a **v0.1 extension under discussion**, not part of the base spec — see [open question 3](https://github.com/permissioning-protocol/spec/issues) (manifest discovery and resource naming for non-web systems).
- The audit log is local and append-only by convention, not tamper-evident.

---

At least two deployments of this protocol are documented publicly (this site's own `.well-known` manifest and the coding-agent manifest above). Additional local dogfood deployments exist but are not yet published as public case studies. Every documented deployment governs the author.
