# Claude Router

**Does routing each Claude Code prompt to Haiku, Sonnet or Opus save money? In our benchmark, no.**

Claude Router is a `UserPromptSubmit` hook that classifies every prompt locally and tells Claude Code which model should do the work, using subagents. We built it, verified that it routes correctly, then measured it against the two things it competes with: Opus alone and Sonnet alone.

Plain Sonnet with no router was the cheapest way to get a passing result. The router did not lower cost with an Opus lead, and made things worse with a Sonnet lead.

The router is still here as an opt in tool, **off by default**, and the benchmark is here so you can rerun it on your own tasks.

| Arm | Passed | Cost | Cost per passed task | Wall time |
|---|---|---|---|---|
| A. Opus, no router | 16/16 | $3.44 | $0.215 | 472 s |
| B. Opus, router | 16/16 | $3.60 | $0.225 | 499 s |
| **C. Sonnet, no router** | **16/16** | **$1.62** | **$0.101** | **317 s** |
| D. Sonnet, router (budget mode) | 14/16 | $2.52 | $0.180 | 570 s |

Measured on 2026-10-04 with Claude Code 2.1.289. Two runs per task per arm, so read every number here as directional.

---

## Contents
1. [Hypothesis](#hypothesis)
2. [Method](#method)
3. [Results](#results)
4. [Why routing lost](#why-routing-lost)
5. [Limitations](#limitations)
6. [Rerun it on your own tasks](#rerun-it-on-your-own-tasks)
7. [The router: an opt in tool](#the-router-an-opt-in-tool)
8. [What we learned about Claude Code](#what-we-learned-about-claude-code)
9. [Testing](#testing)

---

## Hypothesis

Most people leave one model on all day. If a cheap local classifier sent lookups to Haiku, clear work to Sonnet and open ended work to Opus, a session should cost less than Opus alone without losing quality, and should use fewer Opus tokens, which is what counts against subscription limits.

A hook cannot change the session's model or effort, so the router works by telling the lead model to delegate to subagents that pin their own model and effort.

---

## Method

**Tasks.** Eight tasks in a small Node project ([bench/project](bench/project)): 2 fast, 3 standard, 2 deep, 1 max, labeled by the router's own classifier. Each has a hidden automatic check ([bench/checks](bench/checks)) that never enters the working copy during a run. Every check fails on the untouched project and passes on a reference solution.

| Task | Tier | What it asks |
|---|---|---|
| F1 | fast | Rename a function |
| F2 | fast | Say what a function returns for a given input |
| S1 | standard | Add pagination to a list function, with tests |
| S2 | standard | Add a coupon function, with tests |
| S3 | standard | Add a currency argument across three files, with tests |
| D1 | deep | Find and fix lost updates under concurrency |
| D2 | deep | Make a slow report fast without changing its output |
| M1 | max | Find and fix an intermittent deadlock |

**Arms.** A: Opus, no router. B: Opus with the router. C: Sonnet, no router. D: Sonnet with the router in budget mode, where Opus subagents write plans for deep work.

**Conditions.**
* Each arm ran in its own clean HOME with no plugins, no other hooks and no user settings. Both lead models ran at `medium` effort, confirmed from the transcripts.
* `claude -p`, one prompt per session, 2 runs per task per arm: 64 runs.
* Runs were sequential and interleaved per task. The second pass swapped the order within each model pair, so neither arm always ran second.
* Cost and tokens come from the per model usage Claude Code reports for each session (`modelUsage`), at API prices. Prices are from the [official pricing page](https://platform.claude.com/docs/en/about-claude/pricing), read on 2026-10-04:

| Per million tokens | Input | Output | Cache write (1 hour) | Cache read |
|---|---|---|---|---|
| Opus 5.5 | $4 | $20 | $8 | $0.20 |
| Sonnet 5.5 | $2 | $10 | $4 | $0.20 |

---

## Results

All 64 runs finished; none hit a usage or rate limit.

| Arm | Passed | Cost | Cost per passed task | Opus tokens | Opus share of all tokens | Cache read share of input | Wall time |
|---|---|---|---|---|---|---|---|
| A. Opus, no router | 16/16 | $3.44 | $0.215 | 2,099,385 | 100% | 86% | 472 s |
| B. Opus, router | 16/16 | $3.60 | $0.225 | 1,831,017 | 86% | 84% | 499 s |
| C. Sonnet, no router | 16/16 | $1.62 | $0.101 | 0 | 0% | 86% | 317 s |
| D. Sonnet, router | 14/16 | $2.52 | $0.180 | 693,391 | 28% | 85% | 570 s |

**Variance between the two passes**

| Arm | Cost, pass 1 / pass 2 | Cost per passed task, pass 1 / pass 2 | Opus tokens, pass 1 / pass 2 |
|---|---|---|---|
| A | $1.61 / $1.82 | $0.201 / $0.228 | 871,571 / 1,227,814 |
| B | $1.78 / $1.82 | $0.222 / $0.227 | 896,631 / 934,386 |
| C | $0.78 / $0.83 | $0.098 / $0.104 | 0 / 0 |
| D | $1.22 / $1.30 | $0.174 / $0.186 | 278,318 / 415,073 |

**Reading the numbers**

* **Best cost per passed task: plain Sonnet (C)**, at $0.098 to $0.104, with every run passing. That is about half of either Opus arm.
* **Router with an Opus lead (B against A): no saving.** B cost $0.16 more than A. A's own two passes differ by $0.21, so the arms cannot be told apart on cost.
* **Opus tokens (B against A): not established.** B used 13% fewer Opus tokens in total, but A alone moved 41% between its two passes.
* **Router with a Sonnet lead (D against C): worse on every measure.** 56% more cost, 80% more wall time, two failures, and 693,391 Opus tokens where plain Sonnet used none.

**The two failures.** Both are arm D on the rename task. The Haiku subagent renamed the function in the file the prompt named, and the Sonnet lead saw that a test still used the old name and asked whether to fix it rather than fixing it. The project's own test suite was left failing. The other three arms updated the test in all six runs. The prompt did say "in api.js", so this is a strict check; counting both as passes would make D 16/16 at $0.158 per passed task, still well behind C.

Full per task table, per model tokens and routing observed in each run: [bench/results/report.md](bench/results/report.md). Raw rows: [bench/results/results.jsonl](bench/results/results.jsonl).

---

## Why routing lost

**1. A small task's cost is mostly the session's own startup, and routing cannot shrink it.**
Cache writes were 62 to 69% of cost in every arm. Each session writes its system prompt and tool definitions to the prompt cache: about 17,900 tokens per run in arm A and 16,000 in arm C. For arm A that is roughly $0.14 of the $0.215 average run. The lead model pays this whatever the router decides.

**2. A subagent starts cold, so delegation adds a second startup instead of replacing the first.**
On the one task where the Opus lead delegated to Sonnet (S3, three files), the Opus side still cost $0.19 and the Sonnet subagent added $0.13 to $0.14, for $0.32 to $0.33 against $0.26 without the router. The subagent wrote 20,489 to 27,509 tokens of its own to the cache.

**3. Cache reads cost the same on Opus and Sonnet.**
Cache reads were 83 to 88% of input tokens in every arm, and both models charge $0.20 per million for them. Moving work to Sonnet saves nothing on the largest category of tokens. The saving that does exist, half price output and cache writes, is what plain Sonnet already gets in full.

**4. Planning with Opus from a Sonnet lead is the expensive direction.**
In budget mode the Opus planner alone cost $0.14 to $0.28 per run. The deadlock task cost $0.31 and $0.37 with it, against $0.10 and $0.10 for plain Sonnet, which also passed.

**5. Haiku was not cheap in practice.**
In an earlier end to end test with the first version of the routing rules, the Haiku subagent made 14 and 18 API calls to rename one symbol in two files. Those runs cost $0.21 in a clean config and $0.33 in a full one. The rules now keep fast work in the main session under an Opus lead.

**6. Sonnet passed everything.**
Sonnet alone passed all 16 runs, including the deep and max tasks. On these tasks there was no quality gap for Opus to close, so every dollar of Opus was overhead.

---

## Limitations

* **Small sample.** 8 tasks, 2 runs each. Conclusions are directional.
* **The tasks did not separate the models.** No task was hard enough for Sonnet to fail. Whether sending hard work to Opus improves quality when Sonnet would fail is untested, and it is the one case where a router could still pay.
* **Small, single prompt tasks.** Long sessions with large contexts and real design work were not measured. Startup cost matters less there.
* **Clean config only.** In a separate test with 18 plugins and `xhigh` effort, the same prompts cost 1.6 to 2.4 times more per call. That setup was not benchmarked.
* **Headless only.** Everything ran under `claude -p`. In interactive sessions Claude Code runs subagents in the background, which this harness cannot reproduce.
* **API prices, one day, one version.** Costs are notional API prices on 2026-10-04 with Claude Code 2.1.289. Subscription limits are metered differently; during the 31 minute run the account's 5 hour utilization moved from 29% to 44%, which includes other usage in that window.
* **The classifier is imperfect.** It scores 89% on its most honest holdout set; see [Testing](#testing).
* **One strict check.** See the two failures above.

---

## Rerun it on your own tasks

```bash
python3 bench/run.py --home-root /tmp/claude-router-bench/arms --out bench/results --cap-total 12 --link-keychain
python3 bench/report.py bench/results/results.jsonl
```

This calls real models: the published run cost $11.17 at API prices. `--cap-total` stops new runs once that much is spent.

To use your own project, tasks, checks or arms, follow [bench/README.md](bench/README.md). If your tasks are hard enough that Sonnet fails some of them, you will be testing the case this benchmark could not.

---

## The router: an opt in tool

Given the results, the router ships **off**. It stays installed and silent until you switch it on, or prefix a single prompt.

### Install

Requires Claude Code and Python 3.8+. Developed and tested on macOS.

```bash
git clone https://github.com/<your-username>/claude-router.git
cd claude-router
python3 install.py
```

The installer:
* copies the hook to `~/.claude/router/`, four agents to `~/.claude/agents/` and three commands to `~/.claude/commands/`
* adds one `UserPromptSubmit` hook to `~/.claude/settings.json`, keeping your other hooks and settings
* saves the original as `settings.json.bak` once, and keeps it across reruns
* adds a short protocol block to `~/.claude/CLAUDE.md`
* starts **off**; a rerun keeps whatever you set
* refuses to touch anything if your `settings.json` is not valid JSON

**Uninstall:** `python3 install.py --uninstall` removes everything it added.

### Switch it on and off

| In Claude Code | In a terminal | Effect |
|---|---|---|
| `/router-on` | `python3 ~/.claude/router/router.py --on` | Route every prompt |
| `/router-off` | `python3 ~/.claude/router/router.py --off` | Stop routing |
| `/router-status` | `python3 ~/.claude/router/router.py --status` | Show the current state |

The switch is stored in `~/.claude/router/config.json` and persists across sessions. The slash commands each take one model turn to echo the result; the terminal form is free.

While it is on, every prompt shows a status line so you cannot forget it is running:

```
🧭 router ON · standard → Opus main, Sonnet subagent for larger changes
```

While it is off, the hook prints nothing and logs nothing.

### Route one prompt without switching it on

Start a prompt with a tier. This works whether the router is on or off:

| Prefix | Effect |
|---|---|
| `!fast` | Fast tier |
| `!std` | Standard tier |
| `!deep` | Deep tier |
| `!max` | Max tier, thorough |

```
> !deep add a retry to fetchPrices
🧭 deep → Opus main (router off, this prompt only)
```

### What each tier does

| Tier | Opus lead (default) | Sonnet lead (budget mode) |
|---|---|---|
| fast | Opus answers directly and tersely. Haiku subagent only for bulk mechanical work | Haiku subagent |
| standard | Opus does it directly. Sonnet subagent (effort high) only if the change likely touches 2+ files or 50+ lines | Sonnet does it directly |
| deep | Opus directly. Analysis only unless you asked for a change | Opus subagent (effort high) writes a plan, Sonnet implements |
| max | As deep, told to think thoroughly | Opus subagent (effort xhigh) writes a plan, Sonnet implements |

In the benchmark the Opus lead followed these rules in 16 of 16 runs. The Sonnet lead followed them in 13 of 16: it skipped the Haiku delegation once and the Opus planner twice.

### How it classifies

```
your prompt
   │
   ▼
UserPromptSubmit hook  (local Python, no API call)
   │  1. split: what you wrote  vs  what you pasted (logs, code, JSON, CSV, docs)
   │  2. score only what you wrote: complexity words, bug symptoms, ambiguity, scope
   │  3. pick a tier: fast | standard | deep | max
   ▼
one instruction injected into the turn  +  a status line shown to you
```

* Pasted content is not treated as complexity, and a prompt with pasted content never goes to the fast tier.
* Follow ups such as `yes go ahead` are classified standard, never fast.
* Agent completion notices, slash commands, messages from other sessions and built in autonomous loop ticks are ignored. A prompt you scheduled yourself (`/loop 5m ...` or a cron task) arrives as plain text and is routed like a typed prompt each time it fires.
* The hook never blocks a prompt; on any error it stays silent.

Check a prompt without running it:

```bash
python3 ~/.claude/router/router.py --test "your prompt here"
# tier=standard score=0 via=heuristic payload=0 route=Opus main, Sonnet subagent for larger changes
```

### Configuration

`~/.claude/router/config.json`

```json
{
  "enabled": false,
  "main_model": "opus",
  "thresholds": { "fast_max_chars": 160, "deep_score": 3, "max_score": 6 },
  "log": true
}
```

| Key | Meaning |
|---|---|
| `enabled` | The on/off switch. Default `false`. |
| `main_model: "opus"` | Opus leads. Start Claude Code with `claude --model opus`. |
| `main_model: "sonnet"` | Budget mode: Sonnet leads and Opus subagents plan deep work. Start with `claude --model sonnet`. It lost to plain Sonnet in the benchmark. |
| `fast_max_chars` | Longest prompt the fast tier may take. |
| `deep_score`, `max_score` | Scores that send work to the deep and max tiers. Lower sends more. |
| `log` | Write tier, score and length for each routed prompt to `~/.claude/router/log.jsonl`. Prompt text is never stored. |

`CLAUDE_ROUTER_DEBUG=1` writes the raw hook input, including prompt text, to `~/.claude/router/debug.jsonl`.

### claude.ai (web, desktop, mobile)

Hooks do not exist there. [web/claude-ai-router.md](web/claude-ai-router.md) is a short block for your profile preferences that asks Claude to flag a model mismatch in one line, so you can switch by hand. It was not part of the benchmark.

---

## What we learned about Claude Code

Verified on 2.1.289 by reading the API requests Claude Code sent to a mock server, and from real session transcripts. Details in [docs/TESTING.md](docs/TESTING.md).

* **A hook cannot change the model or effort.** `UserPromptSubmit` output has no field for either. Subagents with `model` and `effort` frontmatter are the mechanism that works.
* **A top level `effortLevel` in user settings is ignored by Opus 5.5 and Sonnet 5.5.** Requests stayed at `medium`. The key that works is per model: `modelSettings.claude-opus-5-5.effortLevel`. It is read when a session starts; editing it mid session changed nothing.
* **Haiku 4.5 takes no effort setting.** Requests to it carry no effort field.
* **Foreground delegation only happens under `claude -p`.** Interactive sessions run subagents in the background and remove the `run_in_background` parameter, per the official docs.
* **Other things arrive through `UserPromptSubmit`.** Agent completions come as `<task-notification>`, messages from other sessions as `<cross-session-message ...>`, and autonomous `/loop` ticks as built in text. A hook that treats them as user prompts will route them.
* **Session cost and tokens are in the transcript.** The `cost-state` record carries the same per model usage `claude -p` reports. Summing per message usage undercounts subagent output tokens. [bench/usage.py](bench/usage.py) reads it.

---

## Testing

`bash tests/run_all.sh` runs everything and exits nonzero on any failure.

| Suite | Result |
|---|---|
| Classification, tuning set (70 prompts) | 99%, gate 95% |
| Holdout 1 (45 prompts, later tuned against) | 100%, gate 85% |
| Holdout 2 (44 prompts, closest to real use) | 89%, gate 85%; first unseen run was 75% |
| Complex tasks routed to the fast tier | 0 in every set |
| On/off switch, prefixes, installer | 22 checks pass |
| Bad input, non user prompts, 40 parallel sessions | All pass |
| Performance, inputs up to 5 MB | Worst case 87 to 181 ms across runs |

The routes were also verified end to end with real models: one prompt per tier, in a clean HOME and in a full user config. Method and findings are in [docs/TESTING.md](docs/TESTING.md); history is in [CHANGELOG.md](CHANGELOG.md).

---

## License

MIT © 2026 Shaaz Khan
