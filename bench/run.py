#!/usr/bin/env python3
"""Savings benchmark: run every task in every arm against real models and check each result automatically.

Arms come from arms.json, tasks from tasks.json, the sample project from project/ and the hidden checks from
checks/. See bench/README.md for how to plug in your own. The defaults reproduce the published run:

  A  Opus, no router          C  Sonnet, no router
  B  Opus, router             D  Sonnet, router (budget mode: main_model sonnet)

Each arm gets its own clean HOME under --home-root, so your real config, plugins and hooks are not involved.
Runs are sequential and interleaved per task. A usage limit, rate limit, API error or timeout is recorded as
INFRA FAIL (not a task failure) and pauses the benchmark. This calls real models: read bench/README.md first.

  python3 bench/run.py --home-root /tmp/claude-router-bench/arms --out bench/results --cap-total 12 --link-keychain
"""
import argparse, json, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from usage import find_transcript, normalize, session_usage

ARMS = {}       # loaded from --arms-file: {id: {"label", "model", "router": null | "opus" | "sonnet", "effort": optional}}
ALLOWED = ["Bash(node:*)", "Bash(npm test:*)", "Bash(npm run test:*)", "Bash(git status:*)", "Bash(git diff:*)", "Bash(grep:*)", "Bash(ls:*)", "Bash(cat:*)"]
budget = {"spent": 0.0}
LIMIT = re.compile(r"usage limit|rate.?limit|limit reached|overloaded|\b429\b|\b529\b", re.I)


def order(arms, n):
    """Arm order for pass n. Even passes swap neighbours so neither arm of a pair always runs second on a warm prompt cache."""
    out = list(arms)
    if n % 2 == 0:
        for i in range(0, len(out) - 1, 2):
            out[i], out[i + 1] = out[i + 1], out[i]
    return out


def make_home(root, arm, link_keychain, resume):
    home = os.path.join(root, arm)
    if resume and os.path.isdir(home):
        return home
    shutil.rmtree(home, ignore_errors=True); os.makedirs(home)
    if link_keychain:      # macOS subscription login lives in the login keychain; link it, never copy it
        os.makedirs(os.path.join(home, "Library")); os.symlink(os.path.expanduser("~/Library/Keychains"), os.path.join(home, "Library", "Keychains"))
    main_model = ARMS[arm].get("router")
    if main_model:
        subprocess.run([sys.executable, os.path.join(REPO, "install.py")], env={**os.environ, "HOME": home}, check=True, capture_output=True)
        cfg_p = os.path.join(home, ".claude", "router", "config.json"); cfg = json.load(open(cfg_p)); cfg["main_model"] = main_model; cfg["enabled"] = True
        json.dump(cfg, open(cfg_p, "w"), indent=2)
    return home


def run_one(arm, home, task, n, a):
    available = a.cap_total - budget["spent"]
    if available < 0.15:
        return {"arm": arm, "arm_label": ARMS[arm].get("label", arm), "task": task["id"], "tier": task["tier"], "run": n, "skipped": "total budget cap reached", "passed": False}
    cap = round(min(a.cap_run, available), 2)
    work = os.path.join(a.out, "work", f"{arm}-{task['id']}-{n}"); shutil.rmtree(work, ignore_errors=True); shutil.copytree(a.project, work)
    subprocess.run("git init -q . && git add -A && git -c user.name=bench -c user.email=bench@example.com commit -qm init", cwd=work, shell=True, check=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "ANTHROPIC"))}
    env.update({"HOME": home, "DISABLE_AUTOUPDATER": "1"})
    if os.environ.get("BENCH_MOCK_URL"):      # pipeline test against a mock API: no real calls
        env.update({"ANTHROPIC_BASE_URL": os.environ["BENCH_MOCK_URL"], "ANTHROPIC_API_KEY": "sk-ant-test"})
    cmd = ["claude", "-p", task["prompt"], "--model", ARMS[arm]["model"], "--output-format", "stream-json", "--verbose",
           "--max-budget-usd", str(cap), "--permission-mode", "acceptEdits", "--allowedTools", *(a.allowed_tools or ALLOWED)]
    if ARMS[arm].get("effort"):
        cmd += ["--effort", ARMS[arm]["effort"]]
    t0 = time.time(); timed_out = False
    try:
        out = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=a.timeout).stdout
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode(errors="ignore") if isinstance(e.stdout, bytes) else (e.stdout or ""); timed_out = True
    wall = time.time() - t0
    res, limits, api_errors = {}, [], []
    for line in out.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "result":
            res = ev
        elif ev.get("type") == "rate_limit_event":
            limits.append(ev.get("rate_limit_info"))
        elif ev.get("type") == "system" and ev.get("subtype") == "api_retry":
            api_errors.append({k: ev.get(k) for k in ("error_status", "error", "attempt")})
    cost = float(res.get("total_cost_usd") or 0); budget["spent"] += cost
    # INFRA FAIL: the run did not get a fair attempt (usage or rate limit, API error, crash, timeout). Not a task failure.
    infra = None
    if timed_out:
        infra = "timeout"
    elif not res:
        infra = "no result event (process exited early)"
    elif any((l or {}).get("status") == "rejected" for l in limits):
        infra = "rate limit rejected: " + json.dumps([l for l in limits if (l or {}).get("status") == "rejected"][-1])[:200]
    elif res.get("is_error") and res.get("subtype") != "error_max_budget_usd":
        infra = f"api error: {res.get('subtype')} {str(res.get('result'))[:160]}"
    elif res.get("is_error") is not True and LIMIT.search(str(res.get("result") or "")[:300]) and not res.get("num_turns"):
        infra = "limit message in reply: " + str(res.get("result"))[:160]
    reply_p = os.path.join(a.out, "work", f"{arm}-{task['id']}-{n}.reply.txt"); open(reply_p, "w").write(res.get("result") or "")
    # A check runs in the working copy and exits 0 on pass. Default: node <checks>/<id>.js. A task may set its own "check" command.
    check_cmd = task.get("check") or f'node "{os.path.join(a.checks, task["id"] + ".js")}"'
    chk = subprocess.run(check_cmd, shell=True, cwd=work, env={**os.environ, "BENCH_REPLY": reply_p, "BENCH_CHECKS": a.checks}, capture_output=True, text=True, timeout=120)
    sid = res.get("session_id"); tp = find_transcript(home, sid) if sid else None; u = session_usage(tp) if tp else {}
    return {"arm": arm, "arm_label": ARMS[arm].get("label", arm), "task": task["id"], "tier": task["tier"], "run": n, "passed": chk.returncode == 0 and not infra, "infra_fail": infra,
            "check": chk.stdout.strip()[-160:], "api_retries": api_errors[-3:],
            "cost_usd": cost, "models": normalize(res.get("modelUsage")), "wall_s": round(wall, 1), "turns": res.get("num_turns"),
            "subtype": res.get("subtype"), "timed_out": timed_out, "cap": cap, "session_id": sid,
            "main": u.get("main"), "delegations": u.get("delegations"), "subagents": u.get("subagents"),
            "rate_limit_first": limits[0] if limits else None, "rate_limit_last": limits[-1] if limits else None,
            "started_at": round(t0), "position": a.order[n].index(arm) + 1}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home-root", required=True, help="directory that will hold one clean HOME per arm (wiped per arm)")
    ap.add_argument("--out", default=os.path.join(HERE, "results")); ap.add_argument("--arms", default="", help="comma separated arm ids (default: all in the arms file)")
    ap.add_argument("--arms-file", default=os.path.join(HERE, "arms.json")); ap.add_argument("--tasks-file", default=os.path.join(HERE, "tasks.json"))
    ap.add_argument("--project", default=os.path.join(HERE, "project"), help="directory copied fresh for every run")
    ap.add_argument("--checks", default=os.path.join(HERE, "checks"), help="directory holding <task id>.js checks")
    ap.add_argument("--allowed-tools", nargs="*", help="tool permission rules for the runs (default: node, npm test, read only git and shell)")
    ap.add_argument("--tasks", default="", help="comma separated task ids (default: all)"); ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--cap-total", type=float, required=True, help="stop starting runs once this many notional dollars are spent")
    ap.add_argument("--cap-run", type=float, default=0.6); ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--link-keychain", action="store_true", help="macOS: symlink the login keychain into each clean HOME")
    ap.add_argument("--resume", action="store_true", help="keep finished rows and the arm homes; rerun only what is missing or was an INFRA FAIL")
    ap.add_argument("--already-spent", type=float, default=0.0, help="with --resume: notional dollars already spent, counted against --cap-total")
    a = ap.parse_args(); a.out = os.path.abspath(a.out); os.makedirs(os.path.join(a.out, "work"), exist_ok=True)
    a.project, a.checks = os.path.abspath(a.project), os.path.abspath(a.checks)
    ARMS.update(json.load(open(a.arms_file)))
    tasks = [t for t in json.load(open(a.tasks_file)) if not a.tasks or t["id"] in a.tasks.split(",")]
    results_p = os.path.join(a.out, "results.jsonl"); arms = a.arms.split(",") if a.arms else list(ARMS)
    a.order = {n: order(arms, n) for n in range(1, a.runs + 1)}
    done = {}
    if a.resume and os.path.exists(results_p):
        for l in open(results_p):
            r = json.loads(l)
            if not r.get("infra_fail") and not r.get("skipped"):
                done[(r["arm"], r["task"], r["run"])] = r
        budget["spent"] = a.already_spent
        open(results_p, "w").write("".join(json.dumps(r) + "\n" for r in done.values()))
    else:
        open(results_p, "w").close()
    homes = {arm: make_home(a.home_root, arm, a.link_keychain, a.resume) for arm in arms}
    # Interleaved: for each task, pass 1 over every arm, then pass 2, before moving to the next task.
    for task in tasks:
        for n in range(1, a.runs + 1):
            for arm in a.order[n]:
                if (arm, task["id"], n) in done:
                    continue
                row = run_one(arm, homes[arm], task, n, a)
                open(results_p, "a").write(json.dumps(row) + "\n")
                status = "INFRA FAIL" if row.get("infra_fail") else "PASS" if row["passed"] else "FAIL"
                print(f"{task['id']} run{n} {arm} {status} ${row.get('cost_usd', 0):.4f} {row.get('wall_s', 0)}s {row.get('subtype') or row.get('skipped')} "
                      f"delegations={row.get('delegations')} | spent ${budget['spent']:.2f}", flush=True)
                if row.get("infra_fail"):
                    print(f"PAUSED on INFRA FAIL: {row['infra_fail']}\nNothing else was started. Rerun with --resume --already-spent {budget['spent']:.4f} to continue.", flush=True)
                    sys.exit(3)
    print(f"done: notional spend ${budget['spent']:.4f}; results in {results_p}")


if __name__ == "__main__":
    main()
