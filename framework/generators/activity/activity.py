#!/usr/bin/env python3
"""Generateur de suivi d'activite - point d'entree pilote par la config de mission.

Lit `profiles/<mission>/suivi.yml` (store, transcripts, lien Suivi, DB Notion, themes)
et enchaine les briques du dossier : collect.py, build_weekly.py, sync_notion.py.
Aucun chemin de mission en dur ; zero dependance (mini-YAML du framework).

CLI (lecture seule par defaut) :
    python3 suivi.py <mission> collect [--date J | --since J --until J]   # prompts pertinents
    python3 suivi.py <mission> check                                      # valide le store
    python3 suivi.py <mission> weekly [--week J]                          # bloc Weekly report
    python3 suivi.py <mission> sync                                       # dry-run vers la DB privee
    python3 suivi.py <mission> sync --apply                               # upsert reel (NOTION_TOKEN)
"""
import argparse, datetime, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]                                  # .../pm-framework
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(HERE.parent))

import profile as prof          # noqa: E402  (mini-YAML sans dependance)
import collect as col           # noqa: E402
import build_weekly as bw       # noqa: E402

TYPES = {"produit", "attendu_moi", "attends_autres", "bloquant"}


def load_config(mission):
    path = prof.mission_dir(mission) / "activity.yml"
    if not path.exists():
        raise SystemExit(f"config absente : {path}")
    return prof._load_yaml(path)


def _store(cfg):
    return ROOT / cfg["store"]


def do_collect(cfg, a):
    d = Path(os.path.expanduser(cfg["project_dir"]))
    files = sorted(str(p) for p in d.glob("*.jsonl"))
    since = a.date or a.since or datetime.date.today().isoformat()
    until = a.date or a.until or since
    for e in col.collect(files, since, until):
        if cfg.get("projet"):
            e["projet"] = cfg["projet"]
        sys.stdout.write(json.dumps(e, ensure_ascii=False) + "\n")


def do_check(cfg, a):
    themes = set(cfg.get("themes") or [])
    errs, n = [], 0
    for i, ln in enumerate(_store(cfg).read_text(encoding="utf-8").splitlines(), 1):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        n += 1
        try:
            r = json.loads(ln)
            datetime.date.fromisoformat(r["date"])
        except Exception as ex:
            errs.append(f"l.{i} : ligne invalide ({ex})"); continue
        if r.get("type") not in TYPES:
            errs.append(f"l.{i} : type inconnu {r.get('type')!r}")
        if themes and r.get("theme") and r["theme"] not in themes:
            errs.append(f"l.{i} : theme hors liste {r['theme']!r}")
        if not (r.get("texte") or "").strip():
            errs.append(f"l.{i} : texte vide")
    for e in errs:
        print(e)
    print(f"-- {n} activites, {len(errs)} anomalie(s)")
    return 1 if errs else 0


def do_weekly(cfg, a):
    rows = bw._load(_store(cfg))
    since, until = bw._fenetre(argparse.Namespace(since=None, until=None, week=a.week), rows)
    sys.stdout.write(bw.render(rows, since, until, cfg.get("suivi_link")))


def do_sync(cfg, a):
    import subprocess
    cmd = [sys.executable, str(HERE.parent / "sync_notion.py"),
           "--store", str(_store(cfg)), "--db", cfg["notion_db"]]
    if not a.apply:
        cmd.append("--dry-run")
    return subprocess.call(cmd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mission")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--date"); c.add_argument("--since"); c.add_argument("--until")
    sub.add_parser("check")
    w = sub.add_parser("weekly")
    w.add_argument("--week", help="jour ISO ; rend la semaine (lun-dim) qui le contient")
    s = sub.add_parser("sync")
    s.add_argument("--apply", action="store_true", help="ecrit vraiment (sinon dry-run)")
    a = ap.parse_args()
    cfg = load_config(a.mission)
    fn = {"collect": do_collect, "check": do_check, "weekly": do_weekly, "sync": do_sync}[a.cmd]
    return fn(cfg, a) or 0


if __name__ == "__main__":
    sys.exit(main())
