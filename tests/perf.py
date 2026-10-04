"""Hook latency, including adversarial inputs. Run: python3 tests/perf.py"""
import json, subprocess, sys, time, os
H = os.path.join(os.path.dirname(__file__), "..", "hooks", "router.py")
import tempfile
TMP = tempfile.mkdtemp(); ENV = {**os.environ, "HOME": TMP, "USERPROFILE": TMP}
subprocess.run([sys.executable, H, "--on"], env=ENV, capture_output=True)      # measure the on path
cases = [
    ("normal prompt", "add a loading state to the login button"),
    ("1MB log paste", "fix this\n" + "\n".join(f"2026-10-01 10:00:{i%60:02d} INFO line {i} " + "x"*80 for i in range(10000))),
    ("1MB prose paste", "We discussed the architecture and the plan. " * 25000),
    ("pathological 270KB", "a" * 200000 + "," * 50000 + " (" * 20000),
    ("pipes 500KB one line", "|" + "a|" * 250000),
    ("5MB mixed", ("x" * 300 + "\n|" + "b" * 300 + "\n") * 8000),
]
worst = 0
for name, p in cases:
    ts = []
    for _ in range(3):
        t = time.time(); r = subprocess.run([sys.executable, H], input=json.dumps({"prompt": p}), capture_output=True, text=True, timeout=30, env=ENV); ts.append(time.time() - t)
    m = sorted(ts)[1] * 1000; worst = max(worst, m)
    print(f"{name:22} {len(p)/1024:7.0f} KB  median {m:6.0f} ms  rc={r.returncode}")
print("PASS" if worst < 1000 else "FAIL", f"worst {worst:.0f} ms (budget 1000 ms, hook timeout 5000 ms)")
sys.exit(0 if worst < 1000 else 1)
