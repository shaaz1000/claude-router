#!/usr/bin/env python3
"""Claude Router v5: classifies each prompt locally (no API call, zero tokens)
and routes it to a model + effort via subagents in Claude Code.

Two modes (config "main_model"):

  opus (default, Anthropic's recommended pattern: Opus leads, Sonnet executes)
    fast      -> main session            (Opus, terse); router-fast (Haiku) only for bulk work
    standard  -> router-sonnet subagent  (Sonnet) when the change spans 2+ files or 50+ lines,
                 otherwise main session
    deep/max  -> main session            (Opus); analysis only unless a change was asked for

  sonnet (budget mode)
    fast      -> router-fast subagent    (Haiku)
    standard  -> main session            (Sonnet)
    deep      -> router-deep subagent    (Opus, high) plans, main implements
    max       -> router-max subagent     (Opus, xhigh) plans, main implements

Why subagents: tested on Claude Code 2.1.289, the main session's effortLevel is
read only at session start, and hooks cannot change model. Subagents carry
their own model and effort, verified end to end.

Scores only what you WROTE. Pasted logs, code, data and documents are measured
as payload: they raise the floor to "standard" (Sonnet handles big context
fine) but never push a simple ask up to Opus.

Off by default. In our benchmark (bench/) routing did not save money, so it is opt in:

  python3 router.py --on | --off | --status     switch it; the setting lives in config.json and persists
  !fast !std !deep !max                         prefix one prompt to route just that prompt while off

Hook: UserPromptSubmit.   Test: python3 router.py --test "your prompt"
"""
import json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path

ROUTER_DIR = Path.home() / ".claude" / "router"
CONFIG_PATH = ROUTER_DIR / "config.json"
LOG_PATH = ROUTER_DIR / "log.jsonl"

DEFAULTS = {
    "enabled": False,            # off by default: the hook stays silent unless a prompt starts with a ! prefix
    "main_model": "opus",        # what your main session runs on: opus (recommended) | sonnet
    "thresholds": {"fast_max_chars": 160, "deep_score": 3, "max_score": 6},
    "log": True,
}
TIERS = ["fast", "standard", "deep", "max"]

DEEP = {  # pattern: weight (3 = deep on its own, 2 = needs company, 1 = weak hint)
    r"root cause": 3, r"race conditions?": 3, r"deadlocks?": 3, r"memory leaks?": 3,
    r"security (audit|review)": 3, r"vulnerab\w+": 3, r"architect\w*": 3, r"distributed": 3,
    r"from scratch": 3, r"ultrathink": 3, r"think (hard|deeply)": 3, r"flaky": 3,
    r"intermittent\w*": 3, r"bottleneck\w*": 3, r"concurren\w+": 3,
    r"across (the|our|my) (codebase|repo|project|services)": 3,
    r"why (does|is|isn't|doesn't|do|are|did)": 3,
    r"design (a|an|the)? ?\w* ?(system|schema|api|architecture|service)": 3,
    r"refactor\w*": 2, r"migrat\w+": 2, r"optimi[sz]\w*": 2, r"performance": 2,
    r"scal(e|ing|ability)": 2, r"trade ?offs?": 2, r"debug\w*": 2, r"investigate": 2,
    r"rewrite": 2, r"end to end": 2, r"plan (out|for|the)": 2,
    r"(multi|several|multiple) (file|service|step)s?": 2, r"profil(e|ing)": 2,
    r"implement\w*": 1, r"build (a|an|the|me)": 1, r"production": 1, r"under load": 1,
    r"monolith\w*": 3, r"decoupl\w+": 2, r"(split|extract|break) .{0,40} (into|out)": 2,
    r"event driven": 2, r"idempoten\w+": 2, r"poke holes": 3, r"critique": 2,
    r"(figure|find) out (why|what|how)": 3, r"how (is|was) that possible|how that's possible": 3,
    r"how should we": 2, r"properly": 1, r"strategy": 1, r"redesign\w*": 3, r"data model": 2,
    r"(nobody|no one) knows why": 3, r"not sure (how|what|whether|if|where)": 3,
    r"(best|right) (way|approach) to": 2, r"brainstorm\w*": 2, r"explor\w+ (options|ideas|approaches)": 2,
    r"should (i|we) (use|go|pick|choose)": 2, r"pros and cons": 2, r"plan (to|for)": 2, r"evaluate": 1, r"restructur\w+": 2,
}
SYMPTOM = {  # plain English bug descriptions; each weight 2
    r"randomly", r"sometimes", r"only (happens|fails|in)", r"inconsisten\w+", r"falls? over",
    r"crash\w*", r"slow\w*", r"hangs?", r"freez\w+", r"corrupt\w*", r"leak\w*",
    r"at the same time", r"rps", r"throughput", r"latency", r"p9\d", r"timeouts?",
    r"other users'?", r"wrong (data|user|totals?|results?)", r"after deploys?", r"under load",
    r"double (charg\w*|count\w*|process\w*|book\w*)", r"keeps? (climbing|growing|increasing)", r"worse than"
}
SCOPE = re.compile(r"\b(all|every|entire|whole|everything|across)\b|\bin /?[\w-]+/|\b\w+(components|files|endpoints|modules|services|pages|routes)\b|\b(components|files|endpoints|modules|services|pages|routes)\b")
FAST = [
    r"renam\w+", r"typos?", r"format\w*", r"lint\w*", r"indent\w*", r"add (a )?comments?",
    r"what is", r"what's", r"whats", r"what are", r"what does", r"list", r"show me", r"where is",
    r"find (all|the file|where|usages|references)", r"delete", r"remove (the )?unused", r"change the \w+ (color|colour|text|label|padding|margin|size)",
    r"grep", r"git (status|log|diff|add|commit|push|stash)", r"commit message",
    r"convert", r"translate", r"summari[sz]\w*", r"tl;?dr", r"extract", r"count",
    r"explain (this|the|what)", r"which (line|file|one)", r"quick\w*", r"simple", r"one liner",
    r"bump", r"install", r"proofread", r"spell\w*", r"sort", r"capitali[sz]e",
]
CONCEPT_Q = re.compile(r"^(what (is|are)|what's|explain|define|difference between|how does .{0,60} work)\b")
NEGATION = re.compile(r"\b(don'?t|do not|no need to|without|not(?! sure)|never|avoid)\b(\s+\w+){1,3}")
CUE = re.compile(r"\b(this|these|below|following|above|attached|here is|here are|here's|my notes|the (text|doc|log|file|output|article|email))\b")
DATA_LINE = re.compile(
    r"^\s*(\d{4}-\d\d-\d\d|\d\d:\d\d(:\d\d)?|\[\d|at \S+\(|File \"|Traceback|#\d+ |\$ |> |"
    r"\{|\}|\[|\]|<\/?\w|\"[\w-]+\"\s*:|(import|from|def|class|function|const|let|var|public|private|return|if|for|while)\b)"
    r"|[;{}]\s*$|=>|==|\(\);|^\s*\|.{0,400}\|\s*$|^\s{4,}\S|^\t"
    r"|^[^,\s]{0,40}(,[^,]{0,40}){2,}$|^(From|To|Subject|Date|Cc):\s")
LOOKUP = re.compile(r"^(list|show|find|where|what|which|git|grep|count)\b")
FOLLOWUP = re.compile(r"^(y(es|eah|ep)?|ok(ay)?|sure|go( ahead)?|do it|continue|proceed|next|try again|again|"
                      r"same (for|with|thing)|now (do|the|apply)|and (also|then)|keep going|looks good|lgtm|perfect|"
                      r"haan|theek hai|kar do)\b")
# Prompts Claude Code submits on its own. Captured from real hook input on 2.1.289: task-notification,
# cross-session-message (carries attributes) and the built in autonomous loop prompt.
SYSTEM_PROMPT = re.compile(r"^\s*(<(task-notification|command-name|command-message|command-args|"
                           r"local-command-stdout|local-command-stderr|bash-input|bash-stdout|bash-stderr|"
                           r"user-memory-input|system-reminder|cross-session-message|teammate-message|channel)[\s>]"
                           r"|# Autonomous loop check\b)")
OVERRIDES = {"!fast": "fast", "!std": "standard", "!deep": "deep", "!max": "max"}


def load_config():
    cfg = json.loads(json.dumps(DEFAULTS))
    try:
        for k, v in json.loads(CONFIG_PATH.read_text()).items():
            cfg[k] = {**cfg[k], **v} if isinstance(v, dict) and isinstance(cfg.get(k), dict) else v
    except Exception:
        pass
    return cfg


MAX_ANALYZE = 8000   # instructions sit at the start and end; bound the work for huge pastes


def split(prompt):
    """Return (instruction_text, payload_chars)."""
    payload = 0
    if len(prompt) > 4 * MAX_ANALYZE:
        payload = len(prompt) - MAX_ANALYZE
        prompt = prompt[: MAX_ANALYZE // 2] + "\n\n" + prompt[-MAX_ANALYZE // 2 :]
    def fence(m):
        nonlocal payload
        payload += len(m.group(0))
        return "\n"
    text = re.sub(r"```.*?(```|\Z)", fence, prompt, flags=re.S)

    # line level: runs of 3+ code/log/data lines are payload
    lines, keep, run = text.splitlines(), [], []
    def flush():
        nonlocal payload
        if len(run) >= 3:
            payload += sum(len(l) for l in run)
        else:
            keep.extend(run)
        run.clear()
    for line in lines:
        if line.strip() and DATA_LINE.search(line[:400]):
            run.append(line)
        else:
            flush()
            keep.append(line)
    flush()
    text = "\n".join(keep).strip()

    # pasted document: short head/tail with a cue, long middle
    if len(text) > 700:
        paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
        head_lines = text.splitlines()
        head = ""
        for i, l in enumerate(head_lines[:3]):
            if l.rstrip().endswith(":") and len("\n".join(head_lines[: i + 1])) <= 400:
                head = "\n".join(head_lines[: i + 1])
                break
        if not head and paras and len(paras[0]) <= 400:
            head = paras[0]
        tail = paras[-1] if len(paras) > 1 and len(paras[-1]) <= 400 else ""
        if not tail and head_lines and len(head_lines[-1]) <= 300 and head_lines[-1].rstrip().endswith("?"):
            tail = head_lines[-1]
        instr = (head + "\n" + tail).strip()
        il = instr.lower()
        if instr and (CUE.search(il) or "?" in tail or hits(FAST, il)):
            payload += len(text) - len(instr)
            text = instr
    return text, payload


def hits(patterns, text):
    return sum(1 for p in patterns if re.search(r"\b" + p + r"\b", text))


def weight(patterns, text):
    return sum(w for p, w in patterns.items() if re.search(r"\b" + p + r"\b", text))


def classify(prompt, cfg):
    low_full = prompt.strip().lower()
    for tag, tier in OVERRIDES.items():
        if low_full.startswith(tag):
            return tier, None, "override", 0

    instr, payload = split(prompt.strip())
    if len(instr) <= 80 and FOLLOWUP.match(instr.strip().lower()):
        # "yes go ahead" after an Opus plan means: implement it here, with full context
        return "standard", None, "followup", payload
    if len(instr) > MAX_ANALYZE:
        payload += len(instr) - MAX_ANALYZE
        instr = instr[: MAX_ANALYZE // 2] + "\n" + instr[-MAX_ANALYZE // 2 :]
    low = NEGATION.sub(" ", instr.lower())
    n = len(instr)

    deep, fast = weight(DEEP, low), hits(FAST, low)
    symptoms = hits(SYMPTOM, low)
    score = deep + 2 * symptoms - fast
    score += (n > 600) + (n > 1500) + (n > 3000)
    score += 1 if len(re.findall(r"^\s*(?:\d+[.)]|[-*•])\s", instr, re.M)) >= 4 else 0
    score += 1 if len(set(re.findall(r"[\w/]+\.(?:py|ts|tsx|js|jsx|cs|go|rs|java|sql|ya?ml)\b", low))) >= 3 else 0

    t = cfg["thresholds"]
    if score >= t["max_score"]:
        tier = "max"
    elif score >= t["deep_score"]:
        tier = "deep"
    elif (fast > 0 and deep == 0 and symptoms == 0 and n <= t["fast_max_chars"]
          and (not SCOPE.search(low) or LOOKUP.match(low.strip()))):
        tier = "fast"                     # strict: Haiku only on clear, small, lookup style work
    else:
        tier = "standard"

    if CONCEPT_Q.match(low.strip()) and n <= 250 and tier in ("deep", "max"):
        tier = "standard"                 # explaining a hard topic is not hard work
    if payload > 0 and tier == "fast":
        tier = "standard"                 # context lives in the prompt; don't delegate
    return tier, score, "heuristic", payload


# Delegation only pays for itself on larger changes: a subagent starts cold and the lead still reviews.
BIG = "the change will likely touch 2 or more files or 50 or more lines"
ASK_ONLY = ("Edit files only if the user asked for a change. If they asked a question or for analysis "
            "(why, how, find the cause, compare options), reply with analysis only and leave files untouched.")


def instructions(tier, cfg):
    opus = cfg["main_model"] == "opus"
    if tier == "fast" and opus:
        return ("[router] tier=fast. Handle it directly and answer tersely. Delegate to the router-fast subagent "
                "(run_in_background: false) only for bulk mechanical work across many files.")
    if tier == "fast":
        return ("[router] tier=fast. If the task needs no context from this conversation, "
                "delegate it to the router-fast subagent with run_in_background: false. Answer tersely.")
    if tier == "standard" and opus:
        return (f"[router] tier=standard. Delegate to the router-sonnet subagent (run_in_background: false) only if {BIG} "
                "and the task does not depend on this conversation; then review its result. Otherwise do it directly.")
    if tier == "standard":
        return ("[router] tier=standard. Handle directly. Be concise. If it proves complex (unclear root "
                "cause, design decision, multi file change), brief the router-deep subagent first "
                "(run_in_background: false).")
    if opus:
        extra = " Think it through thoroughly." if tier == "max" else ""
        return (f"[router] tier={tier}. Handle directly. Read the relevant code first. {ASK_ONLY} "
                "When a change was asked for: plan, edit, then verify with tests or a run. Delegate a clearly "
                f"scoped part to router-sonnet only if {BIG}.{extra}")
    agent = "router-max" if tier == "max" else "router-deep"
    return (f"[router] tier={tier}. Send a complete brief (goal, relevant files, constraints, "
            f"what you already know) to the {agent} subagent with run_in_background: false and wait for its "
            f"plan. {ASK_ONLY} When a change was asked for, implement the plan and verify it yourself.")


def route(tier, cfg):
    if cfg["main_model"] == "opus":
        return {"fast": "Opus main (terse)", "standard": "Opus main, Sonnet subagent for larger changes",
                "deep": "Opus main", "max": "Opus main (thorough)"}[tier]
    return {"fast": "Haiku subagent", "standard": "Sonnet main",
            "deep": "Opus subagent (high)", "max": "Opus subagent (xhigh)"}[tier]


def status_text(cfg):
    lead = "Opus lead" if cfg["main_model"] == "opus" else "Sonnet lead (budget mode)"
    if cfg.get("enabled"):
        return f"🧭 router ON ({lead}). Every prompt is routed. Turn off: /router-off"
    return "🧭 router OFF. Prompts are not routed. A !fast, !std, !deep or !max prefix routes one prompt. Turn on: /router-on"


def set_enabled(value):
    """Persist the switch in config.json, keeping every other key the user set."""
    try:
        raw = json.loads(CONFIG_PATH.read_text())
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}
    raw["enabled"] = value
    ROUTER_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(raw, indent=2) + "\n")


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--on", "--off", "--status"):
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")      # Windows consoles default to a legacy codepage
        if sys.argv[1] != "--status":
            set_enabled(sys.argv[1] == "--on")
        print(status_text(load_config()))
        return
    cfg = load_config()
    if len(sys.argv) > 2 and sys.argv[1] == "--test":
        tier, score, how, payload = classify(" ".join(sys.argv[2:]), cfg)
        print(f"tier={tier} score={score} via={how} payload={payload} route={route(tier, cfg)}")
        return
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(data, dict):
        return
    if os.environ.get("CLAUDE_ROUTER_DEBUG"):
        try:
            ROUTER_DIR.mkdir(parents=True, exist_ok=True)
            with (ROUTER_DIR / "debug.jsonl").open("a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception:
            pass
    prompt = data.get("prompt") or ""
    if not isinstance(prompt, str) or not prompt.strip() or prompt.lstrip().startswith("/"):
        return
    if SYSTEM_PROMPT.match(prompt):
        return        # agent notices, messages from other sessions and loop ticks are not user prompts
    on = bool(cfg.get("enabled"))
    if not on and not prompt.strip().lower().startswith(tuple(OVERRIDES)):
        return        # router is off: no output, no log line

    tier, score, how, payload = classify(prompt, cfg)

    if cfg["log"]:
        try:
            ROUTER_DIR.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a") as f:
                f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "chars": len(prompt),
                                    "payload": payload, "tier": tier, "score": score, "via": how}) + "\n")
        except Exception:
            pass

    label = f"🧭 router ON · {tier} → {route(tier, cfg)}" if on else f"🧭 {tier} → {route(tier, cfg)} (router off, this prompt only)"
    sys.stdout.write(json.dumps({
        "systemMessage": label,
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                               "additionalContext": instructions(tier, cfg)},
    }) + "\n")


if __name__ == "__main__":
    main()
