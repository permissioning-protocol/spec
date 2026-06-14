#!/usr/bin/env python3
"""
Permissioning Protocol — MCP-shaped permission shim demo (P013).

Runs every MCP-shaped tools/call payload in sample_calls.jsonl through the shim
(shim.decide), prints a compact PASS/FAIL table against expected effects, and
emits one audit line per decision. Exits 0 only if all decisions match.

stdlib only. Run from the repo root:
    python3 examples/mcp-permission-shim/demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from shim import audit_line, decide, load_manifest, load_tool_map  # noqa: E402

SAMPLES = HERE / "sample_calls.jsonl"

# tool name -> expected effect (the outcomes P013 must demonstrate)
EXPECTED = {
    "crm.read_contacts": "allow",
    "crm.delete_contacts": "deny",
    "payments.transfer": "require_approval",
    "files.delete_all": "deny",  # unmapped -> deny by default
}


def main() -> int:
    manifest = load_manifest()
    tool_map = load_tool_map()

    payloads = [
        json.loads(line)
        for line in SAMPLES.read_text().splitlines()
        if line.strip()
    ]

    header = (
        f"{'#':<3} {'tool':<20} {'action':<8} {'resource':<26} "
        f"{'effect':<16} {'rule_id':<20} result"
    )
    print(header)
    print("-" * len(header))

    audits = []
    all_pass = True
    for i, payload in enumerate(payloads, start=1):
        d = decide(payload, manifest, tool_map)
        audits.append(audit_line(d))
        tool = d["tool"] or "(none)"
        expected = EXPECTED.get(tool)
        ok = (expected is None) or (d["effect"] == expected)
        all_pass = all_pass and ok
        result = "PASS" if ok else f"FAIL(exp {expected})"
        print(
            f"{i:<3} {tool:<20} {str(d['action']):<8} {str(d['resource']):<26} "
            f"{d['effect']:<16} {str(d['rule_id']):<20} {result}"
        )

    print("\n--- audit log ---")
    for line in audits:
        print(line)

    print(f"\n{'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
