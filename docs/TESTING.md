# Testing

Run everything: `bash tests/run_all.sh`

The script exits nonzero if any suite fails. Gates: tuned set at least 95%, each holdout at least 85%, zero complex (deep or max) tasks routed to fast, every robustness check, and the performance budget.

## 1. Classification
Labeled prompts, each with a set of acceptable tiers. Errors are split into:
* **COSTLY**: routed higher than needed (wastes tokens)
* **QUALITY RISK**: routed lower than needed

| File | Prompts | Notes |
|---|---|---|
| `tests/cases.py` | 70 | Used during tuning. Includes big pastes with simple asks, traps, ambiguity, overrides |
| `tests/holdout.py` | 45 | Written as a holdout, then used for tuning |
| `tests/holdout2.py` | 44 | Most honest estimate. Includes follow ups, Hinglish, typos, mixed tasks |

Honest reading: the first unseen run of holdout 2 scored **75%**. General fixes raised it to 89%, but it has now influenced tuning, so expect **roughly 85 to 90%** on your own prompts. Since v2, no real task has been routed to Haiku in any test set.

## 2. On/off switch (`tests/toggle.py`)
The router ships off. 22 checks in a temporary HOME:
* Off: a normal prompt produces no output, no log line and no router directory
* Off: a `!fast`, `!std`, `!deep` or `!max` prefix routes that one prompt, is logged once, and the next prompt is silent again
* `--on`: prompts are routed, the status line starts with `router ON`, and a new process still sees it on
* `--off`: silent again; other config keys survive toggling
* Installer: fresh install is off, three commands are written with the real hook path, a rerun keeps the user's setting, uninstall removes everything

The same behaviour was checked inside Claude Code 2.1.289 against the mock API, in separate `claude -p` sessions: off gave no router context, `!deep` gave it for one prompt, `/router-on` switched it on and two later sessions were routed, `/router-off` switched it off and the next session was not. The three commands were not tried in an interactive session.

## 3. Robustness (`tests/robustness.sh`)
* Empty, garbage, non object and non string input: exit 0, no output
* Nonexistent working directory: no directories created
* Project `settings.local.json`: never modified
* Agent completion notices, slash commands, cross session messages and autonomous loop ticks: ignored
* A scheduled user prompt (cron task or `/loop` wakeup): routed like a typed prompt, because Claude Code delivers it as plain text with nothing that marks it as scheduled
* 40 parallel sessions: all log lines valid, no prompt text stored

## 4. Performance (`tests/perf.py`)
Inputs up to 5 MB, including pathological regex inputs. Budget 1 s; hook timeout is 5 s. Worst observed across five runs on one machine: 87 to 181 ms.

## 5. End to end in real Claude Code (`tests/e2e/`)
`mock_api.py` imitates the Anthropic Messages API, logs every request, approves auto mode safety checks, and can script one Agent tool call. Switch the router on (`python3 ~/.claude/router/router.py --on`), then point Claude Code at the mock:

```bash
MOCK_SCRIPT=agent:router-sonnet MOCK_LOG=/tmp/req.jsonl python3 tests/e2e/mock_api.py 8787 &
ANTHROPIC_BASE_URL=http://127.0.0.1:8787 ANTHROPIC_API_KEY=sk-ant-test \
  claude -p "add pagination to the orders endpoint with tests" --model opus
python3 tests/e2e/check.py /tmp/req.jsonl
```

## 6. Real models, one prompt per tier
Run on 2026-10-04 with the first version of the v5 routing rules (before delegation was made concrete), once in a full user config with 18 plugins and once in a clean HOME. Model and effort were read from the session transcripts.

| Tier | Config | Handled by | Route | Cost | Wall |
|---|---|---|---|---|---|
| fast | full | `router-fast` on `claude-haiku-4-5` | pass | $0.33 | 113 s |
| fast | clean | `router-fast` on `claude-haiku-4-5` | pass | $0.21 | 47 s |
| standard | full | `router-sonnet` on `claude-sonnet-5-5`, effort high | pass | $0.50 | 122 s |
| standard | clean | Opus main, did not delegate | fail | $0.27 | 45 s |
| deep | full | Opus main | pass | $0.40 | 71 s |
| deep | clean | Opus main | pass | $0.20 | 31 s |
| max | full | Opus main; also edited files when asked only for a root cause | pass | $0.48 | 107 s |
| max | clean | Opus main | pass | $0.20 | 35 s |

These runs led to the current rules: concrete delegation thresholds, no Haiku delegation from an Opus lead, and analysis only for questions. In the full config the lead ran at `xhigh` effort; no other `UserPromptSubmit` hook added context, and one plugin's `SessionStart` hook added 3,405 characters.

## 7. Savings benchmark (`bench/`)
See the main README and `bench/README.md`.

## Findings from Claude Code 2.1.289
| Finding | Consequence |
|---|---|
| `UserPromptSubmit` output supports `decision`, `reason`, `additionalContext`, `sessionTitle`, `suppressOriginalPrompt`, plus the universal fields (`continue`, `systemMessage` and so on). None of them sets the model or effort | Hooks cannot change the model; routing uses subagents |
| A saved effort level is read only at session start. Editing `settings.json` between turns of a live `claude -p` session changed nothing on Sonnet 5.5 or Opus 5.5; a new session picked the change up | Per prompt effort is set through subagent `effort:` frontmatter |
| For Sonnet 5.5 and Opus 5.5, a top level `effortLevel` in user settings is ignored (requests stayed at `medium`). The key that works is `modelSettings.<model>.effortLevel`, for example `modelSettings.claude-opus-5-5.effortLevel` | To raise the lead's effort, set the per model key or start with `--effort` |
| Agent `effort:` frontmatter is honored | Sonnet subagent runs at high, Opus planners at high or xhigh |
| Agents run in the background by default. Under `claude -p` the Agent tool accepts `run_in_background: false`. Interactive sessions always run them in the background and remove that parameter (per the official docs; not reproducible with our headless harness) | Router asks for `run_in_background: false`, which only takes effect under `-p` |
| Agent completion notices arrive through `UserPromptSubmit` as `<task-notification>` | Router ignores them to avoid delegation loops |
| A message from another session arrives as `<cross-session-message from=... from-name=... from-mode=...>` | Router ignores it |
| A cron task or `/loop` wakeup arrives as the bare prompt text, with no wrapper and no extra hook input field | Router cannot tell it from a typed prompt and routes it |
| An autonomous `/loop` tick arrives as built in text starting `# Autonomous loop check` | Router ignores it (before this fix it was routed as max on every tick) |
| Subagents inherit session effort unless pinned | `router-sonnet` pins `effort: high` as a quality choice. Sonnet 5.5's own default is `medium` |
| Haiku 4.5 does not support effort; requests to it carry no effort field | `router-fast` sets no `effort:` |
| Under auto mode the classifier evaluates each subagent tool call and reviews the subagent's work and final report | A delegation costs more than one extra request in auto mode |
