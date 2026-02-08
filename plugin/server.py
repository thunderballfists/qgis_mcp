import asyncio
import concurrent.futures
import json
import os
import uuid
import resource
from contextlib import asynccontextmanager
from pathlib import Path
from types import MappingProxyType
from threading import Lock

from qgis.core import (
    QgsProject,
    QgsProcessingFeedback,
    QgsProcessingContext,
    QgsApplication,
)
from qgis import processing
try:
    from . import mcp_schema
except ImportError:
    import mcp_schema

# Socket and limits
SOCKET_PATH = Path('/tmp/qgis-mcp.sock')
TCP_PROXY_PORT = 8765
MAX_MESSAGE_SIZE = 5 * 1024 * 1024  # 5 MB
TIMEOUT_SEC = 30
MEMORY_LIMIT_BYTES = 1_000_000_000  # ~1 GB soft cap

# Sandbox settings
BLOCKED_MODULES = {
    'subprocess',
    'socket',
    'http',
    'urllib',
    'ssl',
    'shutil',
    'pathlib',  # disallow arbitrary fs writes; we’ll expose limited paths later
    'os',       # prevent env tampering; we expose nothing here
}

# File-system allow-list (prefixes). Extend via env QGIS_MCP_ALLOW_DIRS=/path1:/path2
ALLOW_PATHS = [
    '/tmp',
]
_extra_allow = os.environ.get('QGIS_MCP_ALLOW_DIRS')
if _extra_allow:
    ALLOW_PATHS.extend([p for p in _extra_allow.split(':') if p])

class McpServer:
    def __init__(self, iface, socket_path=SOCKET_PATH):
        self.iface = iface
        self.socket_path = Path(socket_path)
        self.server = None
        self._runs = {}
        self._lock = Lock()

    async def start(self):
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except Exception:
                pass
        self.server = await asyncio.start_unix_server(self.handle_client, path=self.socket_path.as_posix())
        os.chmod(self.socket_path, 0o600)

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        if self.socket_path.exists():
            try:
                self.socket_path.unlink()
            except Exception:
                pass

    async def handle_client(self, reader, writer):
        try:
            data = await reader.readexactly(4)
        except asyncio.IncompleteReadError:
            writer.close(); await writer.wait_closed(); return
        length = int.from_bytes(data, 'big')
        if length > MAX_MESSAGE_SIZE:
            writer.close(); await writer.wait_closed(); return
        payload = await reader.readexactly(length)
        req = json.loads(payload.decode('utf-8'))
        resp = await self.dispatch(req)
        out = json.dumps(resp).encode('utf-8')
        writer.write(len(out).to_bytes(4, 'big') + out)
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def dispatch(self, req):
        method = req.get('method')
        if method == 'list_tools':
            return {'result': mcp_schema.tools}
        if method == 'list_layers':
            return {'result': self._list_layers()}
        if method == 'list_algorithms':
            return {'result': self._list_algs()}
        if method == 'list_resources':
            return {'result': mcp_schema.resources}
        if method == 'run_processing':
            return await self._run_processing(req.get('params', {}))
        if method == 'run_script':
            return await self._run_script(req.get('params', {}))
        if method == 'fetch_log':
            run_id = req.get('params', {}).get('run_id')
            return {'result': self._runs.get(run_id)}
        if method == 'cancel_run':
            run_id = req.get('params', {}).get('run_id')
            return {'result': self._cancel_run(run_id)}
        return {'error': 'unknown method'}

    def _list_layers(self):
        layers = []
        for lyr in QgsProject.instance().mapLayers().values():
            layers.append({
                'id': lyr.id(),
                'name': lyr.name(),
                'type': lyr.type(),
                'crs': lyr.crs().authid() if hasattr(lyr, 'crs') else None,
            })
        return layers

    def _list_algs(self):
        algs = []
        for alg_id in QgsApplication.processingRegistry().algorithms():
            algs.append({'id': alg_id.id(), 'name': alg_id.displayName(), 'provider': alg_id.provider().id()})
        return algs

    async def _run_processing(self, params):
        alg_id = params.get('algorithm')
        alg_params = params.get('parameters', {})
        asynchronous = params.get('async', False)
        # path allow-list
        for v in alg_params.values():
            if isinstance(v, str) and ('/' in v or v.endswith('.tif') or v.endswith('.gpkg')):
                if not self._path_allowed(v):
                    return {'error': f'Path not allowed: {v}'}

        def job(log):
            ctx = QgsProcessingContext()
            fb = self._feedback_for(log)
            return processing.run(alg_id, alg_params, context=ctx, feedback=fb)

        if not asynchronous:
            try:
                res = await asyncio.get_event_loop().run_in_executor(None, lambda: job({'progress': 0}))
                return {'result': res}
            except Exception as e:
                return {'error': str(e)}

        # async path
        run_id = str(uuid.uuid4())
        log = {'stdout': '', 'stderr': '', 'error': None, 'progress': 0, 'status': 'running', 'kind': 'processing'}
        with self._lock:
            self._runs[run_id] = log

        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(None, lambda: job(log))

        def done_cb(fut):
            with self._lock:
                if fut.cancelled():
                    log['status'] = 'cancelled'
                else:
                    try:
                        res = fut.result()
                        log['result'] = res
                        log['status'] = 'finished'
                    except Exception as e:
                        log['error'] = str(e)
                        log['status'] = 'error'

        future.add_done_callback(done_cb)
        log['future'] = future
        return {'result': {'run_id': run_id, 'status': 'running'}}

    async def _run_script(self, params):
        code = params.get('code', '')
        asynchronous = params.get('async', False)
        run_id = str(uuid.uuid4())
        log = {'stdout': '', 'stderr': '', 'error': None, 'status': 'running', 'kind': 'script'}
        with self._lock:
            self._runs[run_id] = log

        loop = asyncio.get_event_loop()

        async def run_sync():
            try:
                await asyncio.wait_for(loop.run_in_executor(None, self._sandbox_exec, code, log), timeout=TIMEOUT_SEC)
            except asyncio.TimeoutError:
                log['error'] = f'timeout after {TIMEOUT_SEC}s'
                log['status'] = 'timeout'
            else:
                if log['error']:
                    log['status'] = 'error'
                else:
                    log['status'] = 'finished'
            return {'run_id': run_id, **log}

        if not asynchronous:
            res = await run_sync()
            return {'result': res}

        future = loop.run_in_executor(None, lambda: self._sandbox_exec(code, log))
        log['future'] = future
        return {'result': {'run_id': run_id, 'status': 'running'}}

    def _feedback_for(self, log: dict):
        class FB(QgsProcessingFeedback):
            def setProgress(feedback_self, progress):
                log['progress'] = progress
                super().setProgress(progress)
        return FB()

    def _cancel_run(self, run_id):
        if not run_id:
            return {'error': 'missing run_id'}
        with self._lock:
            info = self._runs.get(run_id)
            if not info:
                return {'error': 'run_id not found'}
            fut = info.get('future')
            if fut and not fut.done():
                fut.cancel()
                info['status'] = 'cancelled'
                return {'status': 'cancelled'}
            return {'status': info.get('status', 'finished')}

    def _path_allowed(self, path: str) -> bool:
        try:
            p = Path(path).resolve()
            allowed = [Path(prefix).resolve() for prefix in ALLOW_PATHS]
            return any(str(p).startswith(str(a)) for a in allowed)
        except Exception:
            return False

    def _sandbox_exec(self, code: str, log: dict):
        """
        Execute user code with guardrails:
        - Block dangerous imports
        - Restrict builtins
        - Capture stdout/stderr
        """
        import builtins
        import io
        import contextlib

        # memory limit (soft)
        try:
            resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
        except Exception:
            pass

        # Restrict builtins
        safe_builtins = {
            'print': print,
            'range': range,
            'len': len,
            'min': min,
            'max': max,
            'sum': sum,
            'map': map,
            'filter': filter,
            'any': any,
            'all': all,
            'zip': zip,
            'enumerate': enumerate,
        }
        # Prepare globals with limited symbols
        safe_globals = {
            '__builtins__': MappingProxyType(safe_builtins),
            'iface': self.iface,
            'QgsProject': QgsProject,
            'processing': processing,
        }

        # Patch __import__ to block dangerous modules
        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            root = name.split('.')[0]
            if root in BLOCKED_MODULES:
                raise ImportError(f"Import of '{name}' is blocked")
            return real_import(name, globals, locals, fromlist, level)

        buf_out, buf_err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
                builtins.__import__ = guarded_import
                compiled = compile(code, '<mcp_script>', 'exec')
                exec(compiled, safe_globals, {})
        except Exception as e:
            log['error'] = str(e)
        finally:
            builtins.__import__ = real_import
        log['stdout'] = buf_out.getvalue()
        log['stderr'] = buf_err.getvalue()

mcp_server_singleton = None

@asynccontextmanager
async def start_server(iface):
    global mcp_server_singleton
    mcp_server_singleton = McpServer(iface)
    await mcp_server_singleton.start()
    try:
        yield mcp_server_singleton
    finally:
        await mcp_server_singleton.stop()
