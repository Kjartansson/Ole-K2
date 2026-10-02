#!/usr/bin/env python3
"""Send one JSON command to the Local Browser Bridge and print the reply.

    ~/chrome-bridge/bc.py '{"cmd":"ping"}'
    ~/chrome-bridge/bc.py '{"cmd":"list_tabs"}'
    ~/chrome-bridge/bc.py '{"cmd":"navigate","url":"https://example.com"}'
    ~/chrome-bridge/bc.py '{"cmd":"exec","action":"read_text"}'
    ~/chrome-bridge/bc.py '{"cmd":"exec","action":"click","args":["button.buy"]}'
    ~/chrome-bridge/bc.py '{"cmd":"exec","action":"type_text","args":["input#q","hello"]}'
    ~/chrome-bridge/bc.py '{"cmd":"wait_for","selector":"h1","timeoutMs":15000}'
    ~/chrome-bridge/bc.py '{"cmd":"screenshot"}' > shot.json   # data URL in .data

Commands: ping | list_tabs | navigate(url, tabId?) | exec(action, args, tabId?)
| wait_for(selector, timeoutMs, tabId?) | screenshot(tabId?)

exec actions: read_text(sel?) read_html(sel?) click(sel) type_text(sel,text)
press(key) query(sel) exists(sel) scroll(y) url() title()
"""
import json
import socket
import sys

cmd = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"cmd": "ping"}
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(float(cmd.get("timeout_s", 60)) + 15)
s.connect("/tmp/chrome-bridge.sock")
s.sendall((json.dumps(cmd) + "\n").encode())
s.shutdown(socket.SHUT_WR)
data = b""
while True:
    chunk = s.recv(1 << 16)
    if not chunk:
        break
    data += chunk
print(data.decode())
