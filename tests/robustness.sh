#!/usr/bin/env bash
# Hook robustness tests. Run: bash tests/robustness.sh
cd "$(dirname "$0")/.." && export HOME=/tmp/rh && rm -rf /tmp/rh /tmp/rtp /tmp/rtc_* && mkdir -p /tmp/rh /tmp/rtp/.claude && H=hooks/router.py
t(){ printf '  %-24s' "$1"; out=$(printf '%s' "$2" | python3 $H 2>&1); rc=$?; echo "rc=$rc out=${out:0:90}"; }
echo "== bad input (must exit 0 and never block your prompt)"
t "empty stdin" ''
t "garbage" 'not json'
t "json array" '[1,2]'
t "prompt is number" '{"prompt":5}'
t "no cwd" '{"prompt":"rename a to b"}'
t "nonexistent cwd" '{"prompt":"debug the race condition","cwd":"/nope/x"}'
t "slash command" '{"prompt":"/compact","cwd":"/tmp/rtp"}'
t "agent notification" '{"prompt":"<task-notification>\\n<summary>root cause: race condition</summary>"}'
[ -d /nope ] && echo "  FAIL created /nope" || echo "  no directories created ✓"
echo "== project settings never touched"
echo '{"permissions":{"allow":["Bash(npm *)"]}}' > /tmp/rtp/.claude/settings.local.json; before=$(md5sum < /tmp/rtp/.claude/settings.local.json)
echo '{"prompt":"find the root cause of the deadlock","cwd":"/tmp/rtp"}' | python3 $H >/dev/null
[ "$before" = "$(md5sum < /tmp/rtp/.claude/settings.local.json)" ] && echo "  settings.local.json unchanged ✓" || echo "  FAIL"
echo "== conversation flow (follow ups stay in main session, never Haiku)"
for p in "add a search bar" "find the root cause of the deadlock in payments" "yes go ahead" "continue" "rename x to y" "same for the orders table" "now redesign the caching layer for multi region"; do
  r=$(echo "{\"prompt\":\"$p\",\"cwd\":\"/tmp/rtp\"}" | python3 $H | python3 -c "import sys,json;print(json.load(sys.stdin)['systemMessage'])"); printf '  %-50s %s\n' "$p" "$r"; done
echo "== concurrency: 40 parallel sessions"
for i in $(seq 1 40); do (echo "{\"prompt\":\"debug the flaky test $i\",\"cwd\":\"/tmp/rtc_$i\"}" | python3 $H >/dev/null) & done; wait
python3 -c "
import json;L=open('/tmp/rh/.claude/router/log.jsonl').read().splitlines();[json.loads(l) for l in L];print('  log lines valid:',len(L),'| prompt text stored:',any('debug' in l for l in L))"
