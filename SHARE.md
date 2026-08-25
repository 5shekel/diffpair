# diffpair — Public Share on zrok

**Live URL:** https://diffpair.z.idiot.io/

The Diffpair Mapper page is served publicly from the reserved zrok name
`diffpair` (public namespace) of the self-hosted zrok instance
(`https://z.idiot.io`). The page's 🪄 AI Console works against the
watchdog, so instructions/commits/restore are usable from the public URL.

## Architecture

```
https://diffpair.z.idiot.io
        │  (zrok2 share, agent mode, reserved name "diffpair")
        ▼
gate.js (:8090, 127.0.0.1)      webroot/gate.js
        │  only allows: / , /diffpair-mapper.html, /api/*
        │  everything else → 403
        ▼
node watchdog.js (:8737)        started: node watchdog.js
        │  serves the page + /api/* (status, commits, instruction, restore, SSE)
        │  version-controls diffpair-mapper.html into .versions/
        ▼
/home/user/diffpair/diffpair-mapper.html
```

### Why the gate?
The watchdog serves the **entire project directory** statically
(including `.env` with a token, `.git/`, `.versions/`, logs, ...). The gate
(`webroot/gate.js`) sits in front and only exposes the page and its
`/api/*` endpoints; all other paths return 403.

## Running processes

| Process | Port | Log |
|---|---|---|
| `node watchdog.js` | 8737 | `watchdog.log` (also the AI Console instruction feed) |
| `node webroot/gate.js` | 8090 | `gate.log` |
| `zrok2 agent start` | unix socket `~/.zrok2/agent.socket` | `agent.log` (filtered — see below) |
| `zrok2 share public http://127.0.0.1:8090 -n public:diffpair --force-agent --headless` | — | `zrok-share.log` |

## Repro steps

```sh
# 1. Reserved name (one-time)
zrok2 create name diffpair            # namespace token defaults to "public"
zrok2 list names                      # verify RESERVED = true

# 2. Agent (needed for the share; foreground command → nohup it)
rm -f ~/.zrok2/agent.socket           # only if a stale socket blocks it
nohup sh -c 'zrok2 agent start 2>&1 | grep --line-buffered -v "\"msg\":\"map\[method:" >> agent.log' &

# 3. Watchdog (serves the page + console API on :8737)
nohup node watchdog.js > watchdog.log 2>&1 &

# 4. Gate (path filter on :8090)
nohup node webroot/gate.js > gate.log 2>&1 &

# 5. Publish on the reserved name:  -n <namespaceToken>:<name>
nohup zrok2 share public http://127.0.0.1:8090 -n public:diffpair \
  --force-agent --headless > zrok-share.log 2>&1 &
```

### `agent.log` — filtered, on purpose

`zrok2 agent`'s stdout is a structured JSON log of every boot/error/retry
event **plus one `"msg":"access"` line per HTTP request through the tunnel**
— that access-log stream is the only thing that ever makes this file grow
unboundedly (a browser tab left open on the public URL, polling
`/api/status`, is enough to add ~1 line/sec forever). It has no ongoing
value here — the app-level request handling is already visible in
`watchdog.log`/`gate.log` if needed — so step 2 above pipes the agent's
output through `grep -v` to drop those lines before they ever hit disk,
keeping only boot/warn/error lines (which is what actually mattered the one
time this needed debugging — see TODO.md's 2026-08-25 "round 2" entry).
`zrok2` itself has no quieter log-level flag (`-v` only *adds* verbosity),
so filtering the stream is the only way to silence it.

**Gotcha:** the agent also persists a local registry at
`~/.zrok2/agent-registry.json` and replays it on every boot to
auto-recreate shares — so restarting the agent process alone is enough to
bring the `diffpair` share back; you generally do **not** need to also
re-run the `zrok2 share public ...` command from step 5 after an agent
restart (doing both races and produces duplicate registry entries that
permanently 409-conflict with each other, needing a manual edit of that
file to fix — worth checking `cat ~/.zrok2/agent-registry.json` first if a
restart ever leaves the share stuck retrying).

## Caveats

- **SSE does not stream through this zrok instance.** The zrok proxy
  buffers chunked/streamed responses until the body ends (verified with a
  controlled streaming test, both local and agent share modes). So on the
  public URL the console's live feed (`/api/events`) hangs — the connection
  dot stays "connecting", and live commit/breakage notifications won't
  appear. SSE works fine directly on `http://localhost:8737`.
- Everything else on the public URL works: page, `POST /api/instruction`
  (instructions still land in the watchdog terminal + `instructions.log`),
  `GET /api/commits`, `GET /api/status`, `POST /api/restore|/api/revert`.
- `-n` selector format is `<namespaceToken>:<name>` (bare `-n diffpair`
  fails — parsed as a namespace token). This zrok2 build has no
  `run`/`reserve` commands; equivalents are `share public ...` /
  `create name ...`.
- The gate forwards `transfer-encoding: chunked` for streamed responses;
  without it, HTTP clients treat the body as read-until-close.

## Stop / restart

```sh
pkill -f 'zrok2 share public http://127[.]0[.]0[.]1:8090'   # tunnel
pkill -f 'node webroot/[g]ate.js'                            # gate
pkill -f 'zrok2 agent sta[r]t'                               # agent
# watchdog: leave running, or  pkill -f 'watchdog[.]js'
```

Restart with the numbered steps above. The reserved name `diffpair`
persists across sessions; only the tunnel/agent need recreating.

Note: `pkill -f` patterns must avoid matching their own command line —
use the bracket trick (e.g. `[g]ate`) or patterns not present verbatim.
