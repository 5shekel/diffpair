# 🪄 AI Console

A side panel inside `diffpair-mapper.html` for sending natural-language
instructions to an AI that edits the page itself — with auto-commits,
health checks, and one-click revert on every change.

## Run

```bash
node watchdog.js          # http://localhost:8737/  (PORT=xxxx to override)
```

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
   big banner to the terminal running `watchdog.js`** — so an agent (e.g. pi)
   running it there sees instructions live.
2. The AI edits `diffpair-mapper.html` directly.
3. The watchdog (fs watcher on the directory) detects any change — including
   renames/replacements (`sed -i`, `git checkout`, agent rewrites) — and
   health-checks it:
   - size sanity (not tiny, not 4× ballooned)
   - page identity markers (`<!doctype html>`, "diffpair")
   - balanced `<script>` tags, proper closing tag
   - **`node --check` on every inline script block**
4. Healthy → auto-committed to `.versions/` (newest 25 kept, ~2 MB each),
   SSE event makes the panel offer a reload. A commit whose content hash is
   byte-identical to the last one is a no-op (no new manifest entry) —
   restoring/reverting to whatever's already live doesn't pile up duplicates.
   Broken → SSE `breakage` event, terminal alert, last-known-good copy kept
   at `.versions/last-known-good.html`.

## API

| Route | Purpose |
|---|---|
| `GET /api/status` | `{healthy, problems, uptimeSec, lastCommit, commits, lastKnownGood}` |
| `GET /api/commits` | last 30 commits (newest first) |
| `POST /api/instruction` `{text}` | record an instruction |
| `POST /api/revert` `{id}` | restore a specific commit — commits with note `"reverted to <id>"` |
| `POST /api/restore` | restore last known-good — commits with note `"restored last-known-good"` |
| `GET /api/events` | SSE: `commit` / `breakage` / `restore` / `status` |

`/api/restore` and `/api/revert` are local-only in practice: the public gate
(see `SHARE.md`) 403s them from the internet.

## Notes

- `.versions/` holds snapshots (max 25 ≈ 55 MB worst case); delete freely —
  the watchdog re-baselines on boot.
- Broken changes are *not* committed; the file stays as-is on disk so you can
  also fix it by hand (watchdog will commit the fix once it's healthy).
- Restoring/reverting to content matching the last commit is a no-op (see
  above) and also refreshes `lastGoodSize`, so a restore never leaves the
  next real edit falsely flagged as "ballooned".
