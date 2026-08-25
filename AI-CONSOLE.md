# 🪄 AI Console

A side panel inside `diffpair-mapper.html` for sending natural-language
instructions to an AI that edits the page itself — with auto-commits,
health checks, and one-click revert on every change.

## Run

```bash
node watchdog.js          # http://localhost:8737/  (PORT=xxxx to override)
```

Requires the `claude` CLI on `PATH` and authenticated (it's what actually
executes each instruction). If it's missing, the watchdog logs a warning at
boot and every run just fails fast with status `cli-missing` — instructions
still get logged, nothing else breaks.

**Open the page via `http://localhost:8737/`, not `file://`** — the panel
talks to the watchdog over HTTP.

The watchdog binds to `127.0.0.1` only — it's not reachable from the LAN or
the internet directly. Public access (e.g. `diffpair.z.idiot.io`) goes
through `webroot/gate.js` in front of it; see `SHARE.md` for that setup.
The gate blocks `POST /api/restore` and `/api/revert` publicly (no auth yet
on those, and they overwrite the file) but leaves `POST /api/instruction`
open so remote suggestions still work.

## Use

- 🪄 floating button (bottom-right) or **Ctrl+Shift+L** toggles the panel.
  **Esc** closes it.
- Type instructions in the box (multiline), **Ctrl+Enter** or "Send to AI ✨".
- The panel shows: watchdog connection dot, live health status, a
  "new version ready → Reload" banner, and the commit history with a
  ↩ button on every entry.
- On breakage: red status + "restore last good" button (or
  `curl -X POST localhost:8737/api/restore`).
- The health status reflects `/api/status`'s real `healthy` flag (not just
  "connected") — a reconnecting panel sees an actual breakage, not a stale
  ✅. The panel prefers the SSE stream once `/api/events` is confirmed live
  and only falls back to polling `/api/status` (every 15s) when it isn't —
  SSE never connects over the public zrok tunnel (it buffers streamed
  responses), so public viewers run on the poller.

## How the AI side works

1. Every instruction is appended to `instructions.log` **and printed as a
   big banner to the terminal running `watchdog.js`**.
2. The watchdog itself spawns the agent: a headless `claude -p` run, scoped
   to `Read`/`Edit`/`Glob`/`Grep` (no `Bash`/`Write`/network tools),
   `cwd`-restricted to this directory, told to touch only
   `diffpair-mapper.html`. Runs are serialized — one instruction is fully
   processed before the next one starts — so two runs can never edit the
   file at once. Configurable via env: `AI_CONSOLE_MODEL` (default
   `sonnet`), `AI_CONSOLE_TIMEOUT_MS` (default 5 min), and
   `AI_CONSOLE_MAX_BUDGET_USD` (per-run spend cap, default `1`).
3. Each run is logged to `.versions/runs/<id>.json` (instruction, status,
   cost, duration, result text, stderr, and which commit(s) it produced) and
   pushed live over SSE. The panel's **Agent runs** section lists these —
   click one to expand it. Any commit a run produced also gets a **log**
   button in **Commit history** that opens the same detail inline, so you
   can go from "why did this change?" straight to the instruction that
   caused it.
4. `POST /api/instruction` is left open to the public tunnel (see below), so
   it's rate-limited (6 instructions / 5 min) and queue-capped (10 pending)
   to bound cost/abuse from that exposure — a burst past those limits gets a
   `429`.
5. The watchdog (fs watcher on the directory) reacts only to
   `diffpair-mapper.html` — including renames/replacements (`sed -i`,
   `git checkout`, agent rewrites) — everything else in the project
   (`agent.log`, `instructions.log`, `photos/`, ...) is ignored rather than
   triggering a wasted 2 MB read + hash. It health-checks the file:
   - size sanity (not tiny, not 4× ballooned)
   - page identity markers (`<!doctype html>`, "diffpair")
   - balanced `<script>` tags, proper closing tag
   - **`node --check` on every inline script block**
6. Healthy → auto-committed to `.versions/` (newest 25 kept, ~2 MB each),
   SSE event makes the panel offer a reload. A commit whose content hash is
   byte-identical to the last one is a no-op (no new manifest entry) —
   restoring/reverting to whatever's already live doesn't pile up duplicates.
   Broken → SSE `breakage` event, terminal alert, last-known-good copy kept
   at `.versions/last-known-good.html`.

## Watching the watchdog

`watchdog.js` and `webroot/gate.js` are the trust boundary — they decide
what counts as "healthy" and what the public internet can touch — so the
watchdog treats edits to its *own* code differently from edits to the page:
it hashes both files at boot and checks for drift (instantly for
`watchdog.js` via the same fs watcher, every 20s for `gate.js` since it's in
a subdirectory the non-recursive watcher can't see into). A change is never
auto-applied or auto-restarted — it's only logged loudly and surfaced as
`controlPlane.{watchdogChanged,gateChanged}` in `/api/status` plus a
`control-drift` SSE event, so a changed control file doesn't go live until
someone reviews it and restarts on purpose.

This is detection, not prevention: anything with filesystem write access —
including the AI Console's own agent, or any other AI agent editing this
repo — can still change `watchdog.js` or `gate.js` directly. The agent's
`--allowedTools` only permits `Read`/`Edit`/`Glob`/`Grep` and its prompt
tells it to touch only `diffpair-mapper.html`, but that's a prompt-level
instruction, not a path-level sandbox — a crafted public instruction could
still ask it to edit a control file. There's no OS-level barrier stopping
that; this just makes sure it can't happen silently.

## API

| Route | Purpose |
|---|---|
| `GET /api/status` | `{healthy, problems, uptimeSec, lastCommit, commits, lastKnownGood, controlPlane}` |
| `GET /api/commits` | last 30 commits (newest first); a commit an agent run produced carries `runId` |
| `POST /api/instruction` `{text}` | log + queue an instruction for the agent — `{ok, runId}`; `429` if rate/queue-limited |
| `GET /api/runs` | last 50 agent run logs (newest first) |
| `GET /api/run?id=<id>` | one run's full log: instruction, status, cost, duration, result text, stderr, commits it produced |
| `POST /api/revert` `{id}` | restore a specific commit — commits with note `"reverted to <id>"` |
| `POST /api/restore` | restore last known-good — commits with note `"restored last-known-good"` |
| `GET /api/events` | SSE: `commit` / `breakage` / `restore` / `status` / `run` / `instruction` |

`/api/restore` and `/api/revert` are local-only in practice: the public gate
(see `SHARE.md`) 403s them from the internet. `/api/run(s)` use a query
param rather than a path segment (`/api/run?id=…`, not `/api/run/…`) so they
pass the gate's single-segment `/api/*` allowlist without needing a
`gate.js` change.

## Notes

- `.versions/` holds snapshots (max 25 ≈ 55 MB worst case); delete freely —
  the watchdog re-baselines on boot.
- Broken changes are *not* committed; the file stays as-is on disk so you can
  also fix it by hand (watchdog will commit the fix once it's healthy).
- Restoring/reverting to content matching the last commit is a no-op (see
  above) and also refreshes `lastGoodSize`, so a restore never leaves the
  next real edit falsely flagged as "ballooned".
