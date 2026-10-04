import sys, importlib.util, collections
spec = importlib.util.spec_from_file_location("router", "../hooks/router.py"); r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
from holdout2 import H2, FOLLOWUPS
cfg = r.load_config(); RANK = {t: i for i, t in enumerate(r.TIERS)}
rows = [(c, p, ok, None) for c, p, ok in H2] + [("followup", p, ok, prev) for prev, p, ok in FOLLOWUPS]
by = collections.defaultdict(lambda: [0, 0]); fails = []; costly = qual = 0
for c, p, ok, prev in rows:
    t, s, how, pay = r.classify(p, cfg)
    g = t in ok; by[c][0] += g; by[c][1] += 1
    if not g:
        over = RANK[t] > max(RANK[x] for x in ok); costly += over; qual += not over
        fails.append(f"  [{c}] {'COSTLY' if over else 'QUALITY RISK'}: got {t} (score {s}, via {how}) want {sorted(ok)} :: {p[:75]!r}")
tot = sum(a for a, b in by.values()); n = sum(b for a, b in by.values())
for c, (a, b) in by.items(): print(f"{c:12} {a}/{b}")
print(f"TOTAL {tot}/{n} = {100*tot/n:.0f}%   costly={costly} quality_risk={qual}"); print("\n".join(fails))
