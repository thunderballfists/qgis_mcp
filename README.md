# QGIS MCP Bridge

A QGIS plugin that runs a local MCP-style server over a Unix domain socket, exposing:
- Structured tools: list layers, list processing algorithms, run processing.
- Sandboxed script runner: execute PyQGIS snippets with stdout/stderr capture (imports guarded, timeout).

## Status
Prototype (0.1.0). Unix socket at `/tmp/qgis-mcp.sock`. Permissions 0600. No auth beyond local user.

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
- `list_tools`: discover supported methods
- `list_layers`: returns id/name/type/crs
- `list_algorithms`: returns id/name/provider
- `run_processing`: `{ "algorithm": "native:buffer", "parameters": { ... } }`
- `run_script`: `{ "code": "print('hi')" }` → returns run_id, stdout, stderr, error (timeout 30s, blocked imports: subprocess/socket/http/urllib/ssl/shutil/pathlib/os)
- `fetch_log`: `{ "run_id": "..." }`

## Security
- UDS 0600 (local user only).
- No network exposure by default.
- Script runner: blocked imports (subprocess, socket, http/urllib/ssl, shutil, pathlib, os), limited builtins, 30s timeout. Still consider untrusted code risky—extend allow-lists and FS guards for production.
- File outputs: simple allow-list check on parameters; defaults to `/tmp` plus optional env `QGIS_MCP_ALLOW_DIRS=/path1:/path2`.

## Roadmap
- Real MCP schema (tools/resources), discovery, and client examples.
- Better sandbox (blocked imports, timeouts, path allow-list).
- Progress reporting and cancellation.
- Windows named-pipe support and optional loopback TCP with token auth.

## Tests
```
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt  # pytest
.venv/bin/python -m pytest tests
```

## Client sample
See `client_example.py` for a minimal Unix-socket client that calls `list_tools`, `list_layers`, and `run_script`.
