#!/usr/bin/env python3
"""Rend le Weekly report (modele actuel, 4 sections) a partir du store d'activites.

Source de verite : un fichier JSONL (une ligne = une activite datee, typee, avec
lien). Le rendu reprend EXACTEMENT le modele de la page Notion "Weekly report" :

  **Activites realisees**                <- type "produit"  (precede du lien Suivi des sujets)
  **Difficultes / Points d'attention**   <- type "bloquant"
  **Ce qui manque pour avancer**         <- type "attends_autres"
  **Plan d'action semaine prochaine**    <- type "attendu_moi"

  python3 build_weekly.py --store profiles/sinbad/suivi/activites.jsonl
  python3 build_weekly.py --store ... --week 2026-10-12     # semaine contenant ce jour
  python3 build_weekly.py --store ... --since 2026-10-06 --until 2026-10-12

Aucune dependance externe. N'ecrit rien dehors : imprime le markdown sur stdout.
"""
import argparse, datetime, json, sys
from pathlib import Path

# Ordre et libelles des sections = modele Weekly report (ne pas reordonner).
# Les 4 types du store (= 4 categories de la DB) se projettent sur les 4 sections :
#   produit -> Activites realisees ; bloquant -> Difficultes ;
#   attends_autres -> Ce qui manque ; attendu_moi -> Plan d'action.
SECTIONS = [
    ("produit",        "**Activités réalisées**"),
    ("bloquant",       "**Difficultés / Points d'attention**"),
    ("attends_autres", "**Ce qui manque pour avancer**"),
    ("attendu_moi",    "**Plan d'action semaine prochaine**"),
]
# Section qui porte le lien "Suivi des sujets" en tete.
_LEAD = "produit"


def _lundi(d):
    return d - datetime.timedelta(days=d.weekday())


def _load(store):
    rows = []
    for ln in Path(store).read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            rows.append(json.loads(ln))
    return rows


def _fenetre(args, rows):
    if args.since and args.until:
        return args.since, args.until
    pivot = args.week or (max((r["date"] for r in rows), default=None))
    if not pivot:
        sys.exit("store vide : aucune activite")
    d = datetime.date.fromisoformat(pivot)
    lun = _lundi(d)
    return lun.isoformat(), (lun + datetime.timedelta(days=6)).isoformat()


def _puce(r):
    t = (r.get("theme") or "").strip()
    txt = (r.get("texte") or "").strip()
    lien = (r.get("lien") or "").strip()
    corps = f"**{t}** : {txt}" if t else txt
    if lien:
        corps += f" {lien}"
    return f"- {corps}"


def render(rows, since, until, suivi_link=None, titre=None):
    sel = [r for r in rows if since <= r.get("date", "") <= until]
    deb = datetime.date.fromisoformat(since)
    head = titre or f"## {deb.day:02d}/{deb.month:02d}"
    out = [head, ""]
    for typ, libelle in SECTIONS:
        items = [r for r in sel if r.get("type") == typ]
        if typ == _LEAD:
            out.append(libelle)
            if suivi_link:
                out.append(f"Suivi des sujets : {suivi_link}")
            out += [_puce(r) for r in items]
        else:
            if not items:
                continue
            out.append(libelle)
            out += [_puce(r) for r in items]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True)
    ap.add_argument("--week", help="jour ISO ; rend la semaine (lun-dim) qui le contient")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--suivi-link", help="URL de la base Suivi des sujets (tete de section)")
    ap.add_argument("--titre", help="titre du bloc (defaut ## JJ/MM du lundi de la semaine)")
    a = ap.parse_args()
    rows = _load(a.store)
    since, until = _fenetre(a, rows)
    sys.stdout.write(render(rows, since, until, a.suivi_link, a.titre))


if __name__ == "__main__":
    main()
