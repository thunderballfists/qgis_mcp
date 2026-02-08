import asyncio
import json
import struct
import os
import socket

UDS = '/tmp/qgis-mcp.sock'
TOKEN = os.environ.get('QGIS_MCP_TOKEN') or 'changeme'

async def handle(reader, writer):
    # simple token in first message
    try:
        hdr = await reader.readexactly(4)
    except asyncio.IncompleteReadError:
        writer.close(); await writer.wait_closed(); return
    length = struct.unpack('>I', hdr)[0]
    first = await reader.readexactly(length)
    msg = json.loads(first.decode('utf-8'))
    if msg.get('token') != TOKEN:
        writer.close(); await writer.wait_closed(); return
    # forward remaining stream for this request
    payload = json.dumps(msg.get('payload', {})).encode('utf-8')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(UDS)
        s.sendall(struct.pack('>I', len(payload)) + payload)
        resp_hdr = s.recv(4)
        if not resp_hdr:
            writer.close(); await writer.wait_closed(); return
        resp_len = struct.unpack('>I', resp_hdr)[0]
        resp = s.recv(resp_len)
    writer.write(struct.pack('>I', len(resp)) + resp)
    await writer.drain()
    writer.close(); await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle, '127.0.0.1', 8765)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
