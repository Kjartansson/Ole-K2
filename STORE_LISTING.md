# Chrome Web Store listing — Ole K2

## Name
Ole K2

## Summary (max 132 chars)
Let a local AI assistant drive your browser — visibly. Loopback-only, paired with a token. Companion server required.

## Description

Ole K2 is Kimi's hands in Chrome: instead of watching an AI assistant
describe what to click, you let it do the clicking. The assistant runs on
your own machine (Kimi Code or any MCP-compatible agent) and Ole K2 is its
browser half — it reads pages, clicks buttons, types into fields, fills
forms and takes screenshots, in your real browser, with your accounts.

EVERY action is visible while it happens: a red outline flashes over the
element being used, and a badge in the corner shows what the bridge is
doing. The toolbar icon shows ON whenever the bridge is connected. Nothing
is silent.

Security by design:
- Loopback only — the extension talks exclusively to 127.0.0.1. No data
  ever leaves your machine through Ole K2.
- Pairing token — you paste a token once (shown by the companion server);
  without it, nothing can connect. Enterprises can deploy or disable it by
  policy.
- Fixed action vocabulary — the extension cannot run arbitrary code, only
  its built-in verbs (click, type, read, navigate, screenshot, …).

Requires the free companion server and a compatible agent:
https://github.com/Kjartansson/Ole-K2

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
