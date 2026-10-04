# Changelog

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
