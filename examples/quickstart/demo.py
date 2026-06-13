#!/usr/bin/env python3
"""
Permissioning Protocol — five-minute quickstart reproducer (PP-009).

Runs five labelled authorization checks through the canonical reference
guard (reference/fs_guard.py) against a small filesystem-glob manifest,
prints a PASS/FAIL table, and emits the resulting audit log.

stdlib-only. Imports FsGuard from reference/ — no matching logic is
duplicated here. Exits 0 only if all five checks match expectations.

Run from the repo root:  python3 examples/quickstart/demo.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Locate the repo root from this file and put reference/ on the import path,
# so the canonical FsGuard is used rather than any reimplementation.
HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT / "reference"))

from fs_guard import FsGuard  # noqa: E402  (path set up above)

MANIFEST = HERE.parent / "agent-permissions.json"
TASK_CONTEXT = "PP-009 quickstart external reproducer"
AGENT_ID = "quickstart-demo"

# (action, resource, expected effect)
CHECKS = [
    ("read", "docs/notes.md", "allow"),
    ("read", ".env", "deny"),
    ("write", "src/app.py", "allow"),
    ("write", "config/prod.yaml", "deny"),
    ("delete", "src/old.py", "require_approval"),
]


def main() -> int:
    audit_log = Path(tempfile.mkdtemp()) / "audit.jsonl"
    guard = FsGuard(MANIFEST, audit_log)

    header = f"{'#':<3} {'action':<7} {'resource':<18} {'expected':<16} {'actual':<16} result"
    print(header)
    print("-" * len(header))

    all_pass = True
    for i, (action, resource, expected) in enumerate(CHECKS, start=1):
        actual = guard.check(action, resource, agent_id=AGENT_ID,
                             task_context=TASK_CONTEXT)["effect"]
        ok = actual == expected
        all_pass = all_pass and ok
        print(f"{i:<3} {action:<7} {resource:<18} {expected:<16} {actual:<16} "
              f"{'PASS' if ok else 'FAIL'}")

    print("\n--- audit log ---")
    print(audit_log.read_text(), end="")

    print(f"\n{'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
