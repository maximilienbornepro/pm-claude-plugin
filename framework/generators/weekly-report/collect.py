#!/usr/bin/env python3
"""weekly-report (collecte) - rassemble la MATIÈRE d'une semaine, par projet (DM-022).

Base du weekly report : ce que l'utilisateur a RÉELLEMENT demandé (ses prompts Claude Code) + les
artefacts touchés + le git. Les mails et le suivi des sujets s'ajoutent EN SESSION (connecteurs, safran) ;
ce script ne fait que la part LOCALE et déterministe : il collecte, il ne juge pas, il cite ses sources.

La SYNTHÈSE (regrouper en grandes lignes, écarter le bruit, rédiger le CR) est le travail du SKILL
`weekly-report` (le modèle), pas de ce script.

    pm run weekly-report --list                        # semaines disponibles + en historique
    pm run weekly-report --week 2026-W42               # matière de la semaine (JSON) + statut historique
    pm run weekly-report --week 2026-W42 --json out.json

Historique : <project>/weekly-reports/AAAA-Www.md  (un CR par semaine ; écrit par le skill après synthèse).
"""
import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# --- bruit : prompts à écarter (confirmations, itérations, réponses de formulaire) ---
NOISE = re.compile(r"^(oui|non|ok|go|vas[- ]?y|continue|parfait|merci|stop|c'est bon|nickel|yes|"
                   r"oui\s+(go|ok|et continue|ommit|commit)|du coup|voila|svp|stp)[\s.!]*$", re.I)
FORM = re.compile(r"(Revue des sujets|·\s*\d+\s*:|^\d+\s*:\s*(oui|non|si ))", re.I)


def _texts(msg):
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return ""


def _tooluses(msg):
    c = msg.get("content")
    out = []
    if isinstance(c, list):
        for x in c:
            if isinstance(x, dict) and x.get("type") == "tool_use":
                out.append((x.get("name"), x.get("input") or {}))
    return out


def _week_of(ts):
    try:
        d = dt.datetime.fromisoformat(str(ts)[:19])
    except Exception:
        return None
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _week_bounds(key):
    y, w = int(key[:4]), int(key[6:])
    monday = dt.date.fromisocalendar(y, w, 1)
    return monday, monday + dt.timedelta(days=6)


def transcripts_dir():
    # transcripts du projet courant : ~/.claude/projects/<cwd encodé>
    enc = "-" + str(Path.cwd()).lstrip("/").replace("/", "-")
    d = Path.home() / ".claude" / "projects" / enc
    return d if d.is_dir() else None


def scan(tdir):
    """Parcourt les transcripts -> {week: {prompts:[...], files:Counter, n_raw:int}}."""
    weeks = collections.defaultdict(lambda: {"prompts": [], "files": collections.Counter(), "n_raw": 0, "seen": set()})
    for f in glob.glob(str(tdir / "*.jsonl")):
        for line in open(f, encoding="utf-8", errors="ignore"):
            try:
                d = json.loads(line)
            except Exception:
                continue
            t = d.get("type"); ts = d.get("timestamp", ""); wk = _week_of(ts)
            if not wk:
                continue
            if t == "user":
                txt = _texts(d.get("message", {})).strip()
                if not txt or txt.startswith(("<", "Caveat", "[Request", "This session")):
                    continue
                weeks[wk]["n_raw"] += 1
                if NOISE.match(txt) or FORM.search(txt) or len(txt) < 12:
                    continue                                    # bruit : écarté
                key = txt[:140]
                if key in weeks[wk]["seen"]:
                    continue
                weeks[wk]["seen"].add(key)
                weeks[wk]["prompts"].append({"ts": ts[:16], "text": txt[:600]})
            elif t == "assistant":
                for name, inp in _tooluses(d.get("message", {})):
                    if name in ("Write", "Edit", "NotebookEdit") and inp.get("file_path"):
                        weeks[wk]["files"][os.path.basename(inp["file_path"])] += 1
    return weeks


def git_week(root, monday, sunday):
    try:
        out = subprocess.run(["git", "-C", root, "log",
                              f"--since={monday} 00:00", f"--until={sunday} 23:59",
                              "--pretty=format:%ad|%s", "--date=format:%Y-%m-%d"],
                             capture_output=True, text=True, timeout=10).stdout
        return [l.split("|", 1) for l in out.splitlines() if "|" in l]
    except Exception:
        return []


def history_dir():
    return Path.cwd() / "weekly-reports"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mission", default="sinbad")
    ap.add_argument("--week", help="AAAA-Www (ISO). Sans ça : --list sous-entendu.")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--json", help="écrit la matière dans ce fichier")
    ap.add_argument("--project-root", default=str(Path.cwd()))
    args = ap.parse_args()

    tdir = transcripts_dir()
    if not tdir:
        print("[!] pas de transcripts pour ce projet (~/.claude/projects/<projet>)."); return 2
    weeks = scan(tdir)
    hist = history_dir()
    done = {p.stem for p in hist.glob("*.md")} if hist.is_dir() else set()

    if args.list or not args.week:
        print("Semaines (projet courant) :\n")
        print(f"  {'semaine':10} {'du':10} {'au':10} {'prompts':>8}  historique")
        print("  " + "-" * 56)
        for wk in sorted(weeks, reverse=True):
            mo, su = _week_bounds(wk)
            tick = "✓ CR en historique" if wk in done else ""
            print(f"  {wk:10} {mo.isoformat():10} {su.isoformat():10} {len(weeks[wk]['prompts']):>8}  {tick}")
        print(f"\n  Historique : {hist}  ({len(done)} CR)")
        print("  Détail d'une semaine : pm run weekly-report --week <AAAA-Www>")
        print("  Le SKILL weekly-report demande la semaine, ajoute mails + sujets (safran), rédige et archive.")
        return 0

    wk = args.week
    if wk not in weeks:
        print(f"[!] semaine {wk} sans prompts. Dispo : {', '.join(sorted(weeks, reverse=True)[:8])}"); return 2
    mo, su = _week_bounds(wk)
    W = weeks[wk]
    matiere = {
        "semaine": wk, "du": mo.isoformat(), "au": su.isoformat(), "mission": args.mission,
        "prompts_bruts": W["n_raw"], "prompts_retenus": len(W["prompts"]),
        "prompts": W["prompts"],
        "fichiers_touches": W["files"].most_common(30),
        "git": git_week(args.project_root, mo, su),
        "cr_existant": (wk in done),
        "note": "Matière LOCALE (prompts + fichiers + git). Les mails et le suivi des sujets s'ajoutent "
                "en session via safran. Le skill synthétise le CR et l'archive dans weekly-reports/.",
    }
    if args.json:
        Path(args.json).write_text(json.dumps(matiere, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"matière écrite : {args.json}  ({len(W['prompts'])} prompts retenus sur {W['n_raw']} bruts)")
    else:
        print(json.dumps(matiere, ensure_ascii=False, indent=2))
    if wk in done:
        print(f"\n[i] un CR existe déjà : {hist / (wk + '.md')} (le skill le rend tel quel, ou régénère sur demande).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
