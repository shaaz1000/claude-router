# 🧭 Claude Router

**Automatic model and effort routing for Claude Code.**
Every prompt is classified locally in about 40 ms, at zero token cost, and sent to the right model: Haiku for lookups, Sonnet for clear everyday work, Opus for complex work that is still taking shape.

Built on Anthropic's own guidance for the Claude 5.5 family: *Sonnet 5.5 for everyday work you can clearly describe, Opus 5.5 for complex work that's still taking shape, and Opus can delegate the clear parts to Sonnet.*

```
🧭 fast → Haiku subagent
🧭 standard → Sonnet subagent or Opus main
🧭 deep → Opus main
```

---

## Contents
1. [Why](#why)
2. [Before and after](#before-and-after)
3. [How it works](#how-it-works)
4. [Install](#install)
5. [How to use it](#how-to-use-it)
6. [Configuration](#configuration)
7. [claude.ai (web, desktop, mobile)](#claudeai-web-desktop-mobile)
8. [How it was tested](#how-it-was-tested)
9. [Limitations](#limitations)
10. [Roadmap: making it better](#roadmap-making-it-better)

---

## Why

Picking a model by hand for every prompt is tedious, so most people leave one model on all day. That means either paying Opus prices to rename a variable, or asking Sonnet to untangle an architecture problem it should not own.

Claude Router makes that choice for you on every prompt, and you can override it with one word.

---

## Before and after

### Without the router
| You type | What runs | Problem |
|---|---|---|
| `rename getUser to fetchUser` | Your session model (often Opus) | Premium model on trivial work |
| 300 line log + "which line has 10:42?" | Your session model | Fine, but nothing stops you overpaying |
| `not sure how to structure billing` | Sonnet, if you left it on Sonnet | Open ended judgment on the cheaper model |
| Every prompt | Same effort level | Effort never matches the task |

### With the router (default mode)
| You type | Tier | What runs |
|---|---|---|
| `rename getUser to fetchUser` | fast | **Haiku 4.5** subagent |
| `add pagination to /orders with tests` | standard | **Sonnet 5.5** subagent (effort high), Opus reviews |
| 300 line log + "which line has 10:42?" | standard | Pasted content is not treated as complexity |
| `not sure how to structure billing` | deep | **Opus 5.5** main session |
| `find the root cause of the deadlock` | max | **Opus 5.5**, told to think thoroughly |
| `yes go ahead` | standard | Stays in main session, which holds the context |

### Project history: v1 → v4
| Version | Change | Why |
|---|---|---|
| v1 | Keyword scorer that rewrote `effortLevel` per prompt | First attempt |
| v2 | Separated what you **wrote** from what you **pasted** | v1 sent a 300 line log with a trivial question to Opus at max effort |
| v2 | Haiku became strict opt in; plain English symptom words added | Fresh test set exposed real bugs routed to Haiku |
| v3 | Dropped per prompt effort switching; routing moved to subagents | Tested inside Claude Code 2.1.289: `effortLevel` is read only at session start |
| v3 | Ignores agent completion notices; agents run in foreground | Found a possible delegation loop in real Claude Code |
| v4 | **Opus leads, Sonnet executes** became the default | Matches Anthropic's Sonnet 5.5 guidance |
| v4 | "Work still taking shape" signals route to Opus | `not sure how`, `best way to`, `pros and cons`, `should we use` |

Full details: [CHANGELOG.md](CHANGELOG.md).

---

## How it works

```
your prompt
   │
   ▼
UserPromptSubmit hook  (local Python, ~40 ms, no API call)
   │  1. split: what you wrote  vs  what you pasted (logs, code, JSON, CSV, docs)
   │  2. score only what you wrote: complexity words, bug symptoms, ambiguity, scope
   │  3. pick a tier: fast | standard | deep | max
   ▼
one line instruction injected into the turn  +  status line shown to you
   │
   ▼
main session follows it: handle directly, or delegate to a subagent
   ├── router-fast    Haiku            lookups, renames, small edits
   ├── router-sonnet  Sonnet, high     clear, self contained work
   ├── router-deep    Opus, high       plans (budget mode only)
   └── router-max     Opus, xhigh      plans (budget mode only)
```

**Why subagents?** In Claude Code 2.1.289, a hook cannot change the session model, and `effortLevel` is read only when a session starts. Subagents carry their own `model` and `effort`, so they are the one mechanism that genuinely switches both per task. This was verified by inspecting real API requests.

**Safety rules built in**
* Haiku only gets short, clear, lookup style work with no bug symptoms and no bulk scope.
* Prompts containing pasted content never go to Haiku, because the context lives in your message.
* Follow ups (`yes go ahead`, `continue`) always stay in the main session.
* Agent completion notices and slash command output are ignored, which prevents delegation loops.
* The hook never blocks a prompt; on any error it stays silent.

---

## Install

Requires Claude Code and Python 3.8+. Works on macOS, Linux and Windows.

```bash
git clone https://github.com/<your-username>/claude-router.git
cd claude-router
python3 install.py
```

The installer:
* copies the hook to `~/.claude/router/` and four agents to `~/.claude/agents/`
* adds one `UserPromptSubmit` hook to `~/.claude/settings.json` (backup saved as `settings.json.bak`)
* adds a short protocol block to `~/.claude/CLAUDE.md`
* keeps your existing hooks, permissions and rules, and is safe to rerun
* refuses to touch anything if your `settings.json` is invalid

Then restart Claude Code with the lead model:

```bash
claude --model opus
```

**Uninstall:** `python3 install.py --uninstall` removes everything it added.

---

## How to use it

Just work normally. Each prompt shows where it went:

```
> rename user_name to userName in profile.ts
🧭 fast → Haiku subagent
```

### Override when it guesses wrong
Start a prompt with a tier:

| Prefix | Effect |
|---|---|
| `!fast` | Force Haiku |
| `!std` | Force standard |
| `!deep` | Force Opus |
| `!max` | Force Opus, thorough |

```
> !deep add a retry to fetchPrices
```

### Check a prompt without running it
```bash
python3 ~/.claude/router/router.py --test "your prompt here"
# tier=standard score=0 via=heuristic payload=0 route=Sonnet subagent or Opus main
```

### Review your routing
`~/.claude/router/log.jsonl` records tier, score and length for every prompt. It **never** stores prompt text.

### Debug
```bash
CLAUDE_ROUTER_DEBUG=1 claude --model opus
# raw hook input goes to ~/.claude/router/debug.jsonl
```

---

## Configuration

`~/.claude/router/config.json`

```json
{
  "main_model": "opus",
  "thresholds": { "fast_max_chars": 160, "deep_score": 3, "max_score": 6 },
  "log": true
}
```

| Key | Meaning |
|---|---|
| `main_model: "opus"` | **Default.** Opus leads; clear work goes to Sonnet. Best quality per Anthropic's guidance. |
| `main_model: "sonnet"` | **Budget mode.** Sonnet leads; Opus subagents write plans for deep work. Start with `claude --model sonnet`. |
| `fast_max_chars` | Longest prompt Haiku may take. Lower is safer. |
| `deep_score` | Score that sends work to Opus. Lower sends more to Opus. |
| `max_score` | Score for the thorough tier. |

**Choosing a mode:** Opus 5.5 costs about twice Sonnet 5.5 per token ($4/$20 vs $2/$10 per million). Opus lead is better for long sessions with real design work; Sonnet lead is cheaper for mostly routine coding.

---

## claude.ai (web, desktop, mobile)

claude.ai cannot switch its own model, so the router cannot run there. Instead, `web/claude-ai-router.md` contains a short block to paste into **Settings → Profile preferences** or a Project's instructions. Claude then flags a mismatch in one line, for example `⚙ Better fit: Opus, extended thinking on`, and you switch manually.

---

## How it was tested

`bash tests/run_all.sh` runs everything below. Details in [docs/TESTING.md](docs/TESTING.md).

| Suite | Result |
|---|---|
| Classification, set used for tuning (70 prompts) | 99% |
| Holdout 1 (45 prompts, later tuned against) | 100% |
| **Holdout 2 (44 prompts, closest to real world)** | **89%**, misses lean to Sonnet, never Haiku |
| Bad input, corrupt files, 40 parallel sessions | All pass |
| Performance, up to 5 MB and adversarial inputs | Worst case 120 ms |
| **End to end in real Claude Code 2.1.289** | All routes verified from actual API requests |

End to end results (mock API, real Claude Code binary):

| Mode | Prompt | Request went to |
|---|---|---|
| Opus lead | rename foo to bar | `claude-haiku-4-5` |
| Opus lead | add pagination with tests | `claude-sonnet-5-5`, effort high |
| Opus lead | not sure how to structure billing | `claude-opus-5-5` main |
| Sonnet lead | redesign the caching layer | `claude-opus-5-5`, effort high |
| Sonnet lead | find the root cause of the deadlock | `claude-opus-5-5`, effort xhigh |

---

## Limitations

* **Keyword classification is roughly 85 to 90% accurate** on unseen prompts. Use the `!` prefixes when it is wrong.
* **Subagents start with a fresh context.** Their quality depends on the brief the lead writes.
* **Tests prove the plumbing, not model judgment.** The mock API returns scripted answers, so whether a real model follows each instruction perfectly was not measured.
* **Auto mode adds one small safety check request** per delegation.
* **Sonnet 5.5 may fall back to Sonnet 5** on higher risk cybersecurity tasks, per public reporting. Use `!deep` for security work.
* **Claude Code internals change.** Facts here were verified on 2.1.289.

---

## Roadmap: making it better

Ordered by expected impact.

1. **Optional Haiku classifier for uncertain prompts.** Call Haiku only when the keyword score sits near a threshold. This costs roughly a few hundred tokens per uncertain prompt and should lift accuracy well above 90%.
2. **Learn from your overrides.** Every `!deep` or `!fast` is a labeled correction. Log them (without prompt text, or with opt in) and suggest threshold changes.
3. **Conversation aware routing.** Read recent turns from the transcript so a short prompt in the middle of an architecture discussion is not treated as trivial.
4. **Native effort switching.** If Claude Code exposes effort or model changes to hooks, route the main session directly instead of through subagents.
5. **Cost dashboard.** Turn `log.jsonl` into a weekly report: prompts per tier and estimated savings.
6. **Project profiles.** Per repository thresholds, for example always deep in a payments service.
7. **Haiku 5.5.** When it ships, the `haiku` alias picks it up automatically; the fast tier can then safely take more work.

Contributions welcome. Please add a labeled case to `tests/cases.py` for any routing bug you report.

---

## License

MIT © 2026 Shaaz Khan
