#!/usr/bin/env python3
"""ticket-changes - qui a modifie quels tickets du tracker, quand, quoi (lecture seule).

Generique et config-driven : projet/board/identifiants viennent du profil et de l'env
(framework/lib/jira.py). Repere les ECRASEMENTS de description via les sections perdues (une
version enregistree par-dessus une autre). N'ecrit jamais.

  python3 changes.py <mission>                      depuis ce matin 00h00
  python3 changes.py <mission> --since 10:30        depuis aujourd'hui 10h30
  python3 changes.py <mission> --since 2026-09-22T17:00
  python3 changes.py <mission> --last-point         depuis 10h30 la veille ouvree (lundi -> vendredi)
  python3 changes.py <mission> --me                 inclut aussi les ecritures de l'auteur "assistant"
  python3 changes.py <mission> --self "Nom"         nom de l'auteur assistant a exclure par defaut

L'auteur "assistant" a exclure par defaut (ses passes d'outillage noient le signal) est pris, dans
l'ordre : --self, puis profil `jira.assistant_author`, puis env PMF_JIRA_SELF. Sans lui, tout est inclus.
"""
import os, re, sys, urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # racine du depot (pour `framework.lib`)
from framework.lib import jira as jira_lib
from framework.lib import profile as prof

SECTION = re.compile(r"^h[1-6]\.\s*(.+)$|^\*\*(.+?)\*\*$", re.M)   # titres wiki Jira ou markdown gras


def veille_ouvree(h=10, m=30):
    jour = datetime.now() - timedelta(days=1)
    while jour.weekday() >= 5:            # samedi / dimanche -> on remonte
        jour -= timedelta(days=1)
    return jour.replace(hour=h, minute=m, second=0, microsecond=0)


def depuis_argument(argv):
    if "--last-point" in argv:
        return veille_ouvree()
    if "--since" in argv:
        v = argv[argv.index("--since") + 1]
        if "T" in v:
            return datetime.fromisoformat(v)
        h, m = v.split(":")
        return datetime.now().replace(hour=int(h), minute=int(m), second=0, microsecond=0)
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def sections(txt):
    return {a or b for a, b in SECTION.findall(txt or "")}


def self_author(mission, argv):
    if "--self" in argv:
        return argv[argv.index("--self") + 1]
    j = prof.load(mission)["profile"].get("jira", {})
    return j.get("assistant_author") or os.environ.get("PMF_JIRA_SELF")


def rapport(mission, depuis, avec_self):
    j = jira_lib.Jira(mission)
    moi = self_author(mission, sys.argv)
    jql = f'project = {j.project} AND updated >= "{depuis:%Y-%m-%d %H:%M}" ORDER BY key'
    issues = j.search(jql, fields=["summary"], max_results=200)
    lignes = []
    for i in issues:
        d = j._api("GET", f"/rest/api/3/issue/{i['key']}?expand=changelog&fields=summary")
        for e in d.get("changelog", {}).get("histories", []):
            quand = datetime.fromisoformat(e["created"][:19])
            if quand < depuis:
                continue
            auteur = e.get("author", {}).get("displayName", "?")
            if moi and auteur == moi and not avec_self:
                continue
            for it in e.get("items", []):
                detail = ""
                if it.get("field") == "description":
                    av, ap = it.get("fromString") or "", it.get("toString") or ""
                    perdues, gagnees = sections(av) - sections(ap), sections(ap) - sections(av)
                    detail = f"{len(av)} -> {len(ap)} car."
                    if perdues:
                        detail += "  ⚠ sections perdues : " + ", ".join(sorted(perdues))
                    if gagnees:
                        detail += "  + " + ", ".join(sorted(gagnees))
                lignes.append((quand, i["key"], i["fields"]["summary"], auteur, it.get("field"), detail))
    lignes.sort()
    horsmoi = "" if avec_self or not moi else f", hors {moi}"
    if not lignes:
        print(f"Aucune modification depuis {depuis:%d/%m %H:%M}{horsmoi}")
        return
    print(f"Modifications depuis {depuis:%d/%m %H:%M}{horsmoi} — {len(lignes)} au total\n")
    for quand, cle, titre, auteur, champ, detail in lignes:
        print(f"{quand:%d/%m %H:%M}  {cle:9} {auteur:20} {champ or '':12} {detail}")
        print(f"{'':17}{titre[:70]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: changes.py <mission> [--since ... | --last-point] [--me] [--self \"Nom\"]"); sys.exit(2)
    rapport(sys.argv[1], depuis_argument(sys.argv), "--me" in sys.argv)
