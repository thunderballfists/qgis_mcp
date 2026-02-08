import asyncio
from qgis.PyQt.QtCore import QObject, QCoreApplication, QTimer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from . import resources_rc  # noqa: F401
from .server import start_server

class QgisMcpPlugin(QObject):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.action = None
        self._server_ctx = None
        self._loop = asyncio.get_event_loop()

    def initGui(self):
        icon = QIcon(':/qgis_mcp/icons/mcp.svg')
        self.action = QAction(icon, self.tr('Start MCP Server'), self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self._toggle)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removeToolBarIcon(self.action)
        if self._server_ctx:
            self._loop.run_until_complete(self._server_ctx.__aexit__(None, None, None))

    def _toggle(self, checked):
        if checked:
            self._start_server()
        else:
            self._stop_server()

    def _start_server(self):
        async def runner():
            self._server_ctx = start_server(self.iface)
            await self._server_ctx.__aenter__()
        self._loop.create_task(runner())
        self._msg_info('MCP server starting (Unix socket: /tmp/qgis-mcp.sock)')

    def _stop_server(self):
        if not self._server_ctx:
            return
        self._loop.create_task(self._server_ctx.__aexit__(None, None, None))
        self._server_ctx = None
        self._msg_info('MCP server stopped')

    def tr(self, message):
        return QCoreApplication.translate('QgisMcpPlugin', message)

    def _msg_info(self, msg):
        self.iface.messageBar().pushInfo('QGIS MCP', msg)
