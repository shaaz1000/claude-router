#!/usr/bin/env python3
"""Install or uninstall Claude Router into ~/.claude (macOS, Linux, Windows).

  python3 install.py              install (safe to rerun)
  python3 install.py --uninstall  remove everything it added
"""
import json, shutil, sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
C = Path.home() / ".claude"
HOOK = C / "router" / "router.py"
CMD = f'"{sys.executable}" "{HOOK}"'          # absolute paths: works without python3 on PATH or ~ expansion
START, END = "<!-- claude-router:start -->", "<!-- claude-router:end -->"
AGENTS = ["router-fast.md", "router-sonnet.md", "router-deep.md", "router-max.md"]


def load_settings(p):
    if not p.exists() or not p.read_text().strip():
        return {}
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"{p} is not valid JSON ({e}). Fix it first; nothing was changed.")


def is_router(h):
    return "router.py" in str(h.get("command", "")) and "router" in str(h.get("command", ""))


def install():
    (C / "router").mkdir(parents=True, exist_ok=True)
    (C / "agents").mkdir(parents=True, exist_ok=True)
    settings_p = C / "settings.json"
    s = load_settings(settings_p)                       # validate before touching anything
    shutil.copy2(SRC / "hooks" / "router.py", HOOK)
    for a in AGENTS:
        shutil.copy2(SRC / "agents" / a, C / "agents" / a)
    cfg = C / "router" / "config.json"
    if not cfg.exists():
        shutil.copy2(SRC / "config.example.json", cfg)
    md = C / "CLAUDE.md"
    text = md.read_text() if md.exists() else ""
    block = (SRC / "CLAUDE.router.md").read_text().strip()
    if START in text:
        text = text[: text.index(START)] + block + text[text.index(END) + len(END):]
    else:
        text = (text.rstrip() + "\n\n" if text.strip() else "") + block + "\n"
    md.write_text(text)
    groups = s.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
    for g in groups:
        g["hooks"] = [h for h in g.get("hooks", []) if not is_router(h)]
    groups[:] = [g for g in groups if g.get("hooks")]
    groups.append({"hooks": [{"type": "command", "command": CMD, "timeout": 5}]})
    if settings_p.exists():
        shutil.copy2(settings_p, settings_p.with_suffix(".json.bak"))
    settings_p.write_text(json.dumps(s, indent=2) + "\n")
    print("Claude Router installed. Restart Claude Code.")
    print(f'Test: "{sys.executable}" "{HOOK}" --test "rename foo to bar"')


def uninstall():
    settings_p = C / "settings.json"
    if settings_p.exists():
        s = load_settings(settings_p)
        groups = s.get("hooks", {}).get("UserPromptSubmit", [])
        for g in groups:
            g["hooks"] = [h for h in g.get("hooks", []) if not is_router(h)]
        if "hooks" in s:
            s["hooks"]["UserPromptSubmit"] = [g for g in groups if g.get("hooks")]
            if not s["hooks"]["UserPromptSubmit"]:
                del s["hooks"]["UserPromptSubmit"]
        settings_p.write_text(json.dumps(s, indent=2) + "\n")
    md = C / "CLAUDE.md"
    if md.exists() and START in md.read_text():
        t = md.read_text()
        md.write_text((t[: t.index(START)] + t[t.index(END) + len(END):]).strip() + "\n")
    for a in AGENTS:
        (C / "agents" / a).unlink(missing_ok=True)
    shutil.rmtree(C / "router", ignore_errors=True)
    print("Claude Router removed.")


if __name__ == "__main__":
    uninstall() if "--uninstall" in sys.argv else install()
