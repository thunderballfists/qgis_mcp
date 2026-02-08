import asyncio
import json
import os
import socket
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from qgis.core import (
    QgsProject,
    QgsProcessingFeedback,
    QgsProcessingContext,
    QgsProcessingAlgorithm,
    QgsApplication,
)
from qgis import processing

SOCKET_PATH = Path('/tmp/qgis-mcp.sock')
MAX_MESSAGE_SIZE = 5 * 1024 * 1024  # 5 MB
TIMEOUT_SEC = 30

class McpServer:
    def __init__(self, iface, socket_path=SOCKET_PATH):
        self.iface = iface
        self.socket_path = Path(socket_path)
        self.server = None
        self._runs = {}

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
        if method == 'list_layers':
            return {'result': self._list_layers()}
        if method == 'list_algorithms':
            return {'result': self._list_algs()}
        if method == 'run_processing':
            return await self._run_processing(req.get('params', {}))
        if method == 'run_script':
            return await self._run_script(req.get('params', {}))
        if method == 'fetch_log':
            run_id = req.get('params', {}).get('run_id')
            return {'result': self._runs.get(run_id)}
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
        ctx = QgsProcessingContext()
        fb = QgsProcessingFeedback()
        try:
            res = await asyncio.get_event_loop().run_in_executor(
                None, lambda: processing.run(alg_id, alg_params, context=ctx, feedback=fb)
            )
            return {'result': res}
        except Exception as e:
            return {'error': str(e)}

    async def _run_script(self, params):
        code = params.get('code', '')
        run_id = str(uuid.uuid4())
        log = {'stdout': '', 'stderr': '', 'error': None}
        self._runs[run_id] = log
        def runner():
            import io, sys, contextlib
            buf_out, buf_err = io.StringIO(), io.StringIO()
            safe_globals = {'iface': self.iface, 'QgsProject': QgsProject, 'processing': processing}
            try:
                with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
                    exec(code, safe_globals, {})
            except Exception as e:
                log['error'] = str(e)
            log['stdout'] = buf_out.getvalue()
            log['stderr'] = buf_err.getvalue()
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, runner)
        return {'result': {'run_id': run_id, **log}}

mcp_server_singleton = None

@asynccontextmanager
def start_server(iface):
    global mcp_server_singleton
    mcp_server_singleton = McpServer(iface)
    await mcp_server_singleton.start()
    try:
        yield mcp_server_singleton
    finally:
        await mcp_server_singleton.stop()
