"""Summarize requests Claude Code sent to the mock API. Usage: python3 check.py <log.jsonl>"""
import json, sys
for l in open(sys.argv[1]):
    d = json.loads(l); r = d["req"]
    if "count_tokens" in d["path"] or not d["path"].startswith("/v1/messages"): continue
    oc = r.get("output_config") or {}
    if "format" in oc: continue                      # session title side call
    sysp = json.dumps(r.get("system", ""))
    msgs = json.dumps(r.get("messages", []))
    if not r.get("tools") and "should be blocked" in sysp: role = "safety check"
    elif "fast executor" in sysp or "brief from the main agent" in sysp or "brief from the lead agent" in sysp: role = "SUBAGENT"
    else: role = "main"
    ctx = msgs[msgs.rfind("[router] tier="):][:24] if "[router] tier=" in msgs else ""
    print(f"  {role:13} model={r.get('model'):26} effort={str(oc.get('effort')):6} {ctx}")
