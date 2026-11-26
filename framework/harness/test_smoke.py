#!/usr/bin/env python3
"""test_smoke - non-régression de bout en bout : chaque générateur et chaque hook tournent sans planter.

Lance chaque commande `pm run` en lecture seule sur la mission `demo` et chaque hook avec une entrée simulée,
puis vérifie : aucune trace d'erreur (Traceback), et le résultat attendu (code de sortie, décision du
garde-fou). `--json out.json` écrit le relevé pour comparer deux versions du plugin (avant / après un
déplacement de fichiers). N'écrit rien hors d'un dossier temporaire.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = Path(tempfile.mkdtemp(prefix="pmf-smoke-"))

GENERATORS = {
    "projection": ["demo"], "plan": ["demo", "--help"], "risks": ["demo"], "raci": ["demo"], "poc": ["demo", "--help"],
    "archi": ["demo"], "activity": ["demo", "check"], "planning": ["demo"], "deck-gate": ["demo"],
    "transcripts": ["demo", "--help"], "omi-sync": ["--help"], "slack": ["--help"], "dossier": ["demo"],
    "traceability": ["--example", str(TMP / "trace.xlsx")], "partner-report": ["--input", str(TMP / "cr.json")],
    "jira-images": ["demo", "--help"], "jira-changes-audit": ["demo", "--help"], "jira-sprints-audit": ["demo", "--help"],
    "notion-topics-audit": ["--help"], "notion-scaffold": ["--mission", "demo", "--emit-plan"],
    "drive-scaffold": ["--mission", "demo"], "docs-coherence-audit": ["--mission", "demo"], "gate": ["demo"],
    "method": ["demo"], "templates": [], "office": ["--help"], "weekly-report": ["--list"], "trace-audit": ["demo"],
    "console": ["--help"], "cockpit": ["demo"], "tones": ["demo"], "init": ["smoke-mission"], "setup": ["demo"],
    "preflight": ["demo"], "reset": ["--help"], "agent": ["--help"],
}
OFFICE = "~/Library/" + "CloudStorage/OneDrive-X/P/Risks." + "xlsx"
HOOKS = {
    ("garde_office", "allow"): {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}},
    ("garde_office", "deny"): {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "r" + "m " + OFFICE}},
    ("garde_suppression", "allow"): {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}},
    ("garde_suppression", "deny"): {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "r" + "m " + OFFICE}},
    ("pas_ecraser_jira", "allow"): {"hook_event_name": "PreToolUse", "tool_name": "mcp__x__editJiraIssue",
                                    "tool_input": {"issueIdOrKey": "X-1", "fields": {"summary": "s"}}},
    ("onboarding_hint", "allow"): {"hook_event_name": "SessionStart", "source": "startup"},
    ("journal_usage", "allow"): {"hook_event_name": "PreToolUse", "tool_name": "Skill", "tool_input": {"skill": "x"}},
    ("journal_activite", "allow"): {"hook_event_name": "PreToolUse", "tool_name": "Skill", "tool_input": {"skill": "x"}, "tool_use_id": "t"},
    ("archi_kit", "allow"): {"hook_event_name": "PostToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}},
}


def hook_path(name):
    for base in (ROOT / "framework" / "garde-fous", ROOT / "framework" / "hooks"):
        if (base / f"{name}.py").exists():
            return base / f"{name}.py"
    return None


def run():
    (TMP / "cr.json").write_text(json.dumps({"partner": "partenaire_b", "meeting": "Point", "date": "2026-11-26",
                                             "points": [{"title": "Sujet", "situation": "S.", "next_step": "faire X", "deadline": "02/12"}]}))
    env = dict(os.environ, PMF_JIRA_ENV="/nonexistent", CLAUDE_PROJECT_DIR=str(TMP), CLAUDE_PLUGIN_ROOT=str(ROOT))
    rows = {}
    for g, args in GENERATORS.items():
        p = subprocess.run([sys.executable, str(ROOT / "framework" / "pm.py"), "run", g] + args, cwd=ROOT,
                           capture_output=True, text=True, timeout=120, env=env)
        out = p.stdout + p.stderr
        rows[f"gen:{g}"] = {"rc": p.returncode, "traceback": "Traceback" in out}
    for (h, expect), payload in HOOKS.items():
        hp = hook_path(h)
        if hp is None:
            rows[f"hook:{h}:{expect}"] = {"rc": "missing", "traceback": False, "decision": None}
            continue
        p = subprocess.run([sys.executable, str(hp)], input=json.dumps(payload), capture_output=True, text=True,
                           timeout=60, env=env, cwd=ROOT)
        out = p.stdout + p.stderr
        rows[f"hook:{h}:{expect}"] = {"rc": p.returncode, "traceback": "Traceback" in out,
                                      "decision": "deny" if '"deny"' in out else "allow"}
    return rows


def main():
    rows = run()
    bad = [k for k, v in rows.items() if v["traceback"] or v.get("rc") == "missing"
           or (k.startswith("hook:") and k.rsplit(":", 1)[1] != v.get("decision"))]
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(rows, indent=1, sort_keys=True))
    for k in bad:
        print("  ECHEC", k, rows[k])
    print(f"  {len(rows) - len(bad)}/{len(rows)} tests OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
