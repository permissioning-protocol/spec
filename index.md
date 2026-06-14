# Permissioning Protocol

**A policy layer for what AI agents are allowed to *do*.**
One machine-readable file, served at `/.well-known/agent-permissions.json`, that declares which actions an autonomous agent may take against your systems — and leaves an audit trail when it tries.

Think `robots.txt`, but for agent *actions* instead of crawler *reads*.

## The problem

Agents now read, write, pay, deploy, and delete. The only controls most stacks have are (a) whatever credentials the agent holds and (b) prompt-level pleading. OAuth scopes govern *API access*, not *agent behavior*: a token that can reach a CRM can also mass-delete it at 3 a.m., and nothing distinguishes that from a human clicking once. There is no standard way to say "agents may read invoices, may draft but not send mail, must get human approval before payments — and every action must be attributable."

This protocol is that declaration.

## What it does (proof, not promises)

A small reference middleware reads a manifest and enforces it at an API boundary. Real outcomes from the runnable demo:

```
allow             -> HTTP 200
deny              -> HTTP 403
require_approval  -> HTTP 202   (held for human/secondary approval)
```

Every governed request is logged:

```
permissioning_audit {"agent_id": "demo-agent", "action": "write",
  "resource": "localhost/payments/transfer", "effect": "require_approval",
  "rule_id": "payments-human-gate", ...}
```

## Who it's for

- AI tooling builders adding guardrails to agent frameworks.
- API and platform engineers who need agent traffic governed at the boundary.
- Teams experimenting with coding or workflow agents.
- Anyone thinking about agent governance and accountability.

## Try it

- **Run the 5-minute quickstart** (Python 3, no dependencies): `python3 examples/quickstart/demo.py` — see [`examples/quickstart/README.md`](examples/quickstart/README.md).
- **Try the HTTP middleware demo** (200 / 403 / 202 + audit log): [`examples/middleware-demo/README.md`](examples/middleware-demo/README.md).
- **Read the spec**: [`spec/v0.1.md`](spec/v0.1.md).
- **Break it via [Issues](https://github.com/permissioning-protocol/spec/issues)** — substantive criticism welcome.

## Honest status

This is **draft v0.1** with a **reference implementation only** — not a production security boundary.

- It enforces at the check-point: traffic that does not pass through the middleware or guard is not governed by it.
- Manifest `conditions` (time windows, value/volume caps, record-age and identity constraints) are *defined in the schema but not yet evaluated* by the reference implementation — treat them as declared intent.
- The `Agent-Id` and `Agent-Action` headers are self-asserted and unsigned in v0.1: declaring a narrower action can reduce authority but never widen it.

A published declaration has value before enforcement is perfect — it sets intent, liability boundaries, and a target for tooling. Then we make it real, in the open.
