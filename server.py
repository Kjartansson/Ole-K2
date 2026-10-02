#!/usr/bin/env python3
"""Local Browser Bridge server.

Two listeners, both loopback-only:
  - ws://127.0.0.1:8765   the Chrome extension connects here (token auth)
  - /tmp/chrome-bridge.sock   local tools send one JSON command per line here

A command received on the unix socket is relayed to the extension, and the
extension's response is written back. One extension connection at a time; a
new one replaces the old.
"""
from __future__ import annotations

import asyncio
import json
import os

import websockets

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = open(os.path.join(HERE, "token")).read().strip()
WS_HOST, WS_PORT = "127.0.0.1", 8765
SOCK = "/tmp/chrome-bridge.sock"

state = {"ws": None}
pending: dict[int, asyncio.Future] = {}
seq = 0


async def extension_handler(ws):
    global seq
    try:
        hello = json.loads(await asyncio.wait_for(ws.recv(), 10))
        if hello.get("auth") != TOKEN:
            await ws.close(4001, "bad token")
            return
        if state["ws"] is not None:
            await state["ws"].close(4002, "replaced by a new connection")
        state["ws"] = ws
        print("extension connected", flush=True)
        async for raw in ws:
            msg = json.loads(raw)
            fut = pending.pop(msg.get("id"), None)
            if fut is not None and not fut.done():
                fut.set_result(msg)
    except (websockets.ConnectionClosed, asyncio.TimeoutError, json.JSONDecodeError):
        pass
    finally:
        if state["ws"] is ws:
            state["ws"] = None
        print("extension disconnected", flush=True)


async def cli_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global seq
    try:
        line = await asyncio.wait_for(reader.readline(), 10)
        cmd = json.loads(line.decode())
        if state["ws"] is None:
            raise RuntimeError("extension not connected")
        seq += 1
        cmd["id"] = seq
        fut = asyncio.get_running_loop().create_future()
        pending[seq] = fut
        await state["ws"].send(json.dumps(cmd))
        timeout = float(cmd.get("timeout_s", 60)) + 5
        res = await asyncio.wait_for(fut, timeout)
        writer.write((json.dumps(res) + "\n").encode())
    except Exception as exc:
        writer.write((json.dumps({"ok": False, "error": str(exc)}) + "\n").encode())
    finally:
        await writer.drain()
        writer.close()


async def keepalive():
    # A WebSocket message every 20s keeps the MV3 service worker alive.
    while True:
        await asyncio.sleep(20)
        ws = state["ws"]
        if ws is not None:
            try:
                await ws.send(json.dumps({"id": -1, "cmd": "ping"}))
            except websockets.ConnectionClosed:
                pass


async def main():
    if os.path.exists(SOCK):
        os.unlink(SOCK)
    async with websockets.serve(extension_handler, WS_HOST, WS_PORT, max_size=None):
        server = await asyncio.start_unix_server(cli_handler, SOCK)
        os.chmod(SOCK, 0o600)
        print(f"bridge up: ws://{WS_HOST}:{WS_PORT} + {SOCK}", flush=True)
        async with server:
            await asyncio.gather(server.serve_forever(), keepalive())


if __name__ == "__main__":
    asyncio.run(main())
