"""Petit journal partagé des garde-fous : une ligne dans .claude/activity.log quand un hook bloque une action.

Lu par l'écran « agence » (garde-fou allumé en rouge). Ne lève jamais : un journal ne doit pas changer la
décision du garde-fou.
"""
import datetime
import json
import os


def guard(name, detail, decision="deny", session=""):
    try:
        path = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), ".claude", "activity.log")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        ts = datetime.datetime.now().isoformat(timespec="milliseconds")
        rec = {"ts": ts, "session": session, "agent": "claude", "ev": "start", "tool": "hook", "kind": "hook",
               "name": name, "detail": f"{'bloqué' if decision == 'deny' else decision} : {str(detail)[:100]}",
               "id": f"hook-{name}-{ts}"}
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
