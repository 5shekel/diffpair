# 🪄 AI Console — issues & TODO (WIP)

Status legend: [ ] open · [x] done

## Findings (from log + code audit, 2026-08-25)

### Process / runtime
1. **Stale running process** — watchdog PID 3413026 booted Aug 23 20:44 but
   `watchdog.js` on disk was edited Aug 23 22:39. The running code ≠ disk code;
   the Aug 23 edit never went live. Same for the gate (PID 929497 booted
   Aug 24 00:32, `gate.js` edited 22:42).
2. **Failed restart crashed with a raw stack trace** — `watchdog.log` ends in
   `EADDRINUSE :::8737` (Aug 24 22:33). No friendly "already running" message,
   no single-instance guard.
3. **Watchdog bound to `*` (all interfaces)** — `server.listen(PORT)` has no
   host, so `:8737` was reachable from the LAN, bypassing the gate's
   whitelist entirely.
4. **Dead zrok share on :8091** (PID 931955) — nothing listens on 8091, the
   tunnel just 502s.
5. **`agent.log` grew to 19 MB** — zrok logs every access; a panel left open on
   the public URL polled `/api/status` ~68,000 times. No rotation.

### Duplicate commits (the reported bug)
6. **`/api/restore` and `/api/revert` commit unconditionally** — every restore
   call pushes a new manifest entry even when the content is byte-identical to
   the last commit. Manifest already has hash `2769d1e5` 4× (all
   "restored last-known-good").
7. **Revert path commits with the wrong note** — it says
   "restored last-known-good" instead of which commit was reverted.
8. **Restore doesn't update `lastGoodSize`** — after restoring a smaller
   known-good, the next healthy change can be falsely flagged "ballooned 4×".
9. **Boot path can also add a duplicate** — "uncommitted change found at boot"
   has no hash-dedupe (it does compare, but restore/initial flows compound).
10. **Dead code in `commit()`** — `note === "restored"` never matches (the
    actual note is "restored last-known-good").

### Status / health reporting
11. **`/api/status` always reports `healthy: true`** — even right after a
    breakage; a reconnecting panel gets "✅" for a broken page.
12. **Panel `status` SSE handler unconditionally shows ✅** — ignores
    `s.healthy`, same problem client-side.

### Security (public tunnel `diffpair.z.idiot.io`)
13. **Gate allows state-changing POSTs publicly** — anyone on the internet can
    `POST /api/restore` / `/api/revert` (overwrite the file) or spam
    `/api/instruction`. No auth of any kind.

### Robustness
14. **SSE responses have no `error` handler** — a dying client can raise an
    unhandled 'error' on `res.write` and crash the server.
15. **Watcher re-hashes on *any* file change in the project root** — log
    writes (agent.log, instructions.log, photos) trigger a 2 MB read + sha256.
    Wasteful, not wrong.

### Housekeeping
16. **`webroot/` is a dead design** — duplicate copies of the HTML, a dead
    `python http.server` (see `webroot-server.log` 404s on `/api/status`), and
    `gate.js`. The running watchdog still uses `ROOT = __dirname`.
17. **No instruction ack/queue** — instructions sit in `instructions.log` with
    no record of which were acted on; if no agent is watching the terminal
    they're silently lost (this is exactly what happened to the 2026-08-25
    instruction).

## Tasks

- [x] T1: Dedupe commits — skip commit when `sha8(buf)` == last manifest hash
      (restore, revert, watcher, boot paths)
- [x] T2: Fix revert note → "reverted to <id>"
- [x] T3: Update `lastGoodSize` on restore
- [x] T4: Track real health in `/api/status` (+ breakage detail for reconnects)
- [x] T5: Panel: respect `s.healthy` in the status SSE handler
- [x] T6: Bind watchdog to 127.0.0.1
- [x] T7: Friendly single-instance error on EADDRINUSE
- [x] T8: Gate: block `/api/restore` + `/api/revert` publicly (keep
      `/api/instruction` so remote suggestions still work — add real auth later)
- [x] T9: SSE res error handler
- [x] T10: Clean up duplicate manifest entries + orphan .versions files
- [x] T11: Kill dead zrok share (:8091), truncate agent.log
- [x] T12: Restart watchdog + gate with the new code, verify
      (restore twice → no new commit; restore blocked publicly; port local-only)
- [x] T13b (bonus, not originally numbered): fixed a debounce/restore race in
      `onDirEvent` — the 700ms-delayed health check re-reads the file at fire
      time instead of trusting a stale buffer, so a restore that lands while
      a breakage check is still pending can no longer get silently
      overwritten back to "unhealthy" with stale data.

- [x] T13: Decide the fate of `webroot/` — deleted the dead duplicate
      `webroot/diffpair-mapper.html` and `webroot/index.html` (both were
      untracked in git, byte-identical to the real files, and unused —
      `gate.js` only proxies, it never serves them). Kept `webroot/gate.js`,
      the actively-run public gate.
- [ ] T14: Auth for the public share (token in URL/header for POSTs, or
      read-only public page). Not done — T8 already blocks the two
      destructive endpoints publicly, so this is lower urgency now; still
      needs a decision on the token/UX scheme before implementing.
- [ ] T15: Instruction queue with ack state (e.g. instructions.json with
      status: pending/done) so agents can't silently miss instructions.
      Not done — needs a decision on who/what consumes the ack state.
- [x] T16: Log rotation for agent.log — the previous truncate had gone stale
      (zrok's writer held a stale fd offset, so the "0-byte" file was
      actually sparse and would have kept *looking* huge). Restarted the
      zrok agent + share cleanly instead so the log genuinely starts at 0;
      combined with T17's slower poll this should stay small. No real
      rotation mechanism exists yet if it grows again.
- [x] T17: Panel: SSE-only once the `/api/events` connection is confirmed
      live (`open` event), falling back to polling otherwise; bumped the
      fallback poll from 4s → 15s since SSE never connects over the public
      zrok tunnel (documented buffering caveat in SHARE.md), so public
      viewers poll indefinitely — 15s keeps that from generating another
      68k-hit log.
