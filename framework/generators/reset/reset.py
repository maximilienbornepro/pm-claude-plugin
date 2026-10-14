#!/usr/bin/env python3
"""reset - remet A ZERO ce que le framework a cree dans un dossier de PROJET DE TEST.

COMMANDE A FORT RISQUE (elle SUPPRIME). Garde-fous :
  - dry-run par defaut : montre ce qui serait supprime, ne touche a rien ;
  - BACKUP horodate OBLIGATOIRE avant toute suppression (copie complete du dossier cible) ;
  - cibles DELIMITEES : seuls les sous-dossiers standard (templates/project-management-tree.yml)
    et les artefacts generes (*.drawio, *_generated.html) presents dans le dossier cible ;
  - REFUS d'un chemin sensible (OneDrive/SharePoint synchronise, depot SINBAD d'origine) sans --force ;
  - la suppression sur un Drive synchronise reste bloquee par le hook garde_suppression.

    python3 reset.py --target <dossier de test>                 # dry-run (rien supprime)
    python3 reset.py --target <dossier de test> --apply         # backup puis suppression
    python3 reset.py --target <...> --apply --backup-dir <...>   # ou mettre le backup
    python3 reset.py --target <...> --apply --force              # outrepasser le refus chemin sensible
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof  # noqa: E402

SENSIBLE = ("cloudstorage", "onedrive", "sharepoint", "/documents/sinbad")


def _standard_folders():
    try:
        tree = prof._load_yaml(ROOT / "templates" / "project-management-tree.yml")
        return [r["drive"] for r in tree.get("project_management", []) if r.get("drive")]
    except Exception:
        return []


def _affected(target):
    """Items du framework presents dans target : sous-dossiers standard + artefacts generes."""
    std = set(_standard_folders())
    folders = [d for d in target.iterdir() if d.is_dir() and d.name in std]
    arts = [f for f in target.rglob("*") if f.is_file() and
            (f.suffix == ".drawio" or f.name.endswith("_generated.html"))]
    return folders, arts


def _backup(target, backup_dir):
    ts = time.strftime("%Y%m%d-%H%M%S")
    dest = Path(backup_dir) / f"{target.name}-{ts}"
    shutil.copytree(target, dest)
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="dossier de projet (de TEST) a remettre a zero")
    ap.add_argument("--apply", action="store_true", help="execute (backup puis suppression)")
    ap.add_argument("--backup-dir", help="ou ecrire le backup (defaut : <parent>/_pm-reset-backups)")
    ap.add_argument("--force", action="store_true", help="outrepasser le refus d'un chemin sensible")
    a = ap.parse_args()

    target = Path(a.target).expanduser().resolve()
    if not target.is_dir():
        print(f"[!] cible introuvable : {target}"); return 2

    low = str(target).lower()
    if any(s in low for s in SENSIBLE) and not a.force:
        print(f"[!] REFUS : « {target} » ressemble a un espace reel (OneDrive/SharePoint/SINBAD).")
        print("    reset est reserve a un projet de TEST. --force pour outrepasser (a tes risques).")
        return 2

    folders, arts = _affected(target)
    print(f"Cible : {target}")
    print(f"Sous-dossiers standard presents : {len(folders)}   artefacts generes : {len(arts)}")
    for d in folders:
        print(f"  [dossier] {d.name}/")
    for f in arts:
        print(f"  [artefact] {f.relative_to(target)}")
    if not folders and not arts:
        print("Rien du framework a remettre a zero dans ce dossier.")
        return 0

    backup_dir = a.backup_dir or str(target.parent / "_pm-reset-backups")
    if not a.apply:
        print(f"\nDry-run : RIEN supprime. Avec --apply : backup complet -> {backup_dir}/, puis suppression.")
        return 0

    # --apply : BACKUP d'abord, toujours
    print(f"\nBackup complet de la cible avant suppression...")
    try:
        dest = _backup(target, backup_dir)
    except Exception as e:
        print(f"[!] backup echoue ({e}) -> ABANDON, rien supprime.")
        return 2
    print(f"  backup : {dest}")

    removed = 0
    for d in folders:
        try:
            shutil.rmtree(d); removed += 1; print(f"  supprime : {d.name}/")
        except Exception as e:
            print(f"  ! echec : {d.name}/ ({e})")
    for f in arts:
        try:
            if f.exists():
                f.unlink(); removed += 1; print(f"  supprime : {f.relative_to(target)}")
        except Exception as e:
            print(f"  ! echec : {f} ({e})")
    print(f"\nFait : {removed} element(s) supprime(s). Backup conserve : {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
