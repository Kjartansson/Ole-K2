# Chrome Web Store listing — Ole K2

## Name
Ole K2

## Summary (max 132 chars)
Kimi's hands in Chrome — the AI clicks, types and reads pages for you. Local only, token-paired, every action visible.

## Description

KIMI'S HANDS IN CHROME

A lot of browser work is repetitive: forms, portals, pages with no export
button. Ole K2 lets your AI assistant do it instead of you. The assistant
runs on your own machine — Kimi Code or any MCP-compatible agent — and
Ole K2 is its browser half: it reads pages, clicks, types, navigates, fills
forms and takes screenshots, in your real browser, with your sessions.

You watch it happen. Every click flashes a red outline on the element being
used, a badge in the corner shows what the bridge is doing, and the toolbar
icon shows ON whenever the bridge is connected. You step in whenever you
want.

WHAT PEOPLE USE IT FOR

- "Check my site the way a user sees it" — the agent browses, you build
- Repetitive web chores: filling, clicking through, gathering
- Letting an agent work in pages that need your login — the session is
  yours, the machine is yours, nothing passes a third party
- Browser-driven testing while you write code

YOU'RE IN CONTROL

- Loopback only: Ole K2 talks exclusively to a server on 127.0.0.1. No
  data leaves your machine through this extension — there is no cloud
  component at all.
- Token pairing: the bridge answers only to the token you paste once (or
  that your admin deploys). No token, no connection.
- Fixed vocabulary: the extension cannot execute arbitrary code. It has a
  short list of verbs — click, type, read, navigate, screenshot — and
  nothing else.
- Honest signal: the ON badge and the red flash make automation visible
  at all times.

FOR ENTERPRISE

Admins can force-install or allowlist Ole K2 by ID, deploy the pairing
token via managed policy (schema included), or disable the bridge org-wide
with one policy flag. No telemetry, no remote code, per-command audit lines
on the companion server. MIT licensed.

FOR DEVELOPERS

The companion server speaks MCP (Model Context Protocol): Kimi Code gets
browser_* tools out of the box, and any MCP client can drive the same
vocabulary. Source, protocol notes and setup:
https://github.com/Kjartansson/Ole-K2

GETTING STARTED

1. Install this extension — the pairing page opens on its own
2. Read the short code on that page to your AI assistant (Kimi Code, Claude)
   — it installs the free companion server and finishes the pairing
3. Ask for something in the browser — and watch it happen

No scripts, no terminal, no account. Developers who prefer manual setup:
github.com/Kjartansson/Ole-K2

Note: Chrome on desktop. Not for Chromium forks that lack MV3 service
workers, and not for mobile.

## Category
Developer Tools

## Language
English

## Privacy practices tab

- Single purpose: "Connects this browser to a user-approved AI assistant
  running on the same machine, so the assistant can operate web pages at
  the user's request."
- Permission justifications:
  - tabs: "Lists open tabs and their URLs when the user's local agent asks,
    e.g. 'what tabs do I have open?'"
  - scripting + host access (all_urls): "Executes the extension's fixed
    action vocabulary (click, type, read) on the page the user asks the
    agent to work on. No code is fetched or injected from anywhere; the
    vocabulary is compiled into the extension."
  - alarms: "Keeps the loopback connection alive across Chrome's service
    worker lifecycle."
  - storage: "Stores the pairing token locally in the browser."
- Data usage: "No data is collected, transmitted, sold or shared. All
  traffic is between the extension and a server on 127.0.0.1."
- Privacy policy: the README's security section —
  https://github.com/Kjartansson/Ole-K2#security-model

## Store assets (store-assets/)

- icon-128.png
- screenshot-1.png (1280x800) — bridge driving a page, badge visible
- screenshot-2.png (1280x800) — the pairing page

## Review notes (for the submission form)

- The extension is the browser half of a local-only pair; the companion
  server is open source at the homepage URL. Reviewers can test pairing
  with any token — the server accepts the token it was started with.
- Ole K2 contains no advertising, analytics, or remote code, and makes no
  network connections except the loopback WebSocket to 127.0.0.1:8765.
