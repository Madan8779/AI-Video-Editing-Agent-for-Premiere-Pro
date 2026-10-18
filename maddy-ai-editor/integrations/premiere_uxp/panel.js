const ppro = require("premierepro");
const { inspectPremiere } = require("./adobe-adapter.js");
let timer = null;
let inFlight = false;
let failures = 0;
let sessionKey = "";
const status = document.getElementById("status");

function disconnect() {
  if (timer) clearInterval(timer);
  timer = null;
  sessionKey = "";
  status.textContent = "Disconnected.";
}

async function heartbeat() {
  if (inFlight || !sessionKey) return;
  inFlight = true;
  try {
    const inspection = await inspectPremiere(ppro);
    // A timer with Promise.race bounds UI waiting; no overlapping retries are issued.
    let timeout;
    const response = await Promise.race([
      fetch("http://127.0.0.1:8765/premiere/heartbeat", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + sessionKey },
        body: JSON.stringify(inspection)
      }),
      new Promise((_, reject) => { timeout = setTimeout(() => reject(new Error("Bridge timeout")), 5000); })
    ]).finally(() => clearTimeout(timeout));
    if (!response.ok) throw new Error("Bridge rejected request: " + response.status);
    failures = 0;
    status.textContent = "Connected\nProject: " + (inspection.project_name || "None open") +
      "\nSequence: " + (inspection.sequence_name || "None active");
  } catch (error) {
    failures += 1;
    status.textContent = "Connection failed: " + error.message;
    if (error.message === "Bridge timeout" || failures >= 3) {
      disconnect(); status.textContent = "Connection stopped. Check desktop and reconnect.";
    }
  } finally { inFlight = false; }
}

document.getElementById("connect").addEventListener("click", () => {
  disconnect();
  sessionKey = document.getElementById("key").value.trim();
  document.getElementById("key").value = "";
  if (!sessionKey) { status.textContent = "Paste the desktop session key first."; return; }
  failures = 0;
  heartbeat();
  timer = setInterval(heartbeat, 3000);
});
document.getElementById("disconnect").addEventListener("click", disconnect);
