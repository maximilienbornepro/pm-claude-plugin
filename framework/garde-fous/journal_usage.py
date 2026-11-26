#!/usr/bin/env python3
"""Hook PreToolUse : journalise les invocations de skills et d'agents - generique.

But : savoir plus tard ce qui n'est plus utilise. Chaque appel d'un skill (outil
`Skill`) ou d'un agent (outil `Agent` / `Task`) ajoute une ligne JSON a
`$CLAUDE_PROJECT_DIR/.claude/usage.log`. Le hook n'autorise ni ne refuse rien (rien
sur stdout) et n'echoue jamais : quoi qu'il arrive, l'outil continue.
"""
import json, sys, os, datetime

try:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    inp = data.get("tool_input") or {}
    name = ""
    if tool == "Skill":
        name = inp.get("skill", "")
    elif tool in ("Agent", "Task"):
        name = inp.get("subagent_type") or inp.get("description", "")
    rec = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "tool": tool,
        "name": name,
        "session": data.get("session_id", ""),
    }
    base = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    path = os.path.join(base, ".claude", "usage.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
except Exception:
    pass  # un hook de journal ne doit jamais bloquer un outil
