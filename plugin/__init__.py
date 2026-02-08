from .plugin import QgisMcpPlugin

def classFactory(iface):
    return QgisMcpPlugin(iface)
