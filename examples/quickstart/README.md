# Permissioning quickstart

Run the Permissioning quickstart in one command and see allow / deny / require_approval decisions.

```bash
git clone https://github.com/permissioning-protocol/spec.git
cd spec
python3 examples/quickstart/demo.py
```

**No dependencies required.** The quickstart runs the stdlib-only filesystem guard (`reference/fs_guard.py`) — Python 3 is the only requirement. You do **not** need to `pip install` anything. The packages in `requirements.txt` (FastAPI / httpx / uvicorn / starlette) are only for the HTTP middleware (`reference/middleware.py`) and its test suite, not for this quickstart.

## What you just saw

The demo loads a small filesystem-glob manifest (`agent-permissions.json`) and runs five labelled checks through the reference `fs_guard`. Each check is a check-point authorization decision — `allow`, `deny`, or `require_approval` — and every decision is appended to an audit log that the demo prints at the end. The five checks are:

| action | resource | effect |
|---|---|---|
| read | `docs/notes.md` | allow |
| read | `.env` | deny |
| write | `src/app.py` | allow |
| write | `config/prod.yaml` | deny |
| delete | `src/old.py` | require_approval |

The script exits `0` only if all five decisions match what the manifest says they should be.

## Honest limits

This is experimental v0.1. It enforces at the check-point — an agent whose operations are not routed through the guard is not constrained by it — and the filesystem-glob resource form is a v0.1 extension, not part of the base spec.

v0.1 fails in known ways; the open issues are part of the honest current state.

See: https://github.com/permissioning-protocol/spec/issues
