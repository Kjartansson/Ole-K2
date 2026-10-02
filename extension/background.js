// Ole K2 — Kimi Chrome Extension. Connects to a WebSocket server on
// 127.0.0.1 and executes a fixed vocabulary of tab/DOM commands for local
// AI tools.
//
// Security notes: loopback only; the server requires a shared token (paired
// once via the options page, stored in chrome.storage.local — or a local
// token.js for developers); there is no arbitrary-JS eval, only the action
// vocabulary in RUNNER below. Keep it that way.
//
// Visibility: every page action flashes a red outline over the element it
// touches and shows a small badge in the corner, so the browser's owner can
// always see what automation is doing.

let token = null;
let policyDisabled = false;
let pairingCode = null;
let pairingWs = null;
try { importScripts("token.js"); token = self.OLE_K2_TOKEN || null; }
catch { /* store/enterprise installs pair via the options page or policy */ }

// Human-speakable pairing codes: no 0/O, 1/I, no vowels (no accidental words).
function makePairingCode() {
  const ABC = "BCDFGHJKMNPQRSTVWXZ23456789";
  const buf = new Uint8Array(8);
  crypto.getRandomValues(buf);
  const raw = [...buf].map((b) => ABC[b % ABC.length]).join("");
  return "K2-" + raw.slice(0, 4) + "-" + raw.slice(4);
}

async function getPairingCode() {
  const stored = await chrome.storage.local.get("pairing_code");
  if (stored.pairing_code) return stored.pairing_code;
  pairingCode = makePairingCode();
  await chrome.storage.local.set({ pairing_code: pairingCode });
  return pairingCode;
}

async function loadToken() {
  // Chrome Enterprise policy wins over everything: an admin can deploy the
  // token to managed devices, or switch the whole bridge off.
  try {
    const managed = await chrome.storage.managed.get(["token", "disabled"]);
    if (managed.disabled === true) { policyDisabled = true; return null; }
    policyDisabled = false;
    if (managed.token) { token = managed.token; return token; }
  } catch { /* no managed storage without an enterprise policy */ }
  if (token) return token;
  const stored = await chrome.storage.local.get("token");
  token = stored.token || null;
  return token;
}

function setBadge() {
  const on = ws && ws.readyState === WebSocket.OPEN;
  chrome.action.setBadgeText({ text: on ? "ON" : "" });
  if (on) chrome.action.setBadgeBackgroundColor({ color: "#137a3f" });
}

const WS_URL = "ws://127.0.0.1:8765";

let ws = null;

async function connect() {
  if (!await loadToken()) { setBadge(); startPairing(); return; } // not paired / policy-disabled
  try {
    ws = new WebSocket(WS_URL);
  } catch {
    setTimeout(connect, 3000);
    return;
  }
  ws.onopen = () => { ws.send(JSON.stringify({ auth: token })); setBadge(); };
  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    handle(msg).then(
      (data) => send({ id: msg.id, ok: true, data }),
      (err) => send({ id: msg.id, ok: false, error: String(err && err.message || err) })
    );
  };
  ws.onclose = () => { setBadge(); setTimeout(connect, 3000); };
  ws.onerror = () => { try { ws.close(); } catch { /* reconnect via onclose */ } };
}

// Unpaired mode: hold a connection open presenting the pairing code. The
// moment someone with local access (the user's AI assistant) confirms the
// code to the server, the server answers {"paired": token} here — the token
// is stored and the bridge goes live. No file editing, no scripts for the
// user: they just read the code off the screen.
async function startPairing() {
  const code = await getPairingCode();
  chrome.action.setBadgeText({ text: "PAIR" });
  chrome.action.setBadgeBackgroundColor({ color: "#e0442e" });
  try {
    pairingWs = new WebSocket(WS_URL);
  } catch {
    setTimeout(startPairing, 5000);
    return;
  }
  pairingWs.onopen = () => pairingWs.send(JSON.stringify({ pair: code }));
  pairingWs.onmessage = async (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    if (msg.paired) {
      await chrome.storage.local.set({ token: msg.paired });
      await chrome.storage.local.remove("pairing_code");
      token = msg.paired;
      try { pairingWs.close(); } catch { /* done with it */ }
      pairingWs = null;
      setBadge();
      connect();
    }
  };
  pairingWs.onclose = () => { setTimeout(() => { if (!token) startPairing(); }, 5000); };
  pairingWs.onerror = () => { try { pairingWs.close(); } catch { /* retry via onclose */ } };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "reconnect") {
    token = null; // force a fresh read from storage
    if (ws) { try { ws.close(); } catch { /* dead already */ } }
    connect();
  }
  if (msg && msg.type === "pairing_code") {
    if (token) { sendResponse({ paired: true }); return; }
    getPairingCode().then((code) => sendResponse({ paired: false, code }));
    return true; // async response
  }
});

// First install without a pairing: open the pairing page so the user never
// has to hunt for it. Dev installs with a token.js connect silently.
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get("token", ({ token: stored }) => {
    if (!stored && !token) chrome.runtime.openOptionsPage();
  });
});

function send(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}

async function activeTabId() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) throw new Error("no active tab");
  return tab.id;
}

// The whole page-side vocabulary lives inside ONE function, because
// chrome.scripting.executeScript serializes the function alone — anything
// defined outside it would not exist in the page. No eval, only these verbs.
// Every action flashes what it touches and leaves a corner badge.
const RUNNER = function (action, args) {
  const flash = (el) => {
    if (!el || !el.getBoundingClientRect) return;
    const r = el.getBoundingClientRect();
    const d = document.createElement("div");
    d.style.cssText = "position:fixed;left:" + (r.left - 4) + "px;top:" + (r.top - 4) +
      "px;width:" + (r.width + 8) + "px;height:" + (r.height + 8) +
      "px;outline:3px solid #e0442e;border-radius:6px;z-index:2147483647;pointer-events:none;transition:opacity .8s";
    (document.body || document.documentElement).appendChild(d);
    setTimeout(() => { d.style.opacity = "0"; setTimeout(() => d.remove(), 900); }, 700);
  };
  const badge = (text) => {
    let b = document.getElementById("__vr_bridge_badge");
    if (!b) {
      b = document.createElement("div");
      b.id = "__vr_bridge_badge";
      b.style.cssText = "position:fixed;right:12px;bottom:12px;z-index:2147483647;background:#1d1f22;color:#fff;" +
        "font:12px system-ui,sans-serif;padding:6px 10px;border-radius:8px;border:1px solid #e0442e;pointer-events:none";
      (document.body || document.documentElement).appendChild(b);
    }
    b.textContent = "Bridge: " + text;
    clearTimeout(b.__t);
    b.__t = setTimeout(() => b.remove(), 2500);
  };
  const visible = (e) => !!(e.offsetWidth || e.offsetHeight);

  const A = {
    read_text: (sel) => {
      const el = sel ? document.querySelector(sel) : document.body;
      return el ? el.innerText : null;
    },
    read_html: (sel) => {
      const el = sel ? document.querySelector(sel) : document.documentElement;
      return el ? el.outerHTML : null;
    },
    click: (sel) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      el.scrollIntoView({ block: "center" });
      flash(el);
      el.click();
      return true;
    },
    // Language-agnostic text click: STRING or ARRAY of candidate texts,
    // exact match first, then "contains"; optional scope selector.
    click_text: (texts, scope) => {
      const root = scope ? document.querySelector(scope) : document;
      if (!root) return false;
      const cands = (Array.isArray(texts) ? texts : [texts]).map((t) => t.toUpperCase());
      const els = [...root.querySelectorAll("a, button, [role='button'], [role='link'], [role='option'], div, span")]
        .filter(visible);
      const exact = (e) => cands.includes((e.innerText || "").trim().toUpperCase());
      const contains = (e) => cands.some((c) => (e.innerText || "").trim().toUpperCase().includes(c));
      const el = els.filter(exact).pop() || els.filter(contains).pop();
      if (!el) return false;
      el.scrollIntoView({ block: "center" });
      flash(el);
      el.click();
      return (el.innerText || "").trim().slice(0, 120);
    },
    // Types like a person: per-character keydown, value insertion and an
    // InputEvent with data — a bare value-set + input event leaves some
    // frameworks' autocompletes (GSC's) with an empty suggestion list.
    type_text: (sel, text) => {
      const el = document.querySelector(sel);
      if (!el) return false;
      el.focus();
      flash(el);
      const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      const set = Object.getOwnPropertyDescriptor(proto, "value").set;
      set.call(el, "");
      for (const ch of text) {
        const kc = ch.toUpperCase().charCodeAt(0);
        el.dispatchEvent(new KeyboardEvent("keydown", { key: ch, keyCode: kc, which: kc, bubbles: true, cancelable: true }));
        set.call(el, el.value + ch);
        el.dispatchEvent(new InputEvent("input", { bubbles: true, data: ch, inputType: "insertText" }));
        el.dispatchEvent(new KeyboardEvent("keyup", { key: ch, keyCode: kc, which: kc, bubbles: true }));
      }
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return true;
    },
    press: (key) => {
      // Legacy keyCode/which are what older handlers (GSC's included) read.
      const KC = { Enter: 13, Escape: 27, Tab: 9, Backspace: 8, Delete: 46, ArrowDown: 40, ArrowUp: 38, " ": 32 };
      const kc = KC[key] || (key.length === 1 ? key.toUpperCase().charCodeAt(0) : 0);
      const code = key.length === 1 ? "Key" + key.toUpperCase() : key;
      const el = document.activeElement || document.body;
      flash(el);
      for (const t of ["keydown", "keypress", "keyup"]) {
        el.dispatchEvent(new KeyboardEvent(t, { key, code, keyCode: kc, which: kc, bubbles: true, cancelable: true }));
      }
      return true;
    },
    query: (sel) => [...document.querySelectorAll(sel)].slice(0, 50).map((el) => ({
      text: (el.innerText || "").trim().slice(0, 200),
      href: el.href || null,
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      aria: el.getAttribute("aria-label"),
    })),
    exists: (sel) => !!document.querySelector(sel),
    scroll: (y) => {
      badge("scroll");
      window.scrollBy(0, y || 600);
      return true;
    },
    url: () => location.href,
    title: () => document.title,
    // What language is everything in — so callers pick the right strings.
    locale: () => ({
      page: document.documentElement.lang || null,
      browser: navigator.language,
      languages: navigator.languages,
    }),
  };

  const fn = A[action];
  if (!fn) return { __error: "unknown action: " + action };
  badge(action);
  return fn(...(args || []));
};

async function execAction(tabId, action, args) {
  const [result] = await chrome.scripting.executeScript({
    target: { tabId },
    func: RUNNER,
    args: [action, args || []],
  });
  if (result === undefined) throw new Error("no frame result");
  if (result.error) throw new Error(result.error.message || "executeScript failed");
  const value = result.result;
  if (value && value.__error) throw new Error(value.__error);
  return value;
}

function waitForLoad(tabId, timeoutMs) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(listener);
      reject(new Error("load timeout"));
    }, timeoutMs || 30000);
    function listener(id, info) {
      if (id === tabId && info.status === "complete") {
        clearTimeout(timer);
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    }
    chrome.tabs.onUpdated.addListener(listener);
  });
}

async function handle(msg) {
  const cmd = msg.cmd;
  switch (cmd) {
    case "ping":
      return "pong";
    case "list_tabs": {
      const tabs = await chrome.tabs.query({});
      return tabs.map((t) => ({ id: t.id, title: t.title, url: t.url, active: t.active }));
    }
    case "navigate": {
      let tabId = msg.tabId;
      if (tabId) {
        await chrome.tabs.update(tabId, { url: msg.url });
      } else {
        const tab = await chrome.tabs.create({ url: msg.url });
        tabId = tab.id;
      }
      await waitForLoad(tabId, msg.timeoutMs).catch(() => {});
      const tab = await chrome.tabs.get(tabId);
      return { tabId, url: tab.url, title: tab.title };
    }
    case "exec":
      return { value: await execAction(msg.tabId || await activeTabId(), msg.action, msg.args) };
    case "wait_for": {
      const tabId = msg.tabId || await activeTabId();
      const deadline = Date.now() + (msg.timeoutMs || 30000);
      while (Date.now() < deadline) {
        const found = await execAction(tabId, "exists", [msg.selector]).catch(() => false);
        if (found) return true;
        await new Promise((r) => setTimeout(r, 500));
      }
      return false;
    }
    case "screenshot": {
      const tab = await chrome.tabs.get(msg.tabId || await activeTabId());
      return await chrome.tabs.captureVisibleTab(tab.windowId, { format: "png" });
    }
    case "resize": {
      const tab = await chrome.tabs.get(msg.tabId || await activeTabId());
      await chrome.windows.update(tab.windowId, {
        width: msg.width || 1280, height: msg.height || 800, state: "normal",
      });
      return true;
    }
    default:
      throw new Error("unknown cmd: " + cmd);
  }
}

connect();

// MV3 kills an idle service worker, and a dead worker's setTimeout dies with
// it — which stranded the bridge after the first disconnect. Alarms are the
// one thing that wakes a dead worker, so this both keeps the connection warm
// and resurrects it after any drop.
chrome.alarms.create("vr-bridge-keepalive", { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener(() => {
  if (!ws || ws.readyState !== WebSocket.OPEN) connect();
});
