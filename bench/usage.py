#!/usr/bin/env python3
"""Read token usage and cost for one Claude Code session from its transcript.

Totals come from the transcript's `cost-state` record (`modelUsage`), the same figures `claude -p` prints
in its result. Summing per message `usage` fields is not reliable: for subagents it undercounts output tokens.

  python3 bench/usage.py ~/.claude/projects/<project>/<session-id>.jsonl
"""
import glob, json, os, sys

FIELDS = {"input": "inputTokens", "output": "outputTokens", "cache_read": "cacheReadInputTokens", "cache_write": "cacheCreationInputTokens"}


def normalize(model_usage):
    """CLI/transcript modelUsage -> {model: {input, output, cache_read, cache_write, cost_usd}}."""
    return {m: {**{k: int(u.get(src) or 0) for k, src in FIELDS.items()}, "cost_usd": float(u.get("costUSD") or 0)}
            for m, u in (model_usage or {}).items()}


def _entries(path):
    with open(path, errors="ignore") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def session_usage(transcript):
    """Return cost, per model tokens, the effort of each step and every delegation for one session."""
    out = {"cost_usd": None, "models": {}, "main": [], "subagents": [], "delegations": []}
    for d in _entries(transcript):
        if d.get("type") == "cost-state":                      # last one wins: it is cumulative
            out["cost_usd"] = d.get("totalCostUSD"); out["models"] = normalize(d.get("modelUsage"))
        elif d.get("type") == "assistant":
            step = {"model": d["message"].get("model"), "effort": d.get("effort")}
            if step not in out["main"]:
                out["main"].append(step)
            for b in d["message"].get("content", []):
                if b.get("type") == "tool_use" and b.get("name") in ("Agent", "Task"):
                    out["delegations"].append(b["input"].get("subagent_type") or "general-purpose")
    for sub in sorted(glob.glob(transcript[:-len(".jsonl")] + "/subagents/*.jsonl")):
        meta_p = sub[:-len(".jsonl")] + ".meta.json"
        meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
        steps = []
        for d in _entries(sub):
            if d.get("type") == "assistant":
                step = {"model": d["message"].get("model"), "effort": d.get("perTurnEffort")}
                if step not in steps:
                    steps.append(step)
        out["subagents"].append({"type": meta.get("agentType"), "steps": steps})
    return out


def find_transcript(home, session_id):
    hits = glob.glob(os.path.join(home, ".claude", "projects", "*", session_id + ".jsonl"))
    return hits[0] if hits else None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(json.dumps(session_usage(sys.argv[1]), indent=2))
