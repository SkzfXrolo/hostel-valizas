/**
 * Valizas WhatsApp bridge — Baileys local HTTP API
 * Endpoints: /health /status /messages /stop /logout
 */
import express from "express";
import qrcode from "qrcode";
import pino from "pino";
import fs from "fs";
import path from "path";
import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
} from "@whiskeysockets/baileys";

const PORT = Number(process.env.WA_PORT || 8787);
const AUTH_DIR = process.env.WA_AUTH_DIR || path.join(process.cwd(), "auth");
const logger = pino({ level: "silent" });

fs.mkdirSync(AUTH_DIR, { recursive: true });

const state = {
  connected: false,
  qrDataUrl: null,
  qrText: null,
  phone: null,
  lastError: null,
  messages: [],
  msgSeq: 0,
  sock: null,
  starting: false,
};

function pushMessage(msg) {
  state.msgSeq += 1;
  const row = { id: state.msgSeq, ...msg, at: Date.now() };
  state.messages.unshift(row);
  if (state.messages.length > 200) state.messages.length = 200;
  return row;
}

async function startSock() {
  if (state.starting) return;
  state.starting = true;
  state.lastError = null;

  try {
    const { state: authState, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
    const { version } = await fetchLatestBaileysVersion();
    const sock = makeWASocket({
      version,
      logger,
      printQRInTerminal: false,
      auth: {
        creds: authState.creds,
        keys: makeCacheableSignalKeyStore(authState.keys, logger),
      },
      syncFullHistory: false,
      markOnlineOnConnect: false,
    });
    state.sock = sock;

    sock.ev.on("creds.update", saveCreds);

    sock.ev.on("connection.update", async (update) => {
      const { connection, lastDisconnect, qr } = update;
      if (qr) {
        state.qrText = qr;
        state.qrDataUrl = await qrcode.toDataURL(qr, {
          margin: 1,
          width: 320,
          color: { dark: "#0b2a33", light: "#ffffff" },
        });
        state.connected = false;
      }
      if (connection === "open") {
        state.connected = true;
        state.qrDataUrl = null;
        state.qrText = null;
        state.phone = sock.user?.id?.split(":")[0] || null;
      }
      if (connection === "close") {
        state.connected = false;
        const code = lastDisconnect?.error?.output?.statusCode;
        const shouldReconnect = code !== DisconnectReason.loggedOut;
        state.lastError = `close:${code || "unknown"}`;
        state.sock = null;
        state.starting = false;
        if (shouldReconnect) {
          setTimeout(() => startSock().catch(() => {}), 1500);
        } else {
          state.qrDataUrl = null;
        }
        return;
      }
    });

    sock.ev.on("messages.upsert", ({ messages, type }) => {
      if (type !== "notify") return;
      for (const m of messages) {
        if (!m.message || m.key.fromMe) continue;
        const jid = m.key.remoteJid || "";
        if (jid.endsWith("@g.us") || jid === "status@broadcast") continue;
        const text =
          m.message.conversation ||
          m.message.extendedTextMessage?.text ||
          m.message.imageMessage?.caption ||
          "";
        if (!text.trim()) continue;
        const from = (m.pushName || jid.split("@")[0] || "Contacto").trim();
        pushMessage({
          from,
          jid,
          text: text.trim(),
          keyId: m.key.id,
        });
      }
    });
  } catch (err) {
    state.lastError = String(err?.message || err);
    state.starting = false;
    setTimeout(() => startSock().catch(() => {}), 2500);
    return;
  }
  state.starting = false;
}

async function logout() {
  try {
    if (state.sock) await state.sock.logout();
  } catch {
    /* ignore */
  }
  state.sock = null;
  state.connected = false;
  state.qrDataUrl = null;
  state.phone = null;
  try {
    fs.rmSync(AUTH_DIR, { recursive: true, force: true });
    fs.mkdirSync(AUTH_DIR, { recursive: true });
  } catch {
    /* ignore */
  }
  state.starting = false;
  await startSock();
}

const app = express();
app.use(express.json({ limit: "1mb" }));

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.get("/status", (_req, res) => {
  res.json({
    ok: true,
    connected: state.connected,
    qr: state.qrDataUrl,
    phone: state.phone,
    error: state.lastError,
    messageCount: state.messages.length,
  });
});

app.get("/messages", (req, res) => {
  const since = Number(req.query.since || 0);
  const messages = state.messages.filter((m) => m.id > since);
  res.json({ ok: true, messages });
});

app.post("/send", async (req, res) => {
  try {
    const jid = String(req.body?.jid || "").trim();
    const text = String(req.body?.text || "").trim();
    const imagePath = String(req.body?.imagePath || "").trim();
    if (!jid) {
      res.status(400).json({ ok: false, error: "jid es requerido" });
      return;
    }
    if (!text && !imagePath) {
      res.status(400).json({ ok: false, error: "text o imagePath son requeridos" });
      return;
    }
    if (!state.connected || !state.sock) {
      res.status(409).json({ ok: false, error: "WhatsApp no está conectado" });
      return;
    }
    if (imagePath) {
      if (!fs.existsSync(imagePath)) {
        res.status(400).json({ ok: false, error: "imagen no encontrada" });
        return;
      }
      const buffer = fs.readFileSync(imagePath);
      const payload = { image: buffer };
      if (text) payload.caption = text;
      await state.sock.sendMessage(jid, payload);
    } else {
      await state.sock.sendMessage(jid, { text });
    }
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ ok: false, error: String(err?.message || err) });
  }
});

app.post("/stop", (_req, res) => {
  try {
    state.sock?.end?.(undefined);
  } catch {
    /* ignore */
  }
  res.json({ ok: true });
  setTimeout(() => process.exit(0), 200);
});

app.post("/logout", async (_req, res) => {
  await logout();
  res.json({ ok: true });
});

app.listen(PORT, "127.0.0.1", () => {
  startSock().catch((err) => {
    state.lastError = String(err?.message || err);
  });
});
