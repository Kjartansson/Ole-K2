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
import hmac
import json
import os

import websockets

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(HERE, "token")


def current_token() -> str:
    """The shared token, or "" before the first pairing creates it."""
    try:
        return open(TOKEN_FILE).read().strip()
    except OSError:
        return ""
WS_HOST, WS_PORT = "127.0.0.1", 8765
SOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "ole-k2-bridge.sock")

state = {"ws": None}
pending: dict[int, asyncio.Future] = {}
pending_pairs: dict[str, object] = {}   # pairing code -> extension websocket
pair_attempts: list[float] = []         # rate limit for pair confirmations
seq = 0

PAIR_WINDOW_S = 600        # a code stays valid for 10 minutes of attempts
PAIR_MAX_ATTEMPTS = 5      # ...with at most 5 confirmations per window


async def extension_handler(ws):
    global seq
    try:
        hello = json.loads(await asyncio.wait_for(ws.recv(), 10))
        if "pair" in hello:
            # Unpaired extension presenting its code: hold the connection and
            # wait for a local tool to confirm the code via the unix socket.
            code = str(hello["pair"])
            if code in pending_pairs:
                await ws.close(4003, "code already pending")
                return
            pending_pairs[code] = ws
            print(f"audit: pairing code presented ({code[:3]}…)", flush=True)
            try:
                async for _ in ws:
                    pass  # pending connections accept no commands
            finally:
                pending_pairs.pop(code, None)
            return
        tok = current_token()
        if not tok or not hmac.compare_digest(str(hello.get("auth", "")), tok):
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


async def confirm_pairing(code: str) -> dict:
    """A local tool confirms the code shown on the extension's pairing page.

    Rate-limited, and only ever completes for a code that is actually on
    someone's screen right now. On success the extension gets the token over
    its pending connection; a first-time server mints the token here.
    """
    now = asyncio.get_running_loop().time()
    pair_attempts[:] = [t for t in pair_attempts if now - t < PAIR_WINDOW_S]
    if len(pair_attempts) >= PAIR_MAX_ATTEMPTS:
        print("audit: pair attempt REJECTED (rate limit)", flush=True)
        return {"ok": False, "error": "too many attempts, try again later"}
    pair_attempts.append(now)
    ws = pending_pairs.pop(code, None)
    if ws is None:
        print("audit: pair attempt with unknown code", flush=True)
        return {"ok": False, "error": "no such pairing code on screen"}
    tok = current_token()
    if not tok:
        import secrets
        tok = secrets.token_hex(24)
        with open(TOKEN_FILE, "w") as fh:
            fh.write(tok + "\n")
        os.chmod(TOKEN_FILE, 0o600)
    await ws.send(json.dumps({"paired": tok}))
    try:
        await ws.close()
    except websockets.ConnectionClosed:
        pass
    print("audit: pairing COMPLETED", flush=True)
    return {"ok": True, "data": "paired"}


async def cli_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global seq
    try:
        line = await asyncio.wait_for(reader.readline(), 10)
        cmd = json.loads(line.decode())
        print(f"audit: cmd={cmd.get('cmd')} action={cmd.get('action')}", flush=True)
        if cmd.get("cmd") == "pair":
            res = await confirm_pairing(str(cmd.get("code", "")))
            writer.write((json.dumps(res) + "\n").encode())
            return
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
