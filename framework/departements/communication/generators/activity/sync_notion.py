#!/usr/bin/env python3
"""Upsert du store d'activites vers la DB Notion PRIVEE de suivi.

Deux usages, au choix :
  1) Via l'API officielle Notion (integration interne, jeton NOTION_TOKEN) : ce
     script cree/ met a jour une page par activite. La DB privee doit etre partagee
     avec l'integration. --dry-run imprime ce qui serait ecrit, sans rien envoyer.
  2) Via le connecteur MCP Notion (pilote par Claude) : meme logique d'upsert,
     cle = (date, texte). C'est la voie utilisee tant qu'aucun NOTION_TOKEN
     n'est configure.

  NOTION_TOKEN=secret_xxx python3 sync_notion.py --store ... --db <db_id> [--dry-run]

Rien n'est supprime. L'upsert evite les doublons (cle date|texte).
Aucune notification : la DB est privee (espace prive de l'utilisateur).
"""
import argparse, json, os, sys, urllib.request
from pathlib import Path

API = "https://api.notion.com/v1"
VER = "2022-06-28"


def _load(store):
    rows = []
    for ln in Path(store).read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            rows.append(json.loads(ln))
    return rows


def _req(method, path, token, body=None):
    r = urllib.request.Request(API + path, method=method,
                               data=json.dumps(body).encode() if body is not None else None,
                               headers={"Authorization": f"Bearer {token}",
                                        "Notion-Version": VER, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r).read())


def _props(e):
    TYPE = {"produit": "Produit", "bloquant": "Bloquant",
            "attends_autres": "J'attends des autres", "attendu_moi": "Attendu de moi"}
    p = {
        "Activité": {"title": [{"text": {"content": e.get("texte", "")[:1900]}}]},
        "Date": {"date": {"start": e["date"]}},
        "Type": {"select": {"name": TYPE.get(e.get("type"), e.get("type", ""))}},
    }
    if e.get("theme"):
        p["Thème"] = {"select": {"name": e["theme"]}}
    if e.get("projet"):
        p["Projet"] = {"select": {"name": e["projet"]}}
    if e.get("lien"):
        p["Lien"] = {"url": e["lien"]}
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True)
    ap.add_argument("--db", required=True, help="id de la DB Notion privee")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rows = _load(a.store)
    if a.dry_run:
        for e in rows:
            print(json.dumps(_props(e), ensure_ascii=False))
        print(f"-- {len(rows)} activites (dry-run, rien envoye)")
        return
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        sys.exit("NOTION_TOKEN absent : passer par le connecteur MCP, ou exporter un jeton d'integration.")
    # cle existante pour l'upsert
    seen = set()
    body = {"page_size": 100}
    while True:
        q = _req("POST", f"/databases/{a.db}/query", token, body)
        for pg in q.get("results", []):
            pr = pg.get("properties", {})
            t = "".join(x["plain_text"] for x in pr.get("Activité", {}).get("title", []))
            d = (pr.get("Date", {}).get("date") or {}).get("start", "")
            seen.add((d, t))
        if not q.get("has_more"):
            break
        body["start_cursor"] = q["next_cursor"]
    n = 0
    for e in rows:
        if (e["date"], e.get("texte", "")) in seen:
            continue
        _req("POST", "/pages", token, {"parent": {"database_id": a.db}, "properties": _props(e)})
        n += 1
    print(f"-- {n} activites creees, {len(rows) - n} deja presentes")


if __name__ == "__main__":
    main()
