import importlib
import sys
import types
import pathlib

def bootstrap_qgis_stubs():
    # Minimal stubs for qgis.core and qgis.processing
    processing_mod = types.ModuleType('processing')
    def _run(alg_id, params, context=None, feedback=None):
        return {'alg': alg_id, 'params': params}
    processing_mod.run = _run

    class DummyAlg:
        def __init__(self, _id, name, provider):
            self._id = _id; self._name = name; self._provider = provider
        def id(self): return self._id
        def displayName(self): return self._name
        def provider(self): return types.SimpleNamespace(id=lambda: self._provider)

    class DummyRegistry:
        def algorithms(self):
            return [DummyAlg('native:buffer', 'Buffer', 'native')]

    class DummyApplication:
        @staticmethod
        def processingRegistry():
            return DummyRegistry()

    class DummyLayer:
        def __init__(self, _id, name, lyr_type=0, crs='EPSG:4326'):
            self._id=_id; self._name=name; self._type=lyr_type; self._crs=types.SimpleNamespace(authid=lambda: crs)
        def id(self): return self._id
        def name(self): return self._name
        def type(self): return self._type
        def crs(self): return self._crs

    class DummyProjectClass:
        def __init__(self):
            self.layers = [DummyLayer('1','A')]
        def mapLayers(self):
            return {lyr.id(): lyr for lyr in self.layers}
        @staticmethod
        def instance():
            return DummyProjectClass()

    core_mod = types.ModuleType('qgis.core')
    core_mod.QgsProject = DummyProjectClass()
    core_mod.QgsProcessingFeedback = object
    core_mod.QgsProcessingContext = object
    core_mod.QgsApplication = DummyApplication

    qgis_mod = types.ModuleType('qgis')
    qgis_mod.processing = processing_mod

    sys.modules['qgis'] = qgis_mod
    sys.modules['qgis.core'] = core_mod
    sys.modules['processing'] = processing_mod
    return processing_mod, core_mod


def load_server():
    import importlib.util
    plugin_dir = pathlib.Path(__file__).resolve().parent.parent / 'plugin'
    sys.path.append(str(plugin_dir))
    spec = importlib.util.spec_from_file_location('server', plugin_dir / 'server.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_list_layers():
    bootstrap_qgis_stubs()
    server = load_server()
    srv = server.McpServer(iface=None)
    layers = srv._list_layers()
    assert layers[0]['name'] == 'A'
    tools = server.mcp_schema.tools
    assert any(t['name'] == 'list_layers' for t in tools)


def test_path_allow():
    bootstrap_qgis_stubs()
    server = load_server()
    srv = server.McpServer(iface=None)
    assert srv._path_allowed('/tmp/foo.tif')
    assert not srv._path_allowed('/etc/passwd')


def test_run_script_blocks_import():
    bootstrap_qgis_stubs()
    server = load_server()
    srv = server.McpServer(iface=None)
    log = {'stdout': '', 'stderr': '', 'error': None}
    srv._sandbox_exec("import subprocess", log)
    assert log['error']


def test_run_script_ok():
    bootstrap_qgis_stubs()
    server = load_server()
    srv = server.McpServer(iface=None)
    log = {'stdout': '', 'stderr': '', 'error': None}
    srv._sandbox_exec("print('hi')", log)
    assert 'hi' in log['stdout']
