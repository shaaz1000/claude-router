# Savings benchmark

Runs a set of tasks through several arms (a model, with or without the router), checks every result automatically, and reports cost, tokens, pass rate and wall time per arm. The results of the published run are in [results/report.md](results/report.md) and discussed in the main [README](../README.md).

## Run the published benchmark

```bash
python3 bench/run.py --home-root /tmp/claude-router-bench/arms --out bench/results --cap-total 12 --link-keychain
python3 bench/report.py bench/results/results.jsonl
```

* **This calls real models.** The full 64 runs cost $11.17 at API prices on 2026-10-04 and took 31 minutes. On a subscription the same runs draw on your usage limits.
* `--cap-total` stops new runs once that many dollars are spent. `--cap-run` (default $0.60) limits one run; the published run used `--cap-run 1.00`.
* Each arm runs in its own clean HOME under `--home-root`, so your own config, plugins and hooks are not involved. That directory is wiped for each arm.
* `--link-keychain` is for macOS with a subscription login: it symlinks your login keychain into each clean HOME so it can authenticate. Nothing is copied. Delete the home root when you are done. With `ANTHROPIC_API_KEY` set you do not need it.
* Runs are sequential and interleaved per task. Even passes swap neighbouring arms, so no arm always runs second on a warm prompt cache.
* A usage limit, rate limit, API error or timeout is recorded as `INFRA FAIL`, not a task failure, and pauses the benchmark. Continue with `--resume --already-spent <dollars>`.

## Security

* **The agent can run code as you.** The default permissions let it run `node` and `npm test`, which is arbitrary code execution, and with `--link-keychain` its HOME can reach your Claude login; the environment scrub does not cover that. Only run projects and tasks you wrote or have read. For anything you do not fully trust, run the benchmark in a container or VM with a throwaway API key.
* **A task's `check` is a shell command.** A tasks file from someone else can run anything on your machine. Read it first.
* **Checks execute code the model wrote.** They run with an empty HOME and without the keychain link.
* **Your shell's secrets are withheld.** The agent and the checks receive only a short allowlist of environment variables (`PASS_ENV` in `run.py`); cloud keys and tokens in your shell are not passed. `ANTHROPIC_API_KEY`, if set, goes to the `claude` process only, and the runner sets `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` so the commands the agent runs do not see it.
* `--allowed-tools` replaces the default permission rules. Keep it as narrow as your tasks allow.

## Plug in your own tasks

A task is a prompt plus a check. Three things to provide:

**1. A project.** Any directory. It is copied fresh and committed to a new git repo for every run. Pass it with `--project path/to/project`.

**2. A tasks file.** Pass it with `--tasks-file`. `tier` is only a label for the report.

```json
[
  {"id": "T1", "tier": "standard", "prompt": "add input validation to createUser in users.py, with tests"},
  {"id": "T2", "tier": "deep", "prompt": "figure out why the export job double counts refunds and fix it",
   "check": "python3 \"$BENCH_CHECKS/T2.py\""}
]
```

**3. A check per task.** A check is a command that runs in the working copy after the run and exits 0 on pass.
* Default: `node <checks dir>/<task id>.js`. Pass the directory with `--checks`.
* For anything else, give the task a `check` command. It runs through the shell with the working copy as the current directory.
* `BENCH_CHECKS` is the checks directory. `BENCH_REPLY` is a file holding the model's final reply, for tasks whose answer is text ([checks/F2.js](checks/F2.js) is an example).
* Keep checks outside the project directory so the model never sees them.

Before spending anything, confirm each check fails on the untouched project and passes on a solution you wrote yourself. A check that cannot fail, or cannot pass, tells you nothing.

If your tasks need tools beyond the default (node, `npm test`, read only git and shell commands), pass `--allowed-tools` with [permission rules](https://code.claude.com/docs/en/permissions), for example `--allowed-tools "Bash(pytest:*)" "Bash(python3:*)"`.

## Plug in your own arms

Arms live in [arms.json](arms.json); pass another file with `--arms-file`.

```json
{
  "A": {"label": "Opus, no router", "model": "opus", "router": null},
  "B": {"label": "Opus, router", "model": "opus", "router": "opus"},
  "E": {"label": "Sonnet, high effort", "model": "sonnet", "router": null, "effort": "high"}
}
```

| Field | Meaning |
|---|---|
| `label` | Name shown in the report |
| `model` | Passed to `claude --model` |
| `router` | `null` for no router. `"opus"` or `"sonnet"` installs the router, switched on, with that `main_model` |
| `effort` | Optional. Passed to `claude --effort`. Left out, the model's default applies (`medium` for Opus 5.5 and Sonnet 5.5) |

Arms run in the order listed. Put the two arms you want to compare next to each other: they form a pair, and the report shows cache use by position within the pair.

`--arms A,B`, `--tasks T1,T2` and `--runs 3` select a subset or change the number of passes.

## Try the pipeline for free

Point the runner at any local server that imitates the Messages API ([tests/e2e/mock_api.py](../tests/e2e/mock_api.py) is one) to check your tasks file, project and checks before paying for real runs. Every task will fail, since the mock does no work, but paths and checks are exercised.

```bash
MOCK_LOG=/tmp/mock.jsonl python3 tests/e2e/mock_api.py 8787 &
BENCH_MOCK_URL=http://127.0.0.1:8787 python3 bench/run.py --home-root /tmp/bench-dry --out /tmp/bench-dry-out --cap-total 1 --runs 1
```

## What the report shows

* Passed runs, cost, cost per passed task, wall time, and the same split by pass so you can see run to run variance.
* Tokens per model family, Opus tokens and Opus share of all tokens.
* Cache read as a share of input, by position within the arm pair.
* Which model and effort handled each run and which subagents were used, read from the session transcripts.
* Task failures with the check's message, and any runs that did not finish normally.

With few runs per task, treat differences smaller than an arm's own pass to pass spread as noise.

## Files

| File | Purpose |
|---|---|
| `run.py` | Runner |
| `report.py` | Report from `results.jsonl` |
| `usage.py` | Cost, tokens, effort and delegations for any session transcript: `python3 bench/usage.py ~/.claude/projects/<project>/<session>.jsonl` |
| `arms.json`, `tasks.json` | The published arms and tasks |
| `project/`, `checks/` | The sample project and its hidden checks |
| `results/` | The published run |
