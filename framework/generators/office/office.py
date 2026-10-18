#!/usr/bin/env python3
"""office - crée un fichier Office (xlsx) si absent, et l'édite de façon CHIRURGICALE si présent.

Le pendant Excel de `notion-scaffold`, pour le disque OneDrive synchronisé (pas le connecteur M365,
qui est en lecture seule) :

  - fichier ABSENT  -> le CRÉE depuis le template `trackers/excel/<objet>.yml` (xlsx_write, stdlib) ;
  - fichier PRÉSENT -> l'édite au cas par cas (append / set) via `onedrive_xlsx` (chirurgical, jamais
    openpyxl : images et dessins préservés), avec SAUVEGARDE d'abord. Jamais d'écrasement global.

Stdlib uniquement : compatible avec le garde-fou `garde_office` (qui refuse openpyxl / .save() / rm / mv).
Dry-run par DÉFAUT. Placement dans un dossier synchronisé = dérouler le `_deroule-office` (fraîcheur,
écriture unique, jamais écraser le travail d'autrui) : ce générateur fait l'écriture unique et la sauvegarde.

    pm run office <mission> <objet> --out <chemin.xlsx>                 # plan (dry-run)
    pm run office <mission> <objet> --out <chemin.xlsx> --apply          # crée si absent
    pm run office <mission> <objet> --out <chemin.xlsx> --append "a|b|c|d" --apply   # ajoute une ligne
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(ROOT / "framework" / "harness"))
import templates as TPL      # noqa: E402
import xlsx_write            # noqa: E402
import onedrive_xlsx as OX   # noqa: E402
import profile as prof       # noqa: E402


def _projet(mission):
    try:
        return prof.load(mission)["profile"].get("name") or mission
    except Exception:
        return mission


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("object", help="objet du registre (risks, raci...)")
    ap.add_argument("--mission", default="sinbad")
    ap.add_argument("--out", help="chemin du .xlsx (dans le dossier synchronisé pour remonter sur SharePoint)")
    ap.add_argument("--apply", action="store_true", help="écrit réellement (sinon dry-run)")
    ap.add_argument("--append", help="ajoute UNE ligne : valeurs séparées par | (ordre des colonnes)")
    ap.add_argument("--sheet", help="feuille à éditer (défaut : la 1re)")
    args = ap.parse_args()

    tpl = TPL.load("excel", args.object)
    if not tpl:
        print(f"[!] pas de template excel/{args.object}. Objets : {', '.join(TPL.OBJECTS)}"); return 2
    sheet = args.sheet or tpl.get("sheet") or tpl.get("main_sheet") or tpl.get("title") or "Feuille"
    out = Path(args.out) if args.out else (ROOT / f"_office/{args.object}.xlsx")
    exists = out.exists()
    print(f"Objet : {args.object}  (template excel/{args.object})   ->   {out}")
    print(f"  fichier : {'EXISTANT' if exists else 'absent'}   feuille : {sheet}\n")

    # ---- création si absent --------------------------------------------------
    if not exists:
        rows = xlsx_write.rows_from_template(tpl, _projet(args.mission))
        print(f"{'CRÉATION' if args.apply else 'À CRÉER (dry-run)'} depuis le template : {len(rows)} ligne(s).")
        apercu = [r for r in rows if r][:6]
        for r in apercu:
            print("  | " + " | ".join(str(c) for c in r))
        if args.apply:
            out.parent.mkdir(parents=True, exist_ok=True)
            xlsx_write.write(str(out), sheet, rows)
            print(f"\nCréé : {out}")
        else:
            print("\n(dry-run : rien écrit. --apply pour créer.)")
        return 0

    # ---- édition chirurgicale si présent -------------------------------------
    if args.append is None:
        print("Fichier déjà présent. Édition CHIRURGICALE (create-si-absent respecté : on n'écrase pas).")
        print("  Ajouter une ligne : --append \"val1|val2|...\" --apply")
        print("  (les colonnes suivent l'ordre du template : " + ", ".join(tpl.get("columns") or []) + ")")
        return 0
    vals = [v.strip() for v in args.append.split("|")]
    cells = {xlsx_write._colref(i + 1): v for i, v in enumerate(vals) if v != ""}
    print(f"{'AJOUT' if args.apply else 'À AJOUTER (dry-run)'} d'une ligne : " + " | ".join(vals))
    if args.apply:
        bak = OX.backup(str(out), str(out.parent))        # sauvegarde horodatée d'abord
        print(f"  sauvegarde : {bak}")
        data = OX.append_row(str(out), cells)
        with open(out, "wb") as f:
            f.write(data)
        print(f"  écrit (une seule écriture) : {out}")
    else:
        print("\n(dry-run : rien écrit. --apply pour ajouter.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
