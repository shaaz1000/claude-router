#!/usr/bin/env bash
# Hook robustness tests. Exits nonzero on any failure. Run: bash tests/robustness.sh
cd "$(dirname "$0")/.." && export HOME=/tmp/rh && rm -rf /tmp/rh /tmp/rtp /tmp/rtc_* && mkdir -p /tmp/rh /tmp/rtp/.claude && H=hooks/router.py
PY="${PYTHON:-python3}"; fails=0
"$PY" $H --on >/dev/null      # the router ships off; these checks exercise the on path
bad(){ echo "  FAIL: $1"; fails=$((fails+1)); }
# t <name> <stdin> <silent|routed>: hook must exit 0; "silent" means it must print nothing
t(){ printf '  %-24s' "$1"; out=$(printf '%s' "$2" | "$PY" $H 2>&1); rc=$?; echo "rc=$rc out=${out:0:90}"
     [ $rc -eq 0 ] || bad "$1 exited $rc"
     if [ "$3" = silent ]; then [ -z "$out" ] || bad "$1 should be ignored but was routed"
     else case "$out" in *'"additionalContext"'*) ;; *) bad "$1 should be routed but printed nothing";; esac; fi; }
echo "== bad input (must exit 0 and never block your prompt)"
t "empty stdin" '' silent
t "garbage" 'not json' silent
t "json array" '[1,2]' silent
t "prompt is number" '{"prompt":5}' silent
t "no cwd" '{"prompt":"rename a to b"}' routed
t "nonexistent cwd" '{"prompt":"debug the race condition","cwd":"/nope/x"}' routed
t "slash command" '{"prompt":"/compact","cwd":"/tmp/rtp"}' silent
t "agent notification" '{"prompt":"<task-notification>\\n<summary>root cause: race condition</summary>"}' silent
t "cross session message" '{"prompt":"<cross-session-message from=\\"uds:/tmp/cc-socks/1.sock\\" from-name=\\"b\\" from-mode=\\"prompting\\">\\nfind the root cause of the deadlock\\n</cross-session-message>"}' silent
t "autonomous loop tick" '{"prompt":"# Autonomous loop check\\n\\nYou are being invoked on a timer while the user is away. Find the root cause of anything broken."}' silent
t "scheduled user prompt" '{"prompt":"find the root cause of the deadlock in payments"}' routed
[ -d /nope ] && bad "created /nope" || echo "  no directories created ✓"
echo "== project settings never touched"
echo '{"permissions":{"allow":["Bash(npm *)"]}}' > /tmp/rtp/.claude/settings.local.json; before=$(cksum < /tmp/rtp/.claude/settings.local.json)
echo '{"prompt":"find the root cause of the deadlock","cwd":"/tmp/rtp"}' | "$PY" $H >/dev/null
[ "$before" = "$(cksum < /tmp/rtp/.claude/settings.local.json)" ] && echo "  settings.local.json unchanged ✓" || bad "settings.local.json changed"
echo "== conversation flow (follow ups never go to Haiku)"
for p in "add a search bar" "find the root cause of the deadlock in payments" "yes go ahead" "continue" "rename x to y" "same for the orders table" "now redesign the caching layer for multi region"; do
  r=$(echo "{\"prompt\":\"$p\",\"cwd\":\"/tmp/rtp\"}" | "$PY" $H | "$PY" -c "import sys,json;print(json.load(sys.stdin)['systemMessage'])"); printf '  %-50s %s\n' "$p" "$r"
  case "$p" in "yes go ahead"|"continue"|"same for the orders table") case "$r" in *fast*) bad "follow up '$p' routed to fast";; esac;; esac; done
echo "== concurrency: 40 parallel sessions"
for i in $(seq 1 40); do (echo "{\"prompt\":\"debug the flaky test $i\",\"cwd\":\"/tmp/rtc_$i\"}" | "$PY" $H >/dev/null) & done; wait
"$PY" -c "
import json,sys;L=open('/tmp/rh/.claude/router/log.jsonl').read().splitlines();[json.loads(l) for l in L];leak=any('debug' in l for l in L)
print('  log lines valid:',len(L),'| prompt text stored:',leak);sys.exit(1 if leak or len(L)<40 else 0)" || bad "log invalid, incomplete or contains prompt text"
[ $fails -eq 0 ] && echo "  robustness: all checks passed" || echo "  robustness: $fails check(s) failed"
[ $fails -eq 0 ]
