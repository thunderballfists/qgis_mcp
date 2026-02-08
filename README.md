# QGIS MCP Bridge

A QGIS plugin that runs an MCP server over a Unix domain socket, exposing:
- Structured tools: list layers, list processing algorithms, run processing.
- Sandboxed script runner: execute PyQGIS snippets with stdout/stderr capture.

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
Messages are length-prefixed JSON over the Unix socket.
- `list_layers`: returns id/name/type/crs
- `list_algorithms`: returns id/name/provider
- `run_processing`: `{ "algorithm": "native:buffer", "parameters": { ... } }`
- `run_script`: `{ "code": "print('hi')" }` → returns run_id, stdout, stderr, error
- `fetch_log`: `{ "run_id": "..." }`

## Security
- UDS 0600 (local user only).
- No network exposure.
- Script runner is minimally sandboxed; do not trust unvetted code. Add allow-lists/blocked imports/timeouts before production use.

## Roadmap
- Real MCP schema (tools/resources), discovery, and client examples.
- Better sandbox (blocked imports, timeouts, path allow-list).
- Progress reporting and cancellation.
- Windows named-pipe support and optional loopback TCP with token auth.
