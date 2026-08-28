# diffpair — public share on zrok
#
# Layout:  zrok tunnel -> gate.js (:8090) -> watchdog.js (:8737) -> diffpair-mapper.html
# See SHARE.md for the full write-up. Targets here just wrap those steps.
#
#   make up        start everything (agent, watchdog, gate, tunnel)
#   make down      stop tunnel + gate + agent (watchdog left running)
#   make restart   down, then up
#   make status    show what's listening / which processes are up
#   make logs      tail -f every log
#   make name      one-time: reserve the public name "diffpair"

SHELL         := /bin/sh
ZROK          := zrok2
SHARE_NAME    := public:diffpair
WATCHDOG_PORT := 8737
GATE_PORT     := 8090

# The zrok agent runs headless behind a unix socket; `zrok2 agent status`
# is the source of truth for whether it's up and which shares it holds.
# Stop patterns use the bracket trick so pkill doesn't match its own line.
AGENT_UP  := $(ZROK) agent status >/dev/null 2>&1
SHARE_UP  := $(ZROK) agent status 2>/dev/null | grep -q diffpair
K_GATE    := node webroot/[g]ate.js
K_WATCH   := node watchdog[.]js
K_AGENT   := zrok2 agent sta[r]t
K_SHARE   := zrok2 share pub[l]ic

.PHONY: up down restart status logs name \
        agent watchdog gate share \
        stop-share stop-gate stop-agent stop-watchdog

up: agent watchdog gate share
	@echo
	@echo "  up -> https://diffpair.z.idiot.io/   (local: http://localhost:$(WATCHDOG_PORT)/)"
	@$(MAKE) --no-print-directory status

down: stop-share stop-gate stop-agent
	@echo "down (watchdog left running; 'make stop-watchdog' to kill it too)"

restart: down
	@sleep 1
	@$(MAKE) --no-print-directory up

# --- individual processes ------------------------------------------------

agent:
	@if $(AGENT_UP); then \
	  echo "agent    already running"; \
	else \
	  rm -f $$HOME/.zrok2/agent.socket; \
	  a='agent start'; \
	  nohup sh -c "$(ZROK) $$a 2>&1 | grep --line-buffered -v '\"msg\":\"map\[method:' >> agent.log" >/dev/null 2>&1 & \
	  echo "agent    started"; \
	  sleep 2; \
	fi

watchdog:
	@if ss -ltn 2>/dev/null | grep -q ':$(WATCHDOG_PORT) '; then \
	  echo "watchdog already running  (:$(WATCHDOG_PORT))"; \
	else \
	  w=watchdog.js; \
	  nohup node $$w > watchdog.log 2>&1 & \
	  echo "watchdog started  (:$(WATCHDOG_PORT))"; \
	  sleep 1; \
	fi

gate:
	@if ss -ltn 2>/dev/null | grep -q ':$(GATE_PORT) '; then \
	  echo "gate     already running  (:$(GATE_PORT))"; \
	else \
	  g=webroot/gate.js; \
	  nohup node $$g > gate.log 2>&1 & \
	  echo "gate     started  (:$(GATE_PORT))"; \
	  sleep 1; \
	fi

# The agent replays ~/.zrok2/agent-registry.json on boot, so once "diffpair"
# is registered the agent usually brings the share back by itself. Re-running
# the share command while it's already up races and creates duplicate
# 409-conflicting registry entries — so only run it if the agent has no
# diffpair share.
share:
	@if $(SHARE_UP); then \
	  echo "share    already up  ($(SHARE_NAME))"; \
	else \
	  u="http://127.0.0.1:$(GATE_PORT)"; s='share public'; \
	  nohup $(ZROK) $$s $$u -n $(SHARE_NAME) --force-agent --headless > zrok-share.log 2>&1 & \
	  echo "share    started  ($(SHARE_NAME))"; \
	  sleep 1; \
	fi

# --- stops -------------------------------------------------------------

stop-share:
	@pkill -f '$(K_SHARE)' && echo "share    stopped" || echo "share    not running"

stop-gate:
	@pkill -f '$(K_GATE)'  && echo "gate     stopped" || echo "gate     not running"

stop-agent:
	@pkill -f '$(K_AGENT)' && echo "agent    stopped" || echo "agent    not running"

stop-watchdog:
	@pkill -f '$(K_WATCH)' && echo "watchdog stopped" || echo "watchdog not running"

# --- info ---------------------------------------------------------------

status:
	@printf '%-9s %s\n' watchdog "$$(ss -ltn 2>/dev/null | grep -q ':$(WATCHDOG_PORT) ' && echo up || echo down)"
	@printf '%-9s %s\n' gate     "$$(ss -ltn 2>/dev/null | grep -q ':$(GATE_PORT) ' && echo up || echo down)"
	@printf '%-9s %s\n' agent    "$$($(AGENT_UP) && echo up || echo down)"
	@printf '%-9s %s\n' share    "$$($(SHARE_UP) && echo up || echo down)"
	@echo "--- listeners ---"
	@ss -ltnp 2>/dev/null | grep -E ':($(WATCHDOG_PORT)|$(GATE_PORT)) ' || echo "(none on :$(WATCHDOG_PORT)/:$(GATE_PORT))"

logs:
	@tail -f watchdog.log gate.log agent.log zrok-share.log

name:
	@$(ZROK) create name diffpair
	@$(ZROK) list names
