#!/usr/bin/env python3
"""Hook (UserPromptSubmit, PreToolUse, PostToolUse) : journal d'activité pour l'écran « agence ».

Chaque événement ajoute une ligne JSON à `$CLAUDE_PROJECT_DIR/.claude/activity.log` :
  {ts, ev: prompt|start|end, tool, kind, name, detail, agent, id, session}
- kind : skill | agent | generator | connector | tool | prompt
- name : le skill, l'agent, le générateur (`pm run <gen>`) ou le connecteur (`mcp__<serveur>__<outil>`)
- agent : l'agent qui agit (sous-agent si le hook le fournit, sinon « claude »)
Le hook n'autorise ni ne refuse rien (rien sur stdout) et n'échoue jamais. Aucun contenu de fichier, aucun
secret : seulement des noms d'outils et un court extrait de la demande (local, jamais envoyé).
"""
import datetime
import json
import os
import re
import sys

PM_RUN = re.compile(r"pm\.py\s+run\s+([\w-]+)|python3?\s+\S*framework/(?:departements/[\w-]+/|charte/)?generators/([\w-]+)/\S+\.py")


def classify(tool, inp):
    if tool == "Skill":
        return "skill", inp.get("skill", ""), inp.get("args", "")[:80]
    if tool in ("Agent", "Task"):
        return "agent", inp.get("subagent_type") or "general-purpose", (inp.get("description") or "")[:80]
    if tool.startswith("mcp__"):
        parts = tool.split("__")
        return "connector", tool, (parts[-1] if len(parts) > 2 else tool)
    if tool == "Bash":
        cmd = inp.get("command", "")
        m = PM_RUN.search(cmd)
        if m:
            return "generator", m.group(1) or m.group(2), (inp.get("description") or "")[:80]
        return "tool", "Bash", (inp.get("description") or cmd.split("\n")[0])[:80]
    detail = inp.get("file_path") or inp.get("pattern") or inp.get("url") or inp.get("query") or ""
    return "tool", tool, os.path.basename(str(detail))[:80]


try:
    data = json.load(sys.stdin)
    event = data.get("hook_event_name", "")
    rec = {"ts": datetime.datetime.now().isoformat(timespec="milliseconds"), "session": data.get("session_id", ""),
           "agent": data.get("agent_type") or data.get("subagent_type") or ("claude" if not data.get("agent_id") else data.get("agent_id"))}
    if event == "UserPromptSubmit":
        rec.update(ev="prompt", kind="prompt", tool="", name="demande", detail=(data.get("prompt") or "").strip().split("\n")[0][:120])
    else:
        tool = data.get("tool_name", "")
        kind, name, detail = classify(tool, data.get("tool_input") or {})
        rec.update(ev="start" if event == "PreToolUse" else "end", tool=tool, kind=kind, name=name, detail=detail,
                   id=data.get("tool_use_id", ""))
    base = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    path = os.path.join(base, ".claude", "activity.log")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
except Exception:
    pass  # un hook de journal ne doit jamais bloquer
