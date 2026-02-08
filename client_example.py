#!/usr/bin/env python3
import json
import socket
import struct
import os

UDS = '/tmp/qgis-mcp.sock'
TCP = ('127.0.0.1', 8765)
TOKEN = os.environ.get('QGIS_MCP_TOKEN') or 'changeme'

def send_uds(req):
    data = json.dumps(req).encode('utf-8')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(UDS)
        s.sendall(struct.pack('>I', len(data)) + data)
        hdr = s.recv(4)
        if not hdr:
            return None
        length = struct.unpack('>I', hdr)[0]
        payload = s.recv(length)
    return json.loads(payload.decode('utf-8'))

def send_tcp(req):
    wrapped = {'token': TOKEN, 'payload': req}
    data = json.dumps(wrapped).encode('utf-8')
    with socket.create_connection(TCP) as s:
        s.sendall(struct.pack('>I', len(data)) + data)
        hdr = s.recv(4)
        if not hdr:
            return None
        length = struct.unpack('>I', hdr)[0]
        payload = s.recv(length)
    return json.loads(payload.decode('utf-8'))

def demo(send_fn):
    print('tools', send_fn({'method': 'list_tools'}))
    print('resources', send_fn({'method': 'list_resources'}))
    print('layers', send_fn({'method': 'list_layers'}))
    script = "print('hello from mcp');"
    res = send_fn({'method': 'run_script', 'params': {'code': script}})
    print('run_script', res)

if __name__ == '__main__':
    print('--- UDS ---')
    demo(send_uds)
    print('--- TCP ---')
    demo(send_tcp)
