# Ole K2 — Kimi Chrome Extension

A local bridge that lets an AI agent (Kimi Code, or any local tool) drive
**your real Chrome** — its tabs, your logged-in sessions — through a
loopback-only WebSocket. Built for agentic workflows that need an actual
browser: reading pages, clicking, typing, screenshots, watching what's on
screen.

Nothing here talks to the internet. The extension connects only to
`ws://127.0.0.1:8765`; local tools talk to a unix socket. A shared token
gates the connection.

## What you see while it works

Every action the agent takes is visible: a red outline flashes over the
element being clicked or typed into, and a small "Bridge: …" badge appears
in the corner of the page. No silent automation.

## Setup (no terminal skills needed)

1. Get the code: `git clone https://github.com/Kjartansson/Ole-K2.git`
   (any agent can do this part for you — see step 3)
2. Chrome → `chrome://extensions` → **Developer mode** → **Load unpacked**
   → select the `Ole-K2/extension` directory. The pairing page opens by
   itself and shows a short code like `K2-7X9Q-M4P2`.
3. Tell your AI assistant: *"Set up Ole K2 — my pairing code is …"* — it
   runs the companion install, registers the MCP tools, and confirms the
   code. The pairing page flips to "Paired" by itself.

Works the same with Kimi Code and Claude (Code or Desktop): `install.sh`
registers the MCP server with whichever of them is installed. Any
MCP-compatible client can also talk to `mcp_server.py` directly.

### Manual/developer setup

`./install.sh` (venv, deps, autostart, MCP registration) and pair with the
token it prints — the options page has a developer field for it. Details in
`docs/autostart.md`.

## Using it

```bash
./bc.py '{"cmd":"ping"}'
./bc.py '{"cmd":"list_tabs"}'
./bc.py '{"cmd":"navigate","url":"https://example.com"}'
./bc.py '{"cmd":"exec","action":"read_text"}'
./bc.py '{"cmd":"exec","action":"click","args":["button.buy"]}'
./bc.py '{"cmd":"exec","action":"type_text","args":["input#q","hello"]}'
./bc.py '{"cmd":"exec","action":"press","args":["Enter"]}'
./bc.py '{"cmd":"exec","action":"query","args":["a"]}'
./bc.py '{"cmd":"exec","action":"click_text","args":[["Sign in","Log ind"]]}'
./bc.py '{"cmd":"exec","action":"locale"}'
./bc.py '{"cmd":"wait_for","selector":"h1","timeoutMs":15000}'
./bc.py '{"cmd":"screenshot"}'
```

exec actions: `read_text(sel?)` `read_html(sel?)` `click(sel)`
`type_text(sel,text)` (per-character, real key events) `press(key)`
`query(sel)` `exists(sel)` `scroll(y)` `url()` `title()`
`click_text(texts, scope?)` (language-agnostic: pass candidate strings)
`locale()` (page + browser language).

## Security model — read before installing

- **Loopback only.** The server binds 127.0.0.1 and a mode-0600 unix socket.
- **Token auth.** The extension must present the token from `token.js`;
  mismatches are dropped. Never commit `token` or `token.js` (gitignored).
- **Fixed vocabulary.** The extension deliberately has NO arbitrary-JS eval
  — only the action verbs above.
- **It acts as YOU.** Anything running as your OS user that knows the token
  can drive your logged-in tabs. Treat the token like a password.
- Remove anytime: unload the extension, stop the server, delete the folder.

## Portability

The extension is OS-independent. The server runs anywhere Python runs; only
the autostart mechanism is OS-specific (Linux systemd user unit example in
`docs/autostart.md` — or just run `server.py` in a terminal).

## Enterprise deployment

Ole K2 is policy-manageable like any store extension:

- **Rollout:** force-install or allowlist by ID via `ExtensionInstallForcelist`
  / `ExtensionInstallAllowlist` once it is on the Web Store.
- **Managed pairing:** set the `token` policy (schema in
  `extension/schema.json`) so managed devices pair without any user step.
- **Kill switch:** set the `disabled` policy to `true` — the extension then
  never connects, on any managed device.

What admins usually ask, answered up front: no remote code, no telemetry,
no external network connections (loopback WebSocket only), a fixed action
vocabulary with no eval, constant-time token comparison, audit lines per
command on the server (journald when run under systemd), and every action
visibly flashed in the browser. MIT licensed.
