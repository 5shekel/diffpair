#!/usr/bin/env node
/**
 * Public gate in front of the watchdog (127.0.0.1:8737).
 *
 * The watchdog serves the *entire* project directory statically (including
 * .env, .git, .versions, logs, ...). This gate only exposes what the public
 * page needs: the mapper page itself and its /api/* endpoints. Everything
 * else gets 403. The zrok share points at this gate, not the watchdog.
 *
 *   node webroot/gate.js        # listens on :8090 (PORT to override)
 */
"use strict";

const http = require("http");
const PORT = Number(process.env.PORT || 8090);
const UP = "http://127.0.0.1:8737";

// allowed paths: "/", "/diffpair-mapper.html", "/api/..."
const ALLOW = /^\/(api\/[a-zA-Z0-9_-]*$|diffpair-mapper\.html$|$)/;

const server = http.createServer((req, res) => {
  let p;
  try {
    p = decodeURIComponent(new URL(req.url, UP).pathname);
  } catch {
    res.writeHead(400);
    return res.end("bad request");
  }
  if (!ALLOW.test(p)) {
    res.writeHead(403);
    return res.end("forbidden");
  }
  const up = http.request(UP + req.url, { method: req.method, headers: req.headers }, (upRes) => {
    // Keep transfer-encoding (chunked) for streamed responses such as SSE —
    // without it, proxies treat the body as read-until-close and buffer it.
    // Node re-chunks the (already de-chunked) stream itself.
    res.writeHead(upRes.statusCode, upRes.headers);
    upRes.pipe(res);
  });
  up.on("error", () => {
    res.writeHead(502);
    res.end("bad gateway");
  });
  req.pipe(up);
});

server.listen(PORT, () => console.log(`gate listening on :${PORT} -> ${UP}`));
