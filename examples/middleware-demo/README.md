# Runnable HTTP enforcement demo

This demo runs the **reference `PermissioningMiddleware`** ([`reference/middleware.py`](../../reference/middleware.py)) at a real HTTP boundary so you can watch enforcement decisions happen over the wire:

| effect | HTTP status |
|---|---|
| `allow` | `200` |
| `deny` | `403` |
| `require_approval` | `202` |

The app ([`app.py`](app.py)) is a do-nothing FastAPI backend; the middleware decides whether a request reaches it. The manifest is [`agent-permissions.json`](agent-permissions.json). No enforcement logic is defined in the demo — it imports the shipped reference middleware verbatim.

## 1. Install the middleware dependencies

The HTTP demo (unlike the stdlib quickstart) needs the reference packages:

```bash
pip install -r requirements.txt   # from the repo root: fastapi, httpx, uvicorn, starlette, pytest
```

## 2. Start the server

From this directory (`examples/middleware-demo/`):

```bash
python3 -m uvicorn app:app --port 8000
```

Leave it running. Governed requests print a `permissioning_audit {...}` line to this terminal.

## 3. Send requests (in a second terminal)

Each request carries an `Agent-Id` header — that is what marks it as agent traffic the manifest governs. Requests without `Agent-Id` pass straight through.

```bash
# 1) Allowed read  -> 200  (matches rule "crm-read")
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -H "Agent-Id: demo-agent" \
  http://localhost:8000/crm/contacts

# 2) Denied write  -> 403  (matches explicit rule "crm-write-deny")
curl -s -w "\nHTTP %{http_code}\n" -X POST \
  -H "Agent-Id: demo-agent" \
  http://localhost:8000/crm/contacts

# 3) Requires approval -> 202  (matches rule "payments-human-gate")
curl -s -w "\nHTTP %{http_code}\n" -X POST \
  -H "Agent-Id: demo-agent" \
  http://localhost:8000/payments/transfer

# 4) No Agent-Id -> 200  (middleware passes non-agent traffic through untouched)
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  http://localhost:8000/payments/transfer
```

The denied case matches an explicit `crm-write-deny` rule so the `403` cites a named `rule_id`. Deny-by-default is still in force for everything else: any write the manifest does not explicitly mention falls through to `default.write: deny` (returning `403` with `rule_id: null`).

### Expected output (captured verbatim)

```
HTTP 200

{"error":"forbidden","detail":"agent action denied by permissioning manifest","rule_id":"crm-write-deny","agent_id":"demo-agent","resource":"localhost/crm/contacts","action":"write"}
HTTP 403

{"status":"pending_approval","rule_id":"payments-human-gate","approval_type":"human","timeout_s":3600,"agent_id":"demo-agent","resource":"localhost/payments/transfer","action":"write"}
HTTP 202

HTTP 200
```

## 4. The audit log

Every governed request is logged on the **server terminal** (stdout). The three requests above produce:

```
permissioning_audit {"agent_id": "demo-agent", "principal": null, "action": "read", "resource": "localhost/crm/contacts", "effect": "allow", "rule_id": "crm-read", "timestamp": "...", "task_context": null}
permissioning_audit {"agent_id": "demo-agent", "principal": null, "action": "write", "resource": "localhost/crm/contacts", "effect": "deny", "rule_id": "crm-write-deny", "timestamp": "...", "task_context": null}
permissioning_audit {"agent_id": "demo-agent", "principal": null, "action": "write", "resource": "localhost/payments/transfer", "effect": "require_approval", "rule_id": "payments-human-gate", "timestamp": "...", "task_context": null}
```

Add `-H "Agent-Task-Context: my task"` and `-H "Agent-Principal: alice@example.com"` to any request to see those fields populated in the audit line.

## Honest limits

- This is a **demo**, not a hardened or production service. It enforces at one in-process API boundary (the "API gateway / proxy" row of the spec's enforcement table, §4); traffic that does not pass through this middleware is not governed by it.
- **`conditions` are not evaluated.** The v0.1 reference middleware resolves a rule's `effect` only. Manifest `conditions` (time windows, value/volume caps, record-age and identity constraints) are part of the v0.1 schema but are **not yet enforced** by the reference implementation (see spec §3.2). The demo manifest deliberately omits them.
- The `Agent-Id` and `Agent-Action` headers are self-asserted and unsigned in v0.1 (spec §3.2.1): a fine-grained action declaration narrows authority but can never widen it.
- The audit log here is process stdout, not a tamper-evident sink.

v0.1 fails in known ways; the open issues are part of the honest current state: https://github.com/permissioning-protocol/spec/issues
