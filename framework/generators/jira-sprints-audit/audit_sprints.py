#!/usr/bin/env python3
"""Audit de sprints generique - LECTURE SEULE, pilote par le profil.

Par-dessus le client Jira du framework : pour les sprints actifs/futurs du board
(lu du profil), il controle ce qui ne depend QUE de Jira :
  - charge estimee par sprint (somme des estimations) ;
  - tickets d'un sprint sans estimation ;
  - tickets deja faits (Done) encore dans un sprint ;
  - blocages inverses (un bloquant place dans un sprint posterieur) ;
  - dates des sprints.

Ce qui depend d'un plan de mission (objectifs, versions V1/V1.1, cibles par pole)
reste au niveau du profil : ce n'est pas porte ici.

    PMF_JIRA_ENV=<.../.env> python3 audit_sprints.py <mission>
N'ecrit rien.
"""
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
import jira as jira_mod  # noqa: E402

DONE = {"Closing", "Closed", "Done", "Canceled", "Cancelled"}
SPRINT_FIELD = "customfield_10020"


def sprint_of(cf, board_ids):
    if not cf:
        return None
    cand = [s for s in cf if isinstance(s, dict) and s.get("id") in board_ids]
    if not cand:
        return None
    for st in ("active", "future"):
        m = [s for s in cand if s.get("state") == st]
        if m:
            return m[-1]["id"]
    return cand[-1]["id"]


def hours(issue_fields):
    sec = issue_fields.get("timeoriginalestimate") or 0
    return round(sec / 3600, 1)


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 else "sinbad"
    J = jira_mod.Jira(mission)

    sp = J.sprints("active,future")
    sp.sort(key=lambda s: (s.get("startDate") or "9999", s.get("id")))
    order = {s["id"]: i for i, s in enumerate(sp)}        # rang chronologique
    name = {s["id"]: f"{s.get('name')} [{s.get('state')}]" for s in sp}
    board_ids = set(order)

    fields = [SPRINT_FIELD, "status", "summary", "issuetype", "timeoriginalestimate", "issuelinks"]
    issues = J.search(f"project={J.project}", fields)
    F = {i["key"]: i["fields"] for i in issues}
    SP = {k: sprint_of(f.get(SPRINT_FIELD), board_ids) for k, f in F.items()}

    print(f"Audit sprints - {mission}  (board {J.board}, lecture seule)")
    print(f"{len(issues)} tickets {J.project}, {len(sp)} sprints actifs/futurs\n")

    print("== Charge par sprint (estimation, hors tickets Done)")
    for sid in sorted(order, key=lambda x: order[x]):
        ks = [k for k, s in SP.items() if s == sid and F[k]["status"]["name"] not in DONE]
        h = round(sum(hours(F[k]) for k in ks), 1)
        sans = sum(1 for k in ks if not F[k].get("timeoriginalestimate"))
        print(f"  {name[sid]:30s} {len(ks):3d} tickets   {h:6.1f} h   {sans} sans estimation")

    print("\n== Tickets d'un sprint sans estimation (comptent 0)")
    n = 0
    for k, s in SP.items():
        if s and not F[k].get("timeoriginalestimate") and F[k]["status"]["name"] not in DONE:
            print(f"  {k}  {name[s].split(' [')[0]}  {F[k]['summary'].strip()}"); n += 1
    print(f"  ({n})")

    done_in = [(k, s) for k, s in SP.items() if s and F[k]["status"]["name"] in DONE]
    print(f"\n== Tickets termines, par sprint (informatif, c'est normal) : {len(done_in)}")
    par = {}
    for k, s in done_in:
        par[s] = par.get(s, 0) + 1
    for sid in sorted(par, key=lambda x: order[x]):
        print(f"  {name[sid].split(' [')[0]:24s} {par[sid]} terminated")

    print("\n== Blocages inverses (le bloquant est dans un sprint posterieur)")
    n = 0
    for k, f in F.items():
        if f["status"]["name"] in DONE or SP[k] is None:
            continue
        for l in f.get("issuelinks", []):
            o = (l.get("outwardIssue") or {}).get("key")
            if (o and l["type"]["outward"] == "blocks" and o in F
                    and F[o]["status"]["name"] not in DONE and SP[o] is not None
                    and order[SP[k]] > order[SP[o]]):
                print(f"  {k} ({name[SP[k]].split(' [')[0]}) bloque {o} ({name[SP[o]].split(' [')[0]})"); n += 1
    print(f"  ({n})")

    print("\n== Dates des sprints")
    for sid in sorted(order, key=lambda x: order[x]):
        s = next(x for x in sp if x["id"] == sid)
        print(f"  {name[sid]:30s} {(s.get('startDate') or '?')[:10]} -> {(s.get('endDate') or '?')[:10]}")


if __name__ == "__main__":
    main()
