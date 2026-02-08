#!/usr/bin/env python3
import json
import socket
import struct

SOCK = '/tmp/qgis-mcp.sock'

def send(req):
    data = json.dumps(req).encode('utf-8')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(SOCK)
        s.sendall(struct.pack('>I', len(data)) + data)
        hdr = s.recv(4)
        if not hdr:
            return None
        length = struct.unpack('>I', hdr)[0]
        payload = s.recv(length)
    return json.loads(payload.decode('utf-8'))

if __name__ == '__main__':
    print('tools', send({'method': 'list_tools'}))
    print('layers', send({'method': 'list_layers'}))
    script = "print('hello from mcp');"
    res = send({'method': 'run_script', 'params': {'code': script}})
    print('run_script', res)
