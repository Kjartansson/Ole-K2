const input = document.getElementById("token");
const status = document.getElementById("status");

chrome.storage.local.get("token", ({ token }) => {
  if (token) {
    status.textContent = "Paired. The bridge connects automatically.";
    status.className = "ok";
    input.value = token;
  }
});

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
    setTimeout(() => { status.textContent = "Paired. The bridge connects automatically."; }, 1500);
  });
});
