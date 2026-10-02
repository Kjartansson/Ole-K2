#!/usr/bin/env bash
# Ole K2 — one-command setup: server deps, pairing token, autostart,
# and Kimi Code MCP registration.
set -euo pipefail
cd "$(dirname "$0")"
HERE="$(pwd)"

echo "== Ole K2 setup =="

# 0. Already installed and running? Then there is nothing to do.
if python3 - <<'EOF' 2>/dev/null
import json, os, socket
sock = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "ole-k2-bridge.sock")
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(2)
s.connect(sock)
s.sendall(b'{"cmd":"ping"}\n')
s.shutdown(socket.SHUT_WR)
print(s.recv(64).decode())
EOF
then
  echo "✓ an Ole K2 server is already running on this machine — reusing it"
  echo
  echo "Pairing token for the extension's options page:"
  echo
  echo "  $(cat token 2>/dev/null || echo '(token file not found in this folder — use the existing install)')"
  echo
  exit 0
fi

# 1. Python deps in a private venv
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q websockets
echo "✓ server deps"

# 2. Shared token (server side). The extension gets it via the options page
#    (or a dev token.js) — it is printed at the end of this script.
if [ ! -s token ]; then
  python3 -c "import secrets; print(secrets.token_hex(24))" > token
  chmod 600 token
  echo "✓ token generated"
else
  echo "✓ token exists (unchanged)"
fi

# 3. Autostart the server (Linux systemd user unit; elsewhere: run
#    '.venv/bin/python server.py' yourself, see docs/autostart.md)
if command -v systemctl >/dev/null 2>&1 && [ -d "$HOME/.config/systemd/user" -o -w "$HOME/.config" ]; then
  mkdir -p "$HOME/.config/systemd/user"
  cat > "$HOME/.config/systemd/user/ole-k2.service" <<EOF
[Unit]
Description=Ole K2 bridge server (loopback only)

[Service]
ExecStart=$HERE/.venv/bin/python $HERE/server.py
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now ole-k2
  echo "✓ server running (systemd user service 'ole-k2')"
else
  echo "! systemd user services not available — start manually: .venv/bin/python server.py"
fi

# 4. Register the MCP server with Kimi Code (user level)
MCP_JSON="$HOME/.kimi-code/mcp.json"
mkdir -p "$HOME/.kimi-code"
python3 - "$MCP_JSON" "$HERE" <<'EOF'
import json, sys
path, here = sys.argv[1], sys.argv[2]
try:
    data = json.load(open(path))
except Exception:
    data = {}
data.setdefault("mcpServers", {})["ole-k2"] = {
    "command": f"{here}/.venv/bin/python",
    "args": [f"{here}/mcp_server.py"],
}
json.dump(data, open(path, "w"), indent=2)
print("✓ Kimi Code MCP registered in", path)
EOF

# Same MCP server for Claude Code and Claude Desktop, when installed
python3 - "$HOME" "$HERE" <<'PYEOF'
import json, os, sys
home, here = sys.argv[1], sys.argv[2]
entry = {"command": f"{here}/.venv/bin/python", "args": [f"{here}/mcp_server.py"]}
for path in (f"{home}/.claude.json", f"{home}/.config/Claude/claude_desktop_config.json"):
    if not os.path.exists(path):
        continue
    try:
        data = json.load(open(path))
    except Exception:
        continue
    servers = data.setdefault("mcpServers", {})
    if servers.get("ole-k2") != entry:
        servers["ole-k2"] = entry
        json.dump(data, open(path, "w"), indent=2)
    print("✓ MCP registered in", path)
PYEOF

echo
echo "Almost done. Two manual steps:"
echo
echo "  1. Chrome → chrome://extensions → Developer mode → Load unpacked →"
echo "     $HERE/extension"
echo "     (after the Web Store release: just install 'Ole K2' from the store)"
echo
echo "  2. Pairing: the extension's options page shows a short code — give it"
echo "     to your AI assistant and it finishes the pairing itself."
echo "     (Developers can still paste the token manually: $(cat token 2>/dev/null || echo 'created at first pairing'))"
echo
echo "Then, in Kimi Code or Claude, the mcp__ole-k2__* browser tools are"
echo "available in new sessions. Test: ask it to list your browser tabs."
