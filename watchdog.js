#!/usr/bin/env node
/**
 * Diffpair Mapper — AI Console watchdog & local server.
 *
 *   node watchdog.js            # serves http://localhost:8737/
 *
 * What it does:
 *  - serves this directory (the page must be opened via this server, not file://)
 *  - accepts LLM instructions from the AI Console  POST /api/instruction
 *      -> appends to instructions.log AND prints a big banner to stdout,
 *         so an AI agent (e.g. pi) running this in a terminal sees them live.
 *  - watches diffpair-mapper.html for changes (debounced), health-checks each
 *      new version, and auto-commits healthy ones to .versions/
 *  - broken changes are flagged (SSE event + red status in the console);
 *      a copy of the last known-good file is always kept for instant restore
 *  - SSE stream at GET /api/events pushes: commit / breakage / restore / status
 */
"use strict";

const http = require("http");
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { spawnSync } = require("child_process");

const ROOT = __dirname;
const PORT = Number(process.env.PORT || 8737);
const TARGET = path.join(ROOT, "diffpair-mapper.html");
const VERSIONS_DIR = path.join(ROOT, ".versions");
const MANIFEST = path.join(VERSIONS_DIR, "manifest.json");
const LAST_GOOD = path.join(VERSIONS_DIR, "last-known-good.html");
const INSTRUCTIONS_LOG = path.join(ROOT, "instructions.log");
const MIN_SIZE = 10 * 1024; // an intact page is ~2 MB; anything tiny is destroyed

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

const clients = new Set();
function sse(event, data) {
  const msg = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  for (const res of clients) res.write(msg);
}

// ---------------------------------------------------------------- versions

function sha8(buf) {
  return crypto.createHash("sha256").update(buf).digest("hex").slice(0, 8);
}

function readManifest() {
  try {
    return JSON.parse(fs.readFileSync(MANIFEST, "utf8"));
  } catch {
    return [];
  }
}
function writeManifest(list) {
  fs.mkdirSync(VERSIONS_DIR, { recursive: true });
  fs.writeFileSync(MANIFEST, JSON.stringify(list, null, 2));
}

function commit(buf, note, meta) {
  const id = Date.now().toString(36) + sha8(buf).slice(0, 4);
  const file = path.join(VERSIONS_DIR, `${id}.html`);
  fs.writeFileSync(file, buf);
  const entry = {
    id,
    hash: sha8(buf),
    size: buf.length,
    time: new Date().toISOString(),
    note: note || "change detected",
    ...(meta || {}),
  };
  const list = readManifest();
  list.push(entry);
  // retention: keep the newest 25 snapshots
  const trimmed = list.slice(-25);
  for (const old of list.slice(0, list.length - 25)) {
    try { fs.unlinkSync(path.join(VERSIONS_DIR, `${old.id}.html`)); } catch {}
  }
  writeManifest(trimmed);
  if (note === "restored" || !meta || meta.healthy !== false) {
    fs.writeFileSync(LAST_GOOD, buf);
  }
  return entry;
}

// ---------------------------------------------------------------- health

function extractScripts(html) {
  const out = [];
  const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    if (/\bsrc\s*=/i.test(m[1])) continue; // external
    if (m[2].trim()) out.push(m[2]);
  }
  return out;
}

function healthCheck(buf, prevSize) {
  const problems = [];
  const size = buf.length;
  const text = buf.toString("utf8");

  if (size < MIN_SIZE) problems.push(`file suspiciously small (${size} bytes)`);
  if (prevSize && size > prevSize * 4) problems.push(`file ballooned ${(size / prevSize).toFixed(1)}x`);
  if (!/<!doctype html>/i.test(text) || !/diffpair/i.test(text)) problems.push("page identity markers missing");
  if (!/<\/(html|body|script)>\s*$/i.test(text.trim())) problems.push("file does not end with a closing tag");
  const openTags = (text.match(/<script\b/gi) || []).length;
  const closeTags = (text.match(/<\/script>/gi) || []).length;
  if (openTags !== closeTags) problems.push(`unbalanced script tags (${openTags} open / ${closeTags} close)`);

  const scripts = extractScripts(text);
  scripts.forEach((code, i) => {
    const tmp = path.join(VERSIONS_DIR, `.check_${i}.js`);
    fs.writeFileSync(tmp, code);
    const r = spawnSync(process.execPath, ["--check", tmp], { encoding: "utf8" });
    fs.unlinkSync(tmp);
    if (r.status !== 0) {
      const line = (r.stderr || "").split("\n").find((l) => /Error/.test(l)) || "syntax error";
      problems.push(`script #${i + 1}: ${line.trim()}`);
    }
  });

  return { ok: problems.length === 0, problems };
}

// Watch the directory (not the file): editors/agents often replace the file via
// rename (sed -i, git checkout, cp), which silently kills a per-file watch.
let lastGoodSize = 0;
let debounce = null;
let lastHash = null;

function onDirEvent() {
  let buf;
  try {
    buf = fs.readFileSync(TARGET);
  } catch {
    sse("breakage", { problems: ["file missing"], time: Date.now() });
    return;
  }
  if (sha8(buf) === lastHash) return; // no real change
  clearTimeout(debounce);
  debounce = setTimeout(() => {
    lastHash = sha8(buf);
    const prevSize = lastGoodSize || buf.length;
    const hc = healthCheck(buf, prevSize);
    if (hc.ok) {
      lastGoodSize = buf.length;
      const entry = commit(buf, "watchdog: change detected");
      console.log(`\x1b[32m[watchdog]\x1b[0m healthy change committed — ${entry.id} (${(buf.length / 1024).toFixed(0)} KB, ${entry.hash})`);
      sse("commit", { entry, healthy: true });
    } else {
      console.error(`\x1b[31m[watchdog]\x1b[0m BREAKAGE detected:\n  - ${hc.problems.join("\n  - ")}\n`);
      console.error("[watchdog] restore with:  curl -X POST localhost:8737/api/restore");
      sse("breakage", { problems: hc.problems, time: Date.now() });
    }
  }, 700);
}

try {
  fs.watch(ROOT, onDirEvent);
} catch (e) {
  console.error("fs.watch failed, falling back to polling:", e.message);
  setInterval(onDirEvent, 2000);
}

// ---------------------------------------------------------------- api

function json(res, code, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(code, {
    "content-type": "application/json; charset=utf-8",
    "access-control-allow-origin": "*",
  });
  res.end(body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (c) => {
      data += c;
      if (data.length > 1e6) {
        reject(new Error("body too large"));
        req.destroy();
      }
    });
    req.on("end", () => resolve(data));
    req.on("error", reject);
  });
}

function statusObj() {
  const list = readManifest();
  const last = list[list.length - 1];
  return {
    healthy: true,
    uptimeSec: Math.round(process.uptime()),
    lastCommit: last || null,
    commits: list.length,
    lastKnownGood: fs.existsSync(LAST_GOOD) ? fs.statSync(LAST_GOOD).size : 0,
  };
}

const server = http.createServer(async (req, res) => {
  const u = new URL(req.url, `http://localhost:${PORT}`);

  // ---- SSE
  if (req.method === "GET" && u.pathname === "/api/events") {
    res.writeHead(200, {
      "content-type": "text/event-stream",
      "cache-control": "no-cache",
      connection: "keep-alive",
      "access-control-allow-origin": "*",
    });
    res.write(`event: status\ndata: ${JSON.stringify(statusObj())}\n\n`);
    clients.add(res);
    const hb = setInterval(() => res.write(": ping\n\n"), 15000);
    req.on("close", () => {
      clearInterval(hb);
      clients.delete(res);
    });
    return;
  }

  // ---- instructions
  if (req.method === "POST" && u.pathname === "/api/instruction") {
    let text = "";
    try {
      const body = JSON.parse((await readBody(req)) || "{}");
      text = String(body.text || "").trim();
    } catch (e) {
      return json(res, 400, { error: "expected {text: string}" });
    }
    if (!text) return json(res, 400, { error: "empty instruction" });
    const ts = new Date().toISOString();
    fs.appendFileSync(INSTRUCTIONS_LOG, `\n[${ts}] ${text}\n`);
    console.log("\n" + "=".repeat(64));
    console.log(`\x1b[1m\x1b[36m NEW AI CONSOLE INSTRUCTION ${ts} \x1b[0m`);
    console.log(text.split("\n").map((l) => "   " + l).join("\n"));
    console.log("=".repeat(64) + "\n");
    sse("instruction", { text, time: Date.now() });
    return json(res, 200, { ok: true });
  }

  // ---- commits
  if (req.method === "GET" && u.pathname === "/api/commits") {
    const list = readManifest().slice().reverse().slice(0, 30);
    return json(res, 200, { commits: list });
  }

  // ---- restore last known-good
  if (req.method === "POST" && (u.pathname === "/api/restore" || u.pathname === "/api/revert")) {
    let target;
    if (u.pathname === "/api/revert" && req.method === "POST") {
      const body = JSON.parse((await readBody(req)) || "{}");
      const entry = readManifest().find((c) => c.id === body.id);
      if (!entry) return json(res, 404, { error: "unknown commit id" });
      target = path.join(VERSIONS_DIR, `${entry.id}.html`);
    } else {
      target = LAST_GOOD;
    }
    if (!fs.existsSync(target)) return json(res, 404, { error: "no snapshot available" });
    const buf = fs.readFileSync(target);
    fs.writeFileSync(TARGET, buf);
    const entry = commit(buf, "restored last-known-good");
    lastHash = sha8(buf); // don't let the watcher double-commit this write
    console.log(`\x1b[33m[watchdog]\x1b[0m restored -> ${entry.id} (${(buf.length / 1024).toFixed(0)} KB)`);
    sse("restore", { entry });
    return json(res, 200, { ok: true, entry });
  }

  // ---- status
  if (req.method === "GET" && u.pathname === "/api/status") {
    return json(res, 200, statusObj());
  }

  // ---- static files
  let p = decodeURIComponent(u.pathname);
  if (p === "/") p = "/diffpair-mapper.html";
  const file = path.normalize(path.join(ROOT, p));
  if (!file.startsWith(ROOT)) {
    res.writeHead(403);
    return res.end("forbidden");
  }
  fs.readFile(file, (err, buf) => {
    if (err) {
      res.writeHead(404);
      return res.end("not found");
    }
    res.writeHead(200, {
      "content-type": MIME[path.extname(file).toLowerCase()] || "application/octet-stream",
    });
    res.end(buf);
  });
});

// ---------------------------------------------------------------- init

fs.mkdirSync(VERSIONS_DIR, { recursive: true });
const bootBuf = fs.readFileSync(TARGET);
let list = readManifest();
if (list.length === 0) {
  const entry = commit(bootBuf, "initial (watchdog boot)");
  console.log(`[watchdog] initial commit ${entry.id} (${(bootBuf.length / 1024).toFixed(0)} KB)`);
} else {
  const last = list[list.length - 1];
  const lastBuf = fs.readFileSync(path.join(VERSIONS_DIR, `${last.id}.html`));
  if (sha8(lastBuf) !== sha8(bootBuf)) commit(bootBuf, "uncommitted change found at boot");
  lastGoodSize = fs.existsSync(LAST_GOOD) ? fs.statSync(LAST_GOOD).size : bootBuf.length;
  lastHash = sha8(bootBuf);
}
if (list.length === 0) lastHash = sha8(bootBuf); // init branch: bootBuf is the latest state too

server.listen(PORT, () => {
  console.log(`\x1b[1m\x1b[32m🪄 AI Console watchdog\x1b[0m listening on http://localhost:${PORT}/`);
  console.log(`   watching ${path.basename(TARGET)}`);
  console.log(`   instructions -> ${path.basename(INSTRUCTIONS_LOG)} (and this terminal)`);
  console.log(`   revert:       curl -X POST http://localhost:${PORT}/api/restore`);
});
