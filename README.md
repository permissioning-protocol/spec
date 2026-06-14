# Permissioning Protocol

A `robots.txt` for agent actions.

**[→ Read the spec](spec/v0.1.md)** &nbsp;·&nbsp; **[permissioning.ai](https://permissioning.ai)**

Status: **draft 0.1 — break it via [Issues](https://github.com/permissioning-protocol/spec/issues)**

## Try it in 5 minutes

```bash
python3 examples/quickstart/demo.py
```

The quickstart uses the stdlib filesystem-guard path (`reference/fs_guard.py`) and needs **no installed dependencies** — Python 3 only. `requirements.txt` (FastAPI / httpx / uvicorn / starlette) is only for the HTTP middleware (`reference/middleware.py`) and its tests, not for the quickstart.

See `examples/quickstart/README.md`.

Want to see enforcement over HTTP (200 / 403 / 202 at an API boundary)? See `examples/middleware-demo/README.md`.

## Status & limits

Draft 0.1. The reference code enforces rule `effect`s (`allow` / `deny` / `require_approval` / `rate_limit`) at the check-point. Manifest `conditions` (time windows, value/volume caps, record-age and identity constraints) are part of the v0.1 schema but are **not yet enforced** by the reference implementation — treat them as declared intent. This is a spec + reference draft, not a finished or fully enforced security product. Break it via [Issues](https://github.com/permissioning-protocol/spec/issues).
