# MCP-shaped permission enforcement shim (demo)

This demo proves one thing: **Permissioning Protocol can gate MCP-shaped tool calls.** It takes JSON-RPC `tools/call`-shaped payloads, maps each tool name to a semantic `(action, resource)` pair, resolves that against an owner-published `agent-permissions.json` (first-match-wins, deny-by-default), and emits a per-decision audit line.

It shows the four outcomes that matter:

| tool call | maps to | effect |
|---|---|---|
| `crm.read_contacts` | `read` / `mcp://crm/contacts` | `allow` |
| `crm.delete_contacts` | `delete` / `mcp://crm/contacts` | `deny` (rule `crm-delete-deny`) |
| `payments.transfer` | `write` / `mcp://payments/transfer` | `require_approval` (rule `payments-human-gate`) |
| `files.delete_all` (unmapped) | `execute` / `mcp://unknown/...` | `deny` by default |

## Run it

From the repo root (Python 3, no dependencies):

```bash
python3 examples/mcp-permission-shim/demo.py
```

Single-payload mode (reads one JSON object from stdin; decision on stdout, audit line on stderr):

```bash
echo '{"jsonrpc":"2.0","id":"x","method":"tools/call","params":{"name":"payments.transfer","arguments":{"amount":500}},"agent_id":"demo-agent"}' \
  | python3 examples/mcp-permission-shim/shim.py
```

## Input shape

```json
{
  "jsonrpc": "2.0",
  "id": "demo-1",
  "method": "tools/call",
  "params": {
    "name": "crm.read_contacts",
    "arguments": { "account_id": "demo" }
  },
  "agent_id": "demo-agent"
}
```

The shim validates `method == "tools/call"`, reads `params.name` as the tool, and uses the top-level `agent_id` for attribution. Tool names are mapped to `(action, resource)` by [`tool_map.json`](tool_map.json); policy lives in [`agent-permissions.json`](agent-permissions.json).

## Expected output (captured verbatim)

```
#   tool                 action   resource                   effect           rule_id              result
---------------------------------------------------------------------------------------------------------
1   crm.read_contacts    read     mcp://crm/contacts         allow            crm-contacts-read    PASS
2   crm.delete_contacts  delete   mcp://crm/contacts         deny             crm-delete-deny      PASS
3   payments.transfer    write    mcp://payments/transfer    require_approval payments-human-gate  PASS
4   files.delete_all     execute  mcp://unknown/files.delete_all deny             None                 PASS

--- audit log ---
permissioning_mcp_audit {"agent_id": "demo-agent", "tool": "crm.read_contacts", "action": "read", "resource": "mcp://crm/contacts", "effect": "allow", "rule_id": "crm-contacts-read", "reason": "matched rule 'crm-contacts-read' (allow)", "timestamp": "...", "task_context": null}
permissioning_mcp_audit {"agent_id": "demo-agent", "tool": "crm.delete_contacts", "action": "delete", "resource": "mcp://crm/contacts", "effect": "deny", "rule_id": "crm-delete-deny", "reason": "matched rule 'crm-delete-deny' (deny)", "timestamp": "...", "task_context": null}
permissioning_mcp_audit {"agent_id": "demo-agent", "tool": "payments.transfer", "action": "write", "resource": "mcp://payments/transfer", "effect": "require_approval", "rule_id": "payments-human-gate", "reason": "matched rule 'payments-human-gate' (require_approval)", "timestamp": "...", "task_context": null}
permissioning_mcp_audit {"agent_id": "demo-agent", "tool": "files.delete_all", "action": "execute", "resource": "mcp://unknown/files.delete_all", "effect": "deny", "rule_id": null, "reason": "tool 'files.delete_all' not in tool_map -> deny by default", "timestamp": "...", "task_context": null}

ALL CHECKS PASSED
```

Every audit line carries `agent_id`, `tool`, `action`, `resource`, `effect`, `rule_id`, and `reason`. The `deny` and `require_approval` cases cite named rules.

## Why this is MCP-shaped, not MCP-compliant

The shim only *consumes* a `tools/call`-shaped JSON object. It does **not** implement the MCP protocol: there is no initialization handshake, no capability negotiation, no transport (stdio/HTTP/SSE), no session management, and not the full method set. Calling it "MCP-compliant" would be inaccurate, so we call it MCP-*shaped*: it speaks just enough of the `tools/call` shape to demonstrate where a permission declaration would sit relative to MCP.

## Honest limits

- **Not a full MCP server** or gateway — see above.
- **Not a production security boundary.** It governs at the decision point: a tool call that is not routed through this shim is not gated by it.
- **No `conditions` evaluation.** The manifest schema can express conditions (time windows, value/volume caps, etc.), but this demo resolves rule *effects* only. Arguments in `params.arguments` are recorded for context but never used to decide.
- **No identity, auth, or crypto.** The top-level `agent_id` is a demo convention for attribution; it is self-asserted and unverified. Base MCP does not define it.
- **Mapping is a demo convenience.** `tool_map.json` is a small static map, not a standardized tool-name-to-action ontology.

This demo reuses the resolution concept from the reference guard (`reference/fs_guard.py`): first-match-wins, deny-by-default, glob resource matching, and action-class matching. v0.1 fails in known ways; the open issues are part of the honest current state: https://github.com/permissioning-protocol/spec/issues
