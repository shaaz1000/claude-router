# Testing

Run everything: `bash tests/run_all.sh`

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

## 2. Robustness (`tests/robustness.sh`)
* Empty, garbage, non object and non string input: exit 0, no output
* Nonexistent working directory: no directories created
* Project `settings.local.json`: never modified
* Agent completion notices and slash commands: ignored
* 40 parallel sessions: all log lines valid, no prompt text stored

## 3. Performance (`tests/perf.py`)
Inputs up to 5 MB, including pathological regex inputs. Budget 1 s; hook timeout is 5 s. Worst observed: about 120 ms.

## 4. End to end in real Claude Code (`tests/e2e/`)
`mock_api.py` imitates the Anthropic Messages API, logs every request, approves auto mode safety checks, and can script one Agent tool call. Point Claude Code at it:

```bash
MOCK_SCRIPT=agent:router-sonnet MOCK_LOG=/tmp/req.jsonl python3 tests/e2e/mock_api.py 8787 &
ANTHROPIC_BASE_URL=http://127.0.0.1:8787 ANTHROPIC_API_KEY=sk-ant-test \
  claude -p "add pagination to the orders endpoint with tests" --model opus
python3 tests/e2e/check.py /tmp/req.jsonl
```

## Findings from Claude Code 2.1.289
| Finding | Consequence |
|---|---|
| `UserPromptSubmit` output supports only `additionalContext` and `sessionTitle` | Hooks cannot change the model; routing uses subagents |
| `effortLevel` is read only at session start (tested headless and interactive) | Per prompt effort is set through subagent `effort:` frontmatter |
| Agent `effort:` frontmatter is honored | Sonnet subagent runs at high, Opus planners at high or xhigh |
| Agents run in the background by default | Router asks for `run_in_background: false` |
| Agent completion notices arrive through `UserPromptSubmit` | Router ignores them to avoid delegation loops |
| Subagents inherit session effort unless pinned | `router-sonnet` pins `effort: high` (Sonnet 5.5's documented default) |
