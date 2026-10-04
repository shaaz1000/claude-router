"""On/off switch tests. The router ships off. Run: python3 tests/toggle.py"""
import json, os, subprocess, sys, tempfile
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
H = os.path.join(ROOT, "hooks", "router.py"); fails = []


def env(home): return {**os.environ, "HOME": home, "USERPROFILE": home, "PYTHONIOENCODING": "utf-8"}
def hook(home, prompt): return subprocess.run([sys.executable, H], input=json.dumps({"prompt": prompt}), capture_output=True, text=True, env=env(home)).stdout.strip()
def cli(home, flag): return subprocess.run([sys.executable, H, flag], capture_output=True, text=True, encoding="utf-8", env=env(home)).stdout.strip()
def log_lines(home):
    p = os.path.join(home, ".claude", "router", "log.jsonl")
    return len(open(p).read().splitlines()) if os.path.exists(p) else 0
def check(name, ok):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    if not ok: fails.append(name)


home = tempfile.mkdtemp()
print("== fresh home, no config: off")
check("normal prompt prints nothing", hook(home, "find the root cause of the deadlock") == "")
check("no log line and no router directory created", log_lines(home) == 0 and not os.path.exists(os.path.join(home, ".claude", "router")))
check("--status reports OFF", "router OFF" in cli(home, "--status"))
out = hook(home, "!deep add a retry to fetchPrices")
check("!deep prefix still routes that one prompt", '"additionalContext": "[router] tier=deep' in out)
check("prefix status line says the router is off", "router off, this prompt only" in out and "router ON" not in out)
check("prefix prompt is logged once", log_lines(home) == 1)
check("next normal prompt is silent again", hook(home, "rename foo to bar") == "" and log_lines(home) == 1)

print("== --on")
check("--on reports ON", "router ON" in cli(home, "--on"))
out = hook(home, "find the root cause of the deadlock")
check("normal prompt is routed", '"additionalContext": "[router] tier=max' in out)
check('status line shows "router ON"', json.loads(out)["systemMessage"].startswith("🧭 router ON"))
check("prefix still works while on", "tier=fast" in hook(home, "!fast find the root cause of the deadlock"))
check("setting is stored in config.json", json.load(open(os.path.join(home, ".claude", "router", "config.json")))["enabled"] is True)
check("a new process still sees ON (persists across sessions)", "router ON" in cli(home, "--status") and hook(home, "add a search bar") != "")
check("non user prompts stay ignored while on", hook(home, "<task-notification>\n<summary>x</summary>") == "" and hook(home, "/compact") == "")

print("== --off")
check("--off reports OFF", "router OFF" in cli(home, "--off"))
n = log_lines(home)
check("normal prompt prints nothing and logs nothing", hook(home, "find the root cause of the deadlock") == "" and log_lines(home) == n)
check("other config keys survive toggling", json.load(open(os.path.join(home, ".claude", "router", "config.json"))) == {"enabled": False})

print("== installer")
home2 = tempfile.mkdtemp(); inst = [sys.executable, os.path.join(ROOT, "install.py")]
subprocess.run(inst, env=env(home2), capture_output=True, check=True); c = os.path.join(home2, ".claude")
cfg_p = os.path.join(c, "router", "config.json")
check("fresh install is off", json.load(open(cfg_p))["enabled"] is False and hook(home2, "find the root cause of the deadlock") == "")
cmds = {n: open(os.path.join(c, "commands", n + ".md"), encoding="utf-8").read() for n in ("router-on", "router-off", "router-status") if os.path.exists(os.path.join(c, "commands", n + ".md"))}
check("three slash commands installed with the real hook path", len(cmds) == 3 and all("{{ROUTER_CMD}}" not in t and "router.py" in t for t in cmds.values()))
cli(home2, "--on"); subprocess.run(inst, env=env(home2), capture_output=True, check=True)
check("reinstall keeps the user's ON setting", json.load(open(cfg_p))["enabled"] is True)
subprocess.run(inst + ["--uninstall"], env=env(home2), capture_output=True, check=True)
check("uninstall removes commands, agents and the router directory", not os.path.exists(os.path.join(c, "router")) and not any(os.path.exists(os.path.join(c, "commands", n + ".md")) for n in cmds)
      and not os.path.exists(os.path.join(c, "agents", "router-fast.md")))
check("uninstall leaves settings.json without router or empty hooks", json.load(open(os.path.join(c, "settings.json"))) == {})
print("PASS" if not fails else f"FAIL: {len(fails)} check(s)")
sys.exit(1 if fails else 0)
