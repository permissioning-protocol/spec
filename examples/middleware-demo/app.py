#!/usr/bin/env python3
"""
Permissioning Protocol v0.1 — runnable HTTP enforcement demo (P010).

A minimal FastAPI app that mounts the reference PermissioningMiddleware at an
API boundary and lets you see real enforcement outcomes over HTTP:

    allow            -> 200
    deny             -> 403
    require_approval -> 202

Every governed request (one carrying an `Agent-Id` header) prints a
`permissioning_audit {...}` line to this server's stdout.

This reuses `reference/middleware.py` verbatim — no enforcement logic is
defined here. It is a demo, not a hardened or production service. The v0.1
reference middleware enforces rule effects only; manifest `conditions` are
NOT evaluated (see README and spec §3.2).

Run from this directory:

    python3 -m uvicorn app:app --port 8000

Spec: https://permissioning.ai/spec/v0.1
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Put the canonical reference implementation on the import path so this demo
# uses the same middleware the spec ships, not a copy.
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "reference"))

from fastapi import FastAPI  # noqa: E402  (path set up above)

from middleware import PermissioningMiddleware, load_manifest  # noqa: E402

# Surface the middleware's audit log on stdout so the demo's audit lines show.
logging.basicConfig(level=logging.INFO, format="%(message)s")

MANIFEST = load_manifest(HERE / "agent-permissions.json")

app = FastAPI(title="Permissioning Protocol — middleware demo")


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def catch_all(full_path: str) -> dict:
    """A do-nothing backend; the middleware decides whether we even get here."""
    return {"ok": True, "path": f"/{full_path}"}


# Mount enforcement at the boundary. Requests without an Agent-Id pass through.
app.add_middleware(PermissioningMiddleware, manifest=MANIFEST)
