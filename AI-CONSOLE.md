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

## Use

- 🪄 floating button (bottom-right) or **Ctrl+Shift+L** toggles the panel.
  **Esc** closes it.
- Type instructions in the box (multiline), **Ctrl+Enter** or "Send to AI ✨".
- The panel shows: watchdog connection dot, live health status, a
  "new version ready → Reload" banner, and the commit history with a
  ↩ button on every entry.
- On breakage: red status + "restore last good" button (or
  `curl -X POST localhost:8737/api/restore`).

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
   SSE event makes the panel offer a reload.
   Broken → SSE `breakage` event, terminal alert, last-known-good copy kept
   at `.versions/last-known-good.html`.

## API

| Route | Purpose |
|---|---|
| `GET /api/status` | health, last commit, commit count |
| `GET /api/commits` | last 30 commits (newest first) |
| `POST /api/instruction` `{text}` | record an instruction |
| `POST /api/revert` `{id}` | restore a specific commit |
| `POST /api/restore` | restore last known-good |
| `GET /api/events` | SSE: `commit` / `breakage` / `restore` / `status` |

## Notes

- `.versions/` holds snapshots (max 25 ≈ 55 MB worst case); delete freely —
  the watchdog re-baselines on boot.
- Broken changes are *not* committed; the file stays as-is on disk so you can
  also fix it by hand (watchdog will commit the fix once it's healthy).
