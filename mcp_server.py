#!/usr/bin/env python3
"""Ole K2 as an MCP server (stdio) — browser tools for Kimi Code.

Register in ~/.kimi-code/mcp.json:

    { "mcpServers": { "ole-k2": {
        "command": "/PATH/TO/Ole-K2/.venv/bin/python",
        "args": ["/PATH/TO/Ole-K2/mcp_server.py"] } } }

Kimi then sees mcp__ole-k2__* tools. The MCP server is a thin relay: it
forwards commands to the running bridge server (server.py) over the unix
socket, which relays to the Chrome extension. install.sh does all of this.
"""
from __future__ import annotations

import json
import socket
import sys

SOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "ole-k2-bridge.sock")

TOOLS = [
    {"name": "ping", "desc": "Check the browser bridge is alive.", "schema": {"type": "object", "properties": {}}},
    {"name": "list_tabs", "desc": "List all open browser tabs (id, title, url, active).", "schema": {"type": "object", "properties": {}}},
    {"name": "navigate", "desc": "Open a URL in a new tab (or reuse tab_id).", "schema": {"type": "object", "properties": {"url": {"type": "string"}, "tabId": {"type": "integer"}}, "required": ["url"]}},
    {"name": "read_text", "desc": "Read the visible text of the page (or of one CSS element).", "schema": {"type": "object", "properties": {"selector": {"type": "string"}, "tabId": {"type": "integer"}}}},
    {"name": "click", "desc": "Click the element matching a CSS selector.", "schema": {"type": "object", "properties": {"selector": {"type": "string"}, "tabId": {"type": "integer"}}, "required": ["selector"]}},
    {"name": "click_text", "desc": "Click a button/link by its visible text. Accepts several candidate strings (e.g. translations).", "schema": {"type": "object", "properties": {"texts": {"type": "array", "items": {"type": "string"}}, "scope": {"type": "string"}, "tabId": {"type": "integer"}}, "required": ["texts"]}},
    {"name": "type_text", "desc": "Type text into an input (per-character, real key events).", "schema": {"type": "object", "properties": {"selector": {"type": "string"}, "text": {"type": "string"}, "tabId": {"type": "integer"}}, "required": ["selector", "text"]}},
    {"name": "press", "desc": "Press a key (Enter, Escape, Tab, ArrowDown...) on the focused element.", "schema": {"type": "object", "properties": {"key": {"type": "string"}, "tabId": {"type": "integer"}}, "required": ["key"]}},
    {"name": "query", "desc": "List elements matching a CSS selector (text, href, tag, aria label).", "schema": {"type": "object", "properties": {"selector": {"type": "string"}, "tabId": {"type": "integer"}}, "required": ["selector"]}},
    {"name": "wait_for", "desc": "Wait until a CSS selector exists on the page (timeout_ms, default 30000).", "schema": {"type": "object", "properties": {"selector": {"type": "string"}, "timeoutMs": {"type": "integer"}, "tabId": {"type": "integer"}}, "required": ["selector"]}},
    {"name": "screenshot", "desc": "Capture the visible tab as a PNG (returned base64).", "schema": {"type": "object", "properties": {"tabId": {"type": "integer"}}}},
    {"name": "locale", "desc": "Report the page language and browser locales.", "schema": {"type": "object", "properties": {"tabId": {"type": "integer"}}}},
    {"name": "pair", "desc": "Pair with the browser extension: the user reads the pairing code shown on the Ole K2 options page.", "schema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}},
]

ACTION_CMDS = {"read_text": "read_text", "click": "click", "click_text": "click_text",
               "type_text": "type_text", "press": "press", "query": "query",
               "locale": "locale", "read_html": "read_html", "exists": "exists", "scroll": "scroll"}


def send_to_bridge(cmd: dict) -> dict:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(float(cmd.get("timeout_s", 60)) + 15)
    s.connect(SOCK)
    s.sendall((json.dumps(cmd) + "\n").encode())
    s.shutdown(socket.SHUT_WR)
    data = b""
    while True:
        chunk = s.recv(1 << 16)
        if not chunk:
            break
        data += chunk
    return json.loads(data.decode())


def call_tool(name: str, args: dict) -> dict:
    if name == "pair":
        cmd = {"cmd": "pair", "code": args["code"]}
    elif name in ("ping", "list_tabs"):
        cmd = {"cmd": name}
    elif name == "navigate":
        cmd = {"cmd": "navigate", "url": args["url"], "timeout_s": args.get("timeout_s", 60)}
        if args.get("tabId"):
            cmd["tabId"] = args["tabId"]
    elif name == "wait_for":
        cmd = {"cmd": "wait_for", "selector": args["selector"], "timeoutMs": args.get("timeoutMs", 30000),
               "timeout_s": (args.get("timeoutMs", 30000) // 1000) + 15}
        if args.get("tabId"):
            cmd["tabId"] = args["tabId"]
    elif name == "screenshot":
        cmd = {"cmd": "screenshot"}
        if args.get("tabId"):
            cmd["tabId"] = args["tabId"]
    elif name in ACTION_CMDS:
        action_args = []
        if name in ("read_text", "read_html", "exists"):
            action_args = [args["selector"]] if args.get("selector") else []
        elif name == "click":
            action_args = [args["selector"]]
        elif name == "click_text":
            action_args = [args["texts"]] + ([args["scope"]] if args.get("scope") else [])
        elif name == "type_text":
            action_args = [args["selector"], args["text"]]
        elif name == "press":
            action_args = [args["key"]]
        elif name == "query":
            action_args = [args["selector"]]
        elif name == "scroll":
            action_args = [args.get("y", 600)]
        cmd = {"cmd": "exec", "action": ACTION_CMDS[name], "args": action_args,
               "timeout_s": args.get("timeout_s", 60)}
        if args.get("tabId"):
            cmd["tabId"] = args["tabId"]
    else:
        raise ValueError(f"unknown tool {name}")
    return send_to_bridge(cmd)


def result(payload: dict) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = req.get("method", "")
        rid = req.get("id")
        if method == "initialize":
            out = {"jsonrpc": "2.0", "id": rid, "result": {
                "protocolVersion": req.get("params", {}).get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ole-k2", "version": "1.0.0"}}}
        elif method == "tools/list":
            out = {"jsonrpc": "2.0", "id": rid, "result": {"tools": [
                {"name": t["name"], "description": t["desc"], "inputSchema": t["schema"]} for t in TOOLS]}}
        elif method == "tools/call":
            p = req.get("params", {})
            try:
                out = {"jsonrpc": "2.0", "id": rid, "result": result(call_tool(p.get("name", ""), p.get("arguments") or {}))}
            except Exception as exc:
                out = {"jsonrpc": "2.0", "id": rid, "result": {
                    "content": [{"type": "text", "text": f"error: {exc}"}], "isError": True}}
        elif method == "ping":
            out = {"jsonrpc": "2.0", "id": rid, "result": {}}
        elif method.startswith("notifications/") or rid is None:
            continue
        else:
            out = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"no such method: {method}"}}
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
