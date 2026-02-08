# QGIS MCP Bridge

A QGIS plugin that runs a local MCP-style server over a Unix domain socket, exposing:
- Structured tools: list layers, list processing algorithms, run processing.
- Sandboxed script runner: execute PyQGIS snippets with stdout/stderr capture (imports guarded, timeout).

## Status
Prototype (0.2.0). Unix socket at `/tmp/qgis-mcp.sock`. Permissions 0600. Optional loopback TCP proxy with token (`QGIS_MCP_TOKEN`).

## Building / Installing
1) Copy the `plugin/` folder to your QGIS profile plugins dir, e.g. `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/qgis_mcp`.
2) Compile resources inside QGIS Python:
```
PYTHONHOME=/Applications/QGIS.app/Contents/Resources \
PYTHONPATH=/Applications/QGIS.app/Contents/Resources/python3.11/site-packages:/Applications/QGIS.app/Contents/Resources/qgis/python \
/Applications/QGIS.app/Contents/MacOS/python -m PyQt5.pyrcc_main plugin/resources.qrc -o plugin/resources_rc.py
```
3) Restart QGIS and enable **QGIS MCP Bridge**. Toggle the toolbar button to start/stop the server.

## Protocol (temporary)
Length-prefixed JSON over the Unix socket.
- `list_tools`: discover supported methods (from `mcp_schema.py`)
- `list_resources`: discover resources
- `list_layers`: returns id/name/type/crs
- `list_algorithms`: returns id/name/provider
- `run_processing`: `{ "algorithm": "native:buffer", "parameters": { ... }, "async": false|true }`
  - async=true returns run_id immediately; poll via `fetch_log` (status/progress)
  - `cancel_run` cancels if still running
- `run_script`: `{ "code": "...", "async": false|true }` → sync returns stdout/stderr/error; async returns run_id
- `fetch_log`: `{ "run_id": "..." }`
- `cancel_run`: `{ "run_id": "..." }`

## Security
- UDS 0600 (local user only). Optional loopback TCP proxy with token.
- Script runner: blocked imports (subprocess, socket, http/urllib/ssl, shutil, pathlib, os), limited builtins, 30s timeout, ~1GB soft memory cap.
- File outputs: allow-list check (defaults `/tmp`; extend with `QGIS_MCP_ALLOW_DIRS=/path1:/path2`).
- Still treat untrusted code as risky; adjust allow-lists and limits as needed.

## Roadmap
- Formal MCP schema responses (JSON-LD) and richer resources.
- Progress/cancel present; improve feedback streaming.
- Windows named-pipe support and hardened FS/CPU/memory quotas.

## Tests
```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt  # pytest
.venv/bin/python -m pytest tests
```

## Client sample
See `client_example.py` for UDS and TCP+token examples calling `list_tools`, `list_layers`, and `run_script`.
