const input = document.getElementById("token");
const status = document.getElementById("status");
const pairingDiv = document.getElementById("pairing");
const doneDiv = document.getElementById("done");
const codeEl = document.getElementById("code");

function refresh() {
  chrome.runtime.sendMessage({ type: "pairing_code" }, (res) => {
    if (!res) return;
    if (res.paired) {
      pairingDiv.style.display = "none";
      doneDiv.style.display = "block";
    } else {
      codeEl.textContent = res.code;
    }
  });
}
refresh();
setInterval(refresh, 2000);

document.getElementById("save").addEventListener("click", () => {
  const token = input.value.trim();
  if (token.length < 16) {
    status.textContent = "That looks too short — paste the full token from install.sh.";
    status.className = "bad";
    return;
  }
  chrome.storage.local.set({ token }, () => {
    status.textContent = "Saved. Connecting…";
    status.className = "ok";
    chrome.runtime.sendMessage({ type: "reconnect" });
    setTimeout(refresh, 1500);
  });
});
