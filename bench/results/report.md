Directional only: 2 runs per task per arm. Costs are notional API prices (cost reported by Claude Code per model).

## Per arm

| Arm | Valid runs | Passed | Cost total | Pass 1 / pass 2 cost | Cost per passed task | Opus tokens | Opus share of all tokens | Opus output tokens | Cache read share of input | Wall total | Pass 1 / pass 2 wall |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A Opus, no router | 16/16 | 16/16 (100%) | $3.44 | $1.61 / $1.82 | $0.215 | 2,099,385 | 100% | 39,774 | 86% | 472 s | 210 s / 263 s |
| B Opus, router | 16/16 | 16/16 (100%) | $3.60 | $1.78 / $1.82 | $0.225 | 1,831,017 | 86% | 34,813 | 84% | 499 s | 240 s / 259 s |
| C Sonnet, no router | 16/16 | 16/16 (100%) | $1.62 | $0.78 / $0.83 | $0.101 | 0 | 0% | 0 | 86% | 317 s | 157 s / 160 s |
| D Sonnet, router | 16/16 | 14/16 (88%) | $2.52 | $1.22 / $1.30 | $0.180 | 693,391 | 28% | 17,953 | 85% | 570 s | 307 s / 263 s |

## Prompt cache: cache read share of input, by the arm's position within its model pair

Input = uncached input + cache write + cache read. Position 1 ran first for that task and pass; position 2 ran right after the other arm on the same model.

| Arm | Ran first in its pair | Ran second in its pair | Cache write tokens, first / second |
|---|---|---|---|
| A Opus, no router | 84% (8 runs) | 88% (8 runs) | 138,266 / 147,408 |
| B Opus, router | 84% (8 runs) | 83% (8 runs) | 167,442 / 172,399 |
| C Sonnet, no router | 85% (8 runs) | 87% (8 runs) | 126,184 / 129,848 |
| D Sonnet, router | 86% (8 runs) | 83% (8 runs) | 183,656 / 191,291 |

## Tokens by model family per arm

| Arm | Family | Input | Output | Cache write | Cache read | Cost |
|---|---|---|---|---|---|---|
| A | opus | 156 | 39,774 | 285,674 | 1,773,781 | $3.44 |
| B | opus | 134 | 34,813 | 291,843 | 1,504,227 | $3.33 |
| B | sonnet | 26 | 9,329 | 47,998 | 247,404 | $0.26 |
| C | sonnet | 150 | 27,232 | 256,032 | 1,593,290 | $1.62 |
| D | opus | 62 | 17,953 | 77,832 | 597,544 | $0.87 |
| D | sonnet | 122 | 24,214 | 258,002 | 1,261,925 | $1.53 |
| D | haiku | 126 | 10,720 | 39,113 | 208,591 | $0.12 |

## Per task: cost of run 1 / run 2 and pass (P) or fail (F)

| Task | Tier | A Opus, no router | B Opus, router | C Sonnet, no router | D Sonnet, router |
|---|---|---|---|---|---|
| F1 | fast | $0.16 P / $0.20 P | $0.16 P / $0.21 P | $0.09 P / $0.11 P | $0.10 F / $0.09 F |
| F2 | fast | $0.13 P / $0.14 P | $0.14 P / $0.13 P | $0.06 P / $0.06 P | $0.13 P / $0.07 P |
| S1 | standard | $0.23 P / $0.19 P | $0.20 P / $0.24 P | $0.11 P / $0.12 P | $0.09 P / $0.12 P |
| S2 | standard | $0.23 P / $0.24 P | $0.21 P / $0.23 P | $0.11 P / $0.12 P | $0.12 P / $0.12 P |
| S3 | standard | $0.26 P / $0.26 P | $0.33 P / $0.32 P | $0.13 P / $0.15 P | $0.13 P / $0.13 P |
| D1 | deep | $0.16 P / $0.27 P | $0.24 P / $0.18 P | $0.08 P / $0.08 P | $0.09 P / $0.31 P |
| D2 | deep | $0.24 P / $0.27 P | $0.30 P / $0.31 P | $0.09 P / $0.09 P | $0.24 P / $0.10 P |
| M1 | max | $0.20 P / $0.25 P | $0.20 P / $0.20 P | $0.10 P / $0.10 P | $0.31 P / $0.37 P |

## Routing actually observed

- A Opus, no router: main steps {('claude-opus-5-5', 'medium'): 16}; delegations by tier deep: none x4; fast: none x4; max: none x2; standard: none x6
- B Opus, router: main steps {('claude-opus-5-5', 'medium'): 16}; delegations by tier deep: none x4; fast: none x4; max: none x2; standard: none x4; standard: ['router-sonnet'] x2
- C Sonnet, no router: main steps {('claude-sonnet-5-5', 'medium'): 16}; delegations by tier deep: none x4; fast: none x4; max: none x2; standard: none x6
- D Sonnet, router: main steps {('claude-sonnet-5-5', 'medium'): 16}; delegations by tier deep: none x2; deep: ['router-deep'] x2; fast: none x1; fast: ['router-fast'] x3; max: ['router-max'] x2; standard: none x6

## Runs that did not finish normally

none

## Task failures

- D F1 run 1: FAIL: getUser still in basic.test.js
- D F1 run 2: FAIL: getUser still in basic.test.js

## Usage limit data carried by rate limit events

first run : {"status": "allowed", "resetsAt": 1791144600, "rateLimitType": "five_hour", "overageStatus": "rejected", "overageDisabledReason": "org_level_disabled", "isUsingOverage": false, "unifiedWindows": {"five_hour": {"utilization": 0.29, "resetsAt": 1791144600}, "seven_day": {"utilization": 0.1, "resetsAt": 1791594000}}}
last run  : {"status": "allowed", "resetsAt": 1791144600, "rateLimitType": "five_hour", "overageStatus": "rejected", "overageDisabledReason": "org_level_disabled", "isUsingOverage": false, "unifiedWindows": {"five_hour": {"utilization": 0.44, "resetsAt": 1791144600}, "seven_day": {"utilization": 0.12, "resetsAt": 1791594000}}}
