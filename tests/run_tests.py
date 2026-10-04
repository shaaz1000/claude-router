import sys, importlib.util, collections
sys.path.insert(0, "..")
spec = importlib.util.spec_from_file_location("router", "../hooks/router.py"); r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
from cases import CASES
cfg = r.load_config(); RANK = {t: i for i, t in enumerate(r.TIERS)}
by_cat = collections.defaultdict(lambda: [0, 0]); fails = []; costly = quality = leaks = 0
for cat, p, ok in CASES:
    tier, score, how, payload = r.classify(p, cfg)
    good = tier in ok
    by_cat[cat][0] += good; by_cat[cat][1] += 1
    leaks += tier == "fast" and min(RANK[t] for t in ok) >= RANK["deep"]   # complex task sent to Haiku
    if not good:
        if RANK[tier] > max(RANK[t] for t in ok): kind = "COSTLY (over routed)"; costly += 1
        else: kind = "QUALITY RISK (under routed)"; quality += 1
        fails.append(f"  [{cat}] {kind}: got {tier} (score {score}, payload {payload}) want {sorted(ok)} :: {p[:70]!r}")
tot = sum(v[0] for v in by_cat.values()); n = sum(v[1] for v in by_cat.values())
for c, (a, b) in by_cat.items(): print(f"{c:12} {a}/{b}")
print(f"TOTAL {tot}/{n} = {100*tot/n:.0f}%   costly={costly} quality_risk={quality}")
print("\n".join(fails))
MIN = float(sys.argv[1]) if len(sys.argv) > 1 else 0          # minimum accuracy in percent
print(f"GATE min={MIN:.0f}% complex_to_fast={leaks} (must be 0)")
sys.exit(0 if 100 * tot / n >= MIN and leaks == 0 else 1)
