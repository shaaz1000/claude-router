#!/usr/bin/env python3
"""Summarize bench results. Usage: python3 bench/report.py bench/results/results.jsonl"""
import collections, json, sys

rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
NAMES = {"A": "A Opus, no router", "B": "B Opus, router", "C": "C Sonnet, no router", "D": "D Sonnet, router"}      # the published run predates arm_label
NAMES.update({r["arm"]: f"{r['arm']} {r['arm_label']}" for r in rows if r.get("arm_label")})
tok = lambda r, fam: sum(sum(u[k] for k in ("input", "output", "cache_read", "cache_write")) for m, u in (r.get("models") or {}).items() if fam in m)
part = lambda r, fam, k: sum(u[k] for m, u in (r.get("models") or {}).items() if fam in m)
by_arm = collections.defaultdict(list)
for r in rows:
    by_arm[r["arm"]].append(r)
rng = lambda xs: f"{min(xs):.2f} to {max(xs):.2f}" if xs else "n/a"

ok = lambda rs: [r for r in rs if not r.get("infra_fail") and not r.get("skipped")]       # runs that got a fair attempt
allk = lambda r: sum(sum(u[k] for k in ("input", "output", "cache_read", "cache_write")) for u in (r.get("models") or {}).values())
inp = lambda r, k: sum(u[k] for u in (r.get("models") or {}).values())
pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "n/a"

print("Directional only: 2 runs per task per arm. Costs are notional API prices (cost reported by Claude Code per model).\n")
print("## Per arm\n\n| Arm | Valid runs | Passed | Cost total | Pass 1 / pass 2 cost | Cost per passed task | Opus tokens | Opus share of all tokens | Opus output tokens | Cache read share of input | Wall total | Pass 1 / pass 2 wall |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
for arm in sorted(by_arm):
    rs = ok(by_arm[arm]); p = sum(r["passed"] for r in rs); cost = sum(r.get("cost_usd", 0) for r in rs); runs = sorted({r["run"] for r in rs})
    per_run = [sum(r.get("cost_usd", 0) for r in rs if r["run"] == n) for n in runs]; wall_run = [sum(r.get("wall_s", 0) for r in rs if r["run"] == n) for n in runs]
    cr = sum(inp(r, "cache_read") for r in rs); all_in = cr + sum(inp(r, "input") + inp(r, "cache_write") for r in rs)
    print(f"| {NAMES.get(arm, arm)} | {len(rs)}/{len(by_arm[arm])} | {p}/{len(rs)} ({pct(p, len(rs))}) | ${cost:.2f} | {' / '.join(f'${c:.2f}' for c in per_run)} | "
          f"{'$%.3f' % (cost / p) if p else 'n/a'} | {sum(tok(r, 'opus') for r in rs):,} | {pct(sum(tok(r, 'opus') for r in rs), sum(allk(r) for r in rs))} | {sum(part(r, 'opus', 'output') for r in rs):,} | "
          f"{pct(cr, all_in)} | {sum(r.get('wall_s', 0) for r in rs):.0f} s | {' / '.join(f'{w:.0f} s' for w in wall_run)} |")

print("\n## Prompt cache: cache read share of input, by the arm's position within its model pair\n\nInput = uncached input + cache write + cache read. Position 1 ran first for that task and pass; position 2 ran right after the other arm on the same model.\n\n| Arm | Ran first in its pair | Ran second in its pair | Cache write tokens, first / second |\n|---|---|---|---|")
for arm in sorted(by_arm):
    cells = []; writes = []
    for first in (True, False):
        rs = [r for r in ok(by_arm[arm]) if (r.get("position", 1) % 2 == 1) == first]
        cr = sum(inp(r, "cache_read") for r in rs); tot = cr + sum(inp(r, "input") + inp(r, "cache_write") for r in rs)
        cells.append(f"{pct(cr, tot)} ({len(rs)} runs)"); writes.append(f"{sum(inp(r, 'cache_write') for r in rs):,}")
    print(f"| {NAMES.get(arm, arm)} | {cells[0]} | {cells[1]} | {' / '.join(writes)} |")

print("\n## Tokens by model family per arm\n\n| Arm | Family | Input | Output | Cache write | Cache read | Cost |\n|---|---|---|---|---|---|---|")
for arm in sorted(by_arm):
    for fam in ("opus", "sonnet", "haiku"):
        vals = [sum(part(r, fam, k) for r in by_arm[arm]) for k in ("input", "output", "cache_write", "cache_read")]
        cost = sum(u["cost_usd"] for r in by_arm[arm] for m, u in (r.get("models") or {}).items() if fam in m)
        if any(vals):
            print(f"| {arm} | {fam} | {vals[0]:,} | {vals[1]:,} | {vals[2]:,} | {vals[3]:,} | ${cost:.2f} |")

print("\n## Per task: cost of run 1 / run 2 and pass (P) or fail (F)\n\n| Task | Tier | " + " | ".join(NAMES.get(a, a) for a in sorted(by_arm)) + " |\n|---|---|" + "---|" * len(by_arm))
tasks = []
for r in rows:
    if (r["task"], r["tier"]) not in tasks:
        tasks.append((r["task"], r["tier"]))
for t, tier in tasks:
    cells = []
    for arm in sorted(by_arm):
        rs = sorted((r for r in by_arm[arm] if r["task"] == t), key=lambda r: r["run"])
        cells.append(" / ".join(("skip" if r.get("skipped") else "INFRA" if r.get("infra_fail") else f"${r['cost_usd']:.2f} {'P' if r['passed'] else 'F'}") for r in rs))
    print(f"| {t} | {tier} | " + " | ".join(cells) + " |")

print("\n## Routing actually observed\n")
for arm in sorted(by_arm):
    d = collections.Counter(); eff = collections.Counter()
    for r in by_arm[arm]:
        d[(r["tier"], tuple(r.get("delegations") or ()))] += 1
        for s in r.get("main") or []:
            eff[(s["model"], s["effort"])] += 1
    print(f"- {NAMES.get(arm, arm)}: main steps {dict(eff)}; delegations by tier " + "; ".join(f"{t}: {list(x) or 'none'} x{n}" for (t, x), n in sorted(d.items())))
bad = [r for r in rows if r.get("skipped") or r.get("infra_fail") or (r.get("subtype") not in (None, "success"))]
print("\n## Runs that did not finish normally\n\n" + ("\n".join(f"- {r['arm']} {r['task']} run {r['run']}: {r.get('skipped') or ('INFRA FAIL: ' + r['infra_fail'] if r.get('infra_fail') else r.get('subtype'))}" for r in bad) or "none"))
fails = [r for r in rows if not r["passed"] and not r.get("infra_fail") and not r.get("skipped")]
print("\n## Task failures\n\n" + ("\n".join(f"- {r['arm']} {r['task']} run {r['run']}: {r.get('check')}" for r in fails) or "none"))
lim = [r for r in sorted(rows, key=lambda r: r.get("started_at", 0)) if r.get("rate_limit_last")]
print("\n## Usage limit data carried by rate limit events\n")
if lim:
    print("first run :", json.dumps(lim[0].get("rate_limit_first"))); print("last run  :", json.dumps(lim[-1]["rate_limit_last"]))
else:
    print("no rate limit events were emitted")
