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
const { spawnSync, spawn } = require("child_process");

const ROOT = __dirname;
const PORT = Number(process.env.PORT || 8737);
const TARGET = path.join(ROOT, "diffpair-mapper.html");
const VERSIONS_DIR = path.join(ROOT, ".versions");
const MANIFEST = path.join(VERSIONS_DIR, "manifest.json");
const LAST_GOOD = path.join(VERSIONS_DIR, "last-known-good.html");
const INSTRUCTIONS_LOG = path.join(ROOT, "instructions.log");
const MIN_SIZE = 10 * 1024; // an intact page is ~2 MB; anything tiny is destroyed

// agent runner tuning — see "agent runner" section below
const RUNS_DIR = path.join(VERSIONS_DIR, "runs");
const AGENT_MODEL = process.env.AI_CONSOLE_MODEL || "sonnet";
const AGENT_TIMEOUT_MS = Number(process.env.AI_CONSOLE_TIMEOUT_MS) || 5 * 60 * 1000;
const AGENT_MAX_BUDGET_USD = process.env.AI_CONSOLE_MAX_BUDGET_USD || "1";
const INSTR_WINDOW_MS = 5 * 60 * 1000;
const INSTR_MAX_PER_WINDOW = 6; // /api/instruction is open to the public tunnel — cap spend/abuse
const MAX_QUEUE_LEN = 10;
let instrTimestamps = [];

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

// ------------------------------------------------------------- control plane
// The watchdog only version-controls and health-checks TARGET. Its own code
// (this file, and the public gate) is a trust boundary — it decides what
// "healthy" means and what the public internet can touch — so an edit to it
// should never be auto-applied or silently ignored. This can only *detect*
// drift after the fact (log + /api/status + SSE), not prevent it: anything
// with filesystem write access, including an AI agent editing this repo,
// can still change this file directly.
const GATE_FILE = path.join(ROOT, "webroot", "gate.js");

function sha8File(p) {
  try {
    return sha8(fs.readFileSync(p));
  } catch {
    return null;
  }
}

const bootControlHash = { watchdog: sha8File(__filename), gate: sha8File(GATE_FILE) };
const controlDrift = { watchdog: false, gate: false };

function checkControlPlaneDrift() {
  const cur = { watchdog: sha8File(__filename), gate: sha8File(GATE_FILE) };
  for (const key of Object.keys(bootControlHash)) {
    const changed = cur[key] !== bootControlHash[key];
    if (changed && !controlDrift[key]) {
      const label = key === "watchdog" ? path.basename(__filename) : "webroot/gate.js";
      console.error(`\x1b[35m[watchdog]\x1b[0m ⚠ control-plane file changed on disk: ${label} — the running process is still the old code; review the change before restarting`);
      sse("control-drift", { file: key, time: Date.now() });
    }
    controlDrift[key] = changed;
  }
}
setInterval(checkControlPlaneDrift, 20000);

const clients = new Set();
function sse(event, data) {
  const msg = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  for (const res of clients) {
    try { res.write(msg); } catch { clients.delete(res); }
  }
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
  const hash = sha8(buf);
  const list = readManifest();
  const last = list[list.length - 1];
  if (last && last.hash === hash) {
    // byte-identical to the last commit — nothing new happened, don't add noise
    if (!meta || meta.healthy !== false) fs.writeFileSync(LAST_GOOD, buf);
    return last;
  }
  const id = Date.now().toString(36) + hash.slice(0, 4);
  const file = path.join(VERSIONS_DIR, `${id}.html`);
  fs.writeFileSync(file, buf);
  const entry = {
    id,
    hash,
    size: buf.length,
    time: new Date().toISOString(),
    note: note || "change detected",
    ...(meta || {}),
  };
  list.push(entry);
  // retention: keep the newest 25 snapshots
  const trimmed = list.slice(-25);
  for (const old of list.slice(0, list.length - 25)) {
    try { fs.unlinkSync(path.join(VERSIONS_DIR, `${old.id}.html`)); } catch {}
  }
  writeManifest(trimmed);
  if (!meta || meta.healthy !== false) {
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

// ------------------------------------------------------------- agent runner
// Turns an AI Console instruction into a real edit: shells out to the
// `claude` CLI (headless, -p) restricted to Read/Edit/Glob/Grep in this
// directory. The directory watcher below still does the actual health check
// + commit — this just feeds it real changes and records what happened so
// the panel can show *why* a commit landed. Runs are serialized (one at a
// time) so two instructions never edit the file concurrently.

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function writeRun(record) {
  fs.mkdirSync(RUNS_DIR, { recursive: true });
  fs.writeFileSync(path.join(RUNS_DIR, `${record.id}.json`), JSON.stringify(record, null, 2));
  sse("run", record);
}

function readRun(id) {
  try {
    return JSON.parse(fs.readFileSync(path.join(RUNS_DIR, `${id}.json`), "utf8"));
  } catch {
    return null;
  }
}

function listRuns(limit) {
  fs.mkdirSync(RUNS_DIR, { recursive: true });
  const files = fs.readdirSync(RUNS_DIR).filter((f) => f.endsWith(".json"));
  const runs = files
    .map((f) => {
      try {
        return JSON.parse(fs.readFileSync(path.join(RUNS_DIR, f), "utf8"));
      } catch {
        return null;
      }
    })
    .filter(Boolean)
    .sort((a, b) => (a.startedAt < b.startedAt ? 1 : -1));
  // retention: keep the newest 100 run logs on disk
  for (const old of runs.slice(100)) {
    try { fs.unlinkSync(path.join(RUNS_DIR, `${old.id}.json`)); } catch {}
  }
  return runs.slice(0, limit || 50);
}

function buildPrompt(text) {
  return [
    "You are the automated AI Console agent for diffpair-mapper.html.",
    "Apply exactly this instruction by editing diffpair-mapper.html in the current directory:",
    "",
    text,
    "",
    "Rules:",
    "- Only edit diffpair-mapper.html. Never touch watchdog.js, webroot/gate.js, .git, instructions.log, instructions2.log, or anything under .versions/.",
    "- Keep it a single self-contained, valid HTML page — don't drop the doctype, and keep every <script> tag balanced and syntactically valid.",
    "- Make the smallest change that satisfies the instruction.",
    "- Don't run shell commands, install packages, or touch the network.",
  ].join("\n");
}

function runClaude(prompt) {
  return new Promise((resolve) => {
    const args = [
      "-p", prompt,
      "--output-format", "json",
      "--permission-mode", "acceptEdits",
      "--allowedTools", "Read Edit Glob Grep",
      "--disallowedTools", "Bash Write WebFetch WebSearch NotebookEdit Agent",
      "--model", AGENT_MODEL,
      "--max-budget-usd", AGENT_MAX_BUDGET_USD,
    ];
    let child;
    try {
      child = spawn("claude", args, { cwd: ROOT, stdio: ["ignore", "pipe", "pipe"] });
    } catch (err) {
      resolve({ code: -1, stdout: "", stderr: String((err && err.message) || err), timedOut: false, spawnError: true });
      return;
    }
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGKILL");
    }, AGENT_TIMEOUT_MS);
    child.stdout.on("data", (d) => { stdout += d; });
    child.stderr.on("data", (d) => { stderr += d; });
    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({ code: -1, stdout, stderr: stderr + "\n" + String((err && err.message) || err), timedOut: false, spawnError: true });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr, timedOut, spawnError: false });
    });
  });
}

let activeRun = null; // { id, events: [] } while a claude run is in flight
const runQueue = [];
let runBusy = false;

async function processInstruction(item) {
  const { id, text, ts } = item;
  activeRun = { id, events: [] };
  writeRun({ id, instruction: text, startedAt: ts, finishedAt: null, status: "running" });
  console.log(`\x1b[36m[agent]\x1b[0m run ${id} started`);

  const result = await runClaude(buildPrompt(text));

  // give the directory watcher's 700ms debounce room to attribute a trailing
  // edit to this run before we clear activeRun and move to the next one.
  await sleep(900);
  const events = activeRun ? activeRun.events : [];
  activeRun = null;

  let parsed = null;
  if (result.stdout) {
    try { parsed = JSON.parse(result.stdout.trim().split("\n").pop()); } catch {}
  }

  const status = result.spawnError ? "cli-missing"
    : result.timedOut ? "timeout"
    : result.code !== 0 ? "process-error"
    : (parsed && parsed.is_error) ? "agent-error"
    : events.some((e) => e.type === "breakage") ? "unhealthy"
    : events.length === 0 ? "no-changes"
    : "ok";

  const record = {
    id,
    instruction: text,
    startedAt: ts,
    finishedAt: new Date().toISOString(),
    status,
    sessionId: parsed ? parsed.session_id : null,
    costUsd: parsed ? parsed.total_cost_usd : null,
    durationMs: parsed ? parsed.duration_ms : null,
    resultText: parsed ? String(parsed.result || "").slice(0, 4000) : null,
    stderr: (result.stderr || "").slice(0, 4000),
    exitCode: result.code,
    events,
  };
  writeRun(record);

  const tag = status === "ok" ? "\x1b[32mOK\x1b[0m"
    : status === "no-changes" ? "\x1b[33mNO-CHANGES\x1b[0m"
    : "\x1b[31m" + status.toUpperCase() + "\x1b[0m";
  console.log(`\x1b[36m[agent]\x1b[0m run ${id} finished: ${tag}${record.costUsd ? ` ($${record.costUsd.toFixed(4)})` : ""}`);
}

function pumpQueue() {
  if (runBusy) return;
  const item = runQueue.shift();
  if (!item) return;
  runBusy = true;
  processInstruction(item)
    .catch((err) => console.error("\x1b[31m[agent]\x1b[0m run crashed:", err))
    .finally(() => {
      runBusy = false;
      pumpQueue();
    });
}

function enqueueRun(id, text, ts) {
  runQueue.push({ id, text, ts });
  pumpQueue();
}

// Watch the directory (not the file): editors/agents often replace the file via
// rename (sed -i, git checkout, cp), which silently kills a per-file watch.
let lastGoodSize = 0;
let debounce = null;
let lastHash = null;
let currentHealth = { healthy: true, problems: [], time: Date.now() };

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
    // re-read at fire time rather than trusting the buf captured above — a
    // restore/revert (or another rapid edit) may have landed while we waited
    // out the debounce, and reacting to stale content would clobber the
    // health state a concurrent restore just set.
    let buf;
    try {
      buf = fs.readFileSync(TARGET);
    } catch {
      sse("breakage", { problems: ["file missing"], time: Date.now() });
      return;
    }
    if (sha8(buf) === lastHash) return; // settled back to a known state already
    lastHash = sha8(buf);
    const prevSize = lastGoodSize || buf.length;
    const hc = healthCheck(buf, prevSize);
    if (hc.ok) {
      lastGoodSize = buf.length;
      currentHealth = { healthy: true, problems: [], time: Date.now() };
      const runId = activeRun ? activeRun.id : null;
      const entry = commit(buf, runId ? "agent edit" : "watchdog: change detected", runId ? { runId } : undefined);
      console.log(`\x1b[32m[watchdog]\x1b[0m healthy change committed — ${entry.id} (${(buf.length / 1024).toFixed(0)} KB, ${entry.hash})${runId ? ` [run ${runId}]` : ""}`);
      sse("commit", { entry, healthy: true });
      if (activeRun) activeRun.events.push({ type: "commit", entry, time: Date.now() });
    } else {
      currentHealth = { healthy: false, problems: hc.problems, time: Date.now() };
      console.error(`\x1b[31m[watchdog]\x1b[0m BREAKAGE detected:\n  - ${hc.problems.join("\n  - ")}\n`);
      console.error("[watchdog] restore with:  curl -X POST localhost:8737/api/restore");
      sse("breakage", { problems: hc.problems, time: Date.now() });
      if (activeRun) activeRun.events.push({ type: "breakage", problems: hc.problems, time: Date.now() });
    }
  }, 700);
}

const TARGET_NAME = path.basename(TARGET);

try {
  // filename is only reliably reported on Linux/inotify; when the OS omits
  // it, fall back to checking on every event rather than silently missing
  // real edits.
  fs.watch(ROOT, (eventType, filename) => {
    if (!filename || filename === TARGET_NAME) onDirEvent();
    if (!filename || filename === path.basename(__filename)) checkControlPlaneDrift();
  });
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
    healthy: currentHealth.healthy,
    problems: currentHealth.problems,
    uptimeSec: Math.round(process.uptime()),
    lastCommit: last || null,
    commits: list.length,
    lastKnownGood: fs.existsSync(LAST_GOOD) ? fs.statSync(LAST_GOOD).size : 0,
    controlPlane: {
      watchdogChanged: controlDrift.watchdog,
      gateChanged: controlDrift.gate,
    },
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
    res.on("error", () => {
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

    // /api/instruction is left open to the public tunnel (see gate.js) and now
    // actually spawns a real agent per call — cap rate + queue depth so a
    // burst of public requests can't run away with cost or pile up forever.
    const now = Date.now();
    instrTimestamps = instrTimestamps.filter((t) => now - t < INSTR_WINDOW_MS);
    if (instrTimestamps.length >= INSTR_MAX_PER_WINDOW) {
      return json(res, 429, { error: `rate limit: max ${INSTR_MAX_PER_WINDOW} instructions per ${INSTR_WINDOW_MS / 60000} min` });
    }
    if (runQueue.length >= MAX_QUEUE_LEN) {
      return json(res, 429, { error: "agent queue is full — try again shortly" });
    }
    instrTimestamps.push(now);

    const ts = new Date().toISOString();
    fs.appendFileSync(INSTRUCTIONS_LOG, `\n[${ts}] ${text}\n`);
    console.log("\n" + "=".repeat(64));
    console.log(`\x1b[1m\x1b[36m NEW AI CONSOLE INSTRUCTION ${ts} \x1b[0m`);
    console.log(text.split("\n").map((l) => "   " + l).join("\n"));
    console.log("=".repeat(64) + "\n");

    const runId = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    writeRun({ id: runId, instruction: text, startedAt: ts, finishedAt: null, status: "queued" });
    sse("instruction", { text, time: Date.now(), runId });
    enqueueRun(runId, text, ts);
    return json(res, 200, { ok: true, runId });
  }

  // ---- commits
  if (req.method === "GET" && u.pathname === "/api/commits") {
    const list = readManifest().slice().reverse().slice(0, 30);
    return json(res, 200, { commits: list });
  }

  // ---- agent run logs (query param, not a path segment, so the single-
  // segment public gate allowlist for /api/* doesn't need touching)
  if (req.method === "GET" && u.pathname === "/api/runs") {
    return json(res, 200, { runs: listRuns(50) });
  }
  if (req.method === "GET" && u.pathname === "/api/run") {
    const id = u.searchParams.get("id") || "";
    const r = /^[a-z0-9]+$/i.test(id) ? readRun(id) : null;
    if (!r) return json(res, 404, { error: "unknown run id" });
    return json(res, 200, r);
  }

  // ---- restore last known-good
  if (req.method === "POST" && (u.pathname === "/api/restore" || u.pathname === "/api/revert")) {
    let target, note;
    if (u.pathname === "/api/revert") {
      const body = JSON.parse((await readBody(req)) || "{}");
      const entry = readManifest().find((c) => c.id === body.id);
      if (!entry) return json(res, 404, { error: "unknown commit id" });
      target = path.join(VERSIONS_DIR, `${entry.id}.html`);
      note = `reverted to ${entry.id}`;
    } else {
      target = LAST_GOOD;
      note = "restored last-known-good";
    }
    if (!fs.existsSync(target)) return json(res, 404, { error: "no snapshot available" });
    const buf = fs.readFileSync(target);
    fs.writeFileSync(TARGET, buf);
    const entry = commit(buf, note);
    lastHash = sha8(buf); // don't let the watcher double-commit this write
    lastGoodSize = buf.length;
    currentHealth = { healthy: true, problems: [], time: Date.now() };
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

server.on("error", (err) => {
  if (err.code === "EADDRINUSE") {
    console.error(`\x1b[31m[watchdog]\x1b[0m port ${PORT} is already in use — a watchdog is probably already running.`);
    console.error(`[watchdog] check with:  ss -ltnp | grep ${PORT}   (or lsof -i :${PORT})`);
    process.exit(1);
  }
  throw err;
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`\x1b[1m\x1b[32m🪄 AI Console watchdog\x1b[0m listening on http://localhost:${PORT}/`);
  console.log(`   watching ${path.basename(TARGET)}`);
  console.log(`   instructions -> ${path.basename(INSTRUCTIONS_LOG)} (and this terminal) -> spawns \`claude -p\` (model: ${AGENT_MODEL})`);
  console.log(`   run logs:     http://localhost:${PORT}/api/runs`);
  console.log(`   revert:       curl -X POST http://localhost:${PORT}/api/restore`);
  const probe = spawnSync("claude", ["--version"], { encoding: "utf8" });
  if (probe.error || probe.status !== 0) {
    console.warn(`\x1b[33m[agent]\x1b[0m \`claude\` CLI not found on PATH — instructions will be logged but runs will fail with status "cli-missing".`);
  }
});
