#!/usr/bin/env bash
# Ole K2 — one-command setup: server deps, pairing token, autostart,
# and Kimi Code MCP registration.
set -euo pipefail
cd "$(dirname "$0")"
HERE="$(pwd)"

echo "== Ole K2 setup =="

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

echo
echo "Almost done. Two manual steps:"
echo
echo "  1. Chrome → chrome://extensions → Developer mode → Load unpacked →"
echo "     $HERE/extension"
echo "     (after the Web Store release: just install 'Ole K2' from the store)"
echo
echo "  2. Pair: open the extension's options (Details → Extension options)"
echo "     and paste this token:"
echo
echo "     $(cat token)"
echo
echo "Then, in Kimi Code, the mcp__ole-k2__* browser tools are available"
echo "in new sessions. Test: ask Kimi to list your browser tabs."
