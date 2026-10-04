# Changelog

## v5
* **Off by default.** A benchmark (`bench/`, 64 real runs) found that routing did not save money: plain Sonnet was cheapest per passed task, the router changed nothing measurable with an Opus lead and cost 56% more with a Sonnet lead. See the README.
* New `enabled` switch in `config.json`, `router.py --on | --off | --status`, and `/router-on`, `/router-off`, `/router-status` commands. While off the hook prints and logs nothing; a `!fast`, `!std`, `!deep` or `!max` prefix still routes that one prompt. While on, every status line starts with `router ON`.
* `bench/`: reusable benchmark with configurable arms, project, tasks and checks, and `bench/usage.py`, which reads cost and tokens from a session transcript's `cost-state` record.
* README rewritten as a research write up.
* Uninstall also removes the commands and no longer leaves an empty `hooks` key.
* `tests/run_all.sh` now exits nonzero on failure. Gates: tuned set 95%, holdouts 85%, zero complex tasks routed to fast. Robustness checks assert instead of only printing.
* Router ignores cross session messages and built in autonomous loop ticks. Both were being routed, the loop tick as max on every firing.
* Removed `effort: low` from `router-fast`: Haiku 4.5 does not support effort.
* Delegation is now concrete. With an Opus lead, standard work goes to `router-sonnet` only when the change likely touches 2 or more files or 50 or more lines, and fast work stays in the main session unless it is bulk mechanical work. In real runs the Haiku route made 14 and 18 API calls for a two file rename, and Opus skipped a vaguely worded delegation in 1 of 2 runs.
* Deep and max instructions: edit files only when a change was asked for; questions get analysis only. Before, the instruction said "plan, edit, then verify" and one real run edited files when asked only for a root cause.
* `install.py` writes `settings.json.bak` once and keeps the oldest original across reruns.
* Docs corrected against Claude Code 2.1.289: foreground delegation only works under `claude -p`; Sonnet's `effort: high` is a quality choice, not its default; auto mode reviews the subagent's whole run; full list of `UserPromptSubmit` output fields; a top level `effortLevel` is ignored by Sonnet 5.5 and Opus 5.5.

## v4
* **Opus leads, Sonnet executes** is now the default (`main_model: "opus"`), matching Anthropic's Sonnet 5.5 guidance. Previous behavior is available as budget mode (`main_model: "sonnet"`).
* New `router-sonnet` subagent, pinned to `effort: high` after testing showed it inherited Opus's medium.
* "Work still taking shape" signals route to Opus: `not sure how`, `best way to`, `pros and cons`, `should we use`.
* Fixed: negation filter erased "not sure how".
* Status line labels reflect the active mode.

## v3
* Removed per prompt `effortLevel` writing: verified in Claude Code 2.1.289 that it is read only at session start.
* Routing moved fully to subagents with their own `model` and `effort`; added `router-max` (Opus, xhigh).
* Ignores agent completion notices, which arrive through the same hook and could cause delegation loops.
* Delegations run in the foreground (`run_in_background: false`).
* Follow ups always stay in the main session; per project state removed.
* Cross platform `install.py` with uninstall, backups and validation.

## v2
* Splits what you wrote from what you pasted; pasted content no longer counts as complexity.
* Haiku is strict opt in; uncertain prompts default to Sonnet.
* Plain English bug symptoms (`randomly`, `slow`, `at the same time`) count as deep signals.
* Bounded analysis for huge pastes: worst case latency fell from over 30 s to about 100 ms.
* Fixed crash on non object input, directory creation, and a state race across parallel sessions.

## v1
* Keyword scoring hook that wrote `effortLevel` per prompt and delegated to Haiku and Opus subagents.
