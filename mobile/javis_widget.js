// Javis OS — Standalone iPhone 11 Scriptable Widget (Crimson-Dark Theme)
const TAILSCALE_IP = "100.x.y.z";
const JAVIS_PORT = 8765;
const MOBILE_TOKEN = "PASTE_YOUR_JAVIS_MOBILE_TOKEN_HERE";
const GAS_BRIEFING_URL = "PASTE_YOUR_LIFE_MANAGER_GAS_URL_HERE";
const BASE_URL = `http://${TAILSCALE_IP}:${JAVIS_PORT}`;

async function fetchJavisHealth() {
  try {
    const req = new Request(`${BASE_URL}/v1/health`);
    req.timeoutInterval = 1.5;
    const d = await req.loadJSON();
    return { online: d && d.status === "ok", hermes: !d.hermes_circuit_open };
  } catch (_) {
    return { online: false, hermes: false };
  }
}

async function fetchBriefing(online) {
  if (online) {
    try {
      const req = new Request(`${BASE_URL}/v1/ask`);
      req.method = "POST";
      req.timeoutInterval = 2.5;
      req.headers = { "Content-Type": "application/json", Authorization: `Bearer ${MOBILE_TOKEN}` };
      req.body = JSON.stringify({ query: "สรุปงานวันนี้", tts: false });
      const r = await req.loadJSON();
      if (r && r.reply) return r.reply;
    } catch (_) {}
  }
  if (GAS_BRIEFING_URL.startsWith("http")) {
    try {
      const req = new Request(`${GAS_BRIEFING_URL}?api=briefing`);
      req.timeoutInterval = 3.0;
      const d = await req.loadJSON();
      if (d && (d.summary || d.briefing)) return String(d.summary || d.briefing);
    } catch (_) {}
  }
  return "แตะปุ่ม Ask Javis เพื่อสั่งงานด้วยเสียง";
}

const health = await fetchJavisHealth();
const briefing = await fetchBriefing(health.online);
const w = new ListWidget();
const g = new LinearGradient();
g.colors = [new Color("#14070A"), new Color("#260B12"), new Color("#0D0D10")];
g.locations = [0.0, 0.55, 1.0];
w.backgroundGradient = g;
w.setPadding(14, 16, 14, 16);

const hdr = w.addStack();
const title = hdr.addText("JAVIS OS");
title.font = Font.blackSystemFont(15);
title.textColor = new Color("#FF3B5C");
hdr.addSpacer();
const st = hdr.addText(health.online ? "● MINT ON" : "○ CLOUD FALLBACK");
st.font = Font.boldSystemFont(10);
st.textColor = health.online ? new Color("#4ADE80") : new Color("#F87171");

w.addSpacer(8);
const body = w.addText(briefing);
body.font = Font.mediumSystemFont(12);
body.textColor = Color.white();
body.lineLimit = 2;
w.addSpacer(10);

const row = w.addStack();
row.spacing = 8;
const b1 = row.addStack();
b1.backgroundColor = new Color("#DC2626");
b1.cornerRadius = 8;
b1.setPadding(6, 10, 6, 10);
b1.url = "shortcuts://run-shortcut?name=Ask%20Javis";
const t1 = b1.addText("🎙️ Ask Javis");
t1.font = Font.boldSystemFont(12);
t1.textColor = Color.white();

if (config.runsInWidget) Script.setWidget(w);
else await w.presentMedium();
Script.complete();
