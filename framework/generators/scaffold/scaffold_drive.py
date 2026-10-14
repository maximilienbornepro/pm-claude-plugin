#!/usr/bin/env python3
"""scaffold Drive - compare l'arborescence standard a un dossier reel ; cree-si-absent sur --apply.

Compare l'arborescence standard (templates/project-management-tree.yml) a un dossier
Project Management reel, et liste ce qui MANQUERAIT. Dry-run par defaut : ne touche a rien.
Avec --apply, cree UNIQUEMENT les dossiers manquants (mkdir, creer-si-absent) : jamais
d'ecrasement, jamais de suppression, jamais de deplacement. Un dossier ne notifie personne.

    python3 scaffold_drive.py --pm "<chemin vers 02 - Project Management>"            # dry-run
    python3 scaffold_drive.py --pm "<...>" --apply                                     # cree les manquants
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]                       # .../pm-framework
sys.path.insert(0, str(ROOT / 'framework' / 'lib'))
import profile as prof                        # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pm', required=True, help="chemin du dossier '02 - Project Management'")
    ap.add_argument('--apply', action='store_true', help="cree les dossiers manquants (creer-si-absent)")
    args = ap.parse_args()

    tree = prof._load_yaml(ROOT / 'templates' / 'project-management-tree.yml')
    wanted = [n['drive'] for n in tree['project_management']]
    pm = Path(args.pm)

    if not pm.is_dir():
        print(f"[!] dossier introuvable : {pm}")
        sys.exit(2)

    existing = {d.name for d in pm.iterdir() if d.is_dir()}
    present = [w for w in wanted if w in existing]
    missing = [w for w in wanted if w not in existing]

    print(f"Cible    : {pm}")
    print(f"Attendus : {len(wanted)}   presents : {len(present)}   manquants : {len(missing)}")
    print()
    for w in wanted:
        print(f"  [{'x' if w in existing else ' '}] {w}")
    print()
    if not missing:
        print("Rien a creer : l'arborescence est deja complete. (idempotent)")
        return
    if not args.apply:
        print("Dry-run : seraient CREES (relancer avec --apply pour creer, creer-si-absent) :")
        for m in missing:
            print(f"  + {m}")
        return
    print("Creation des dossiers manquants (creer-si-absent, aucun ecrasement) :")
    for m in missing:
        d = pm / m
        try:
            d.mkdir(exist_ok=True)            # jamais parents : le PM doit deja exister
            print(f"  + cree : {m}")
        except OSError as e:
            print(f"  ! echec : {m} ({e})")
    print("Fait. Rien de supprime ni deplace.")


if __name__ == '__main__':
    main()
