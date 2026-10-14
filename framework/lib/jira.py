#!/usr/bin/env python3
"""Client Jira generique du pm-framework - lecture seule par defaut, sans dependance.

Config (base, projet, board) lue DEPUIS LE PROFIL (`profiles/<mission>/profile.yml`),
identifiants depuis l'environnement (JIRA_EMAIL, JIRA_TOKEN ; base JIRA_BASE optionnelle,
sinon derivee de jira.instance). Si les identifiants manquent dans l'env, on peut pointer
un fichier .env via PMF_JIRA_ENV (ex. celui de scan-jira). Les secrets ne sont jamais affiches.

CLI (lecture seule) : python3 jira.py <mission>
  -> liste les sprints actifs/futurs du board et compte les tickets du projet.
"""
import os, sys, json, base64, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import profile as prof  # noqa: E402


def _load_env():
    if os.environ.get("JIRA_EMAIL") and os.environ.get("JIRA_TOKEN"):
        return
    p = os.environ.get("PMF_JIRA_ENV")
    if p and Path(p).exists():
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


class Jira:
    def __init__(self, mission):
        _load_env()
        j = prof.load(mission)["profile"]["jira"]
        self.base = (os.environ.get("JIRA_BASE") or f"https://{j['instance']}").rstrip("/")
        self.project = j["project_key"]
        self.board = j["board"]
        email, token = os.environ["JIRA_EMAIL"], os.environ["JIRA_TOKEN"]
        self.auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()

    def _api(self, method, path, data=None):
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(data).encode() if data is not None else None,
            method=method,
            headers={"Authorization": self.auth, "Content-Type": "application/json",
                     "Accept": "application/json"})
        b = urllib.request.urlopen(req).read()
        return json.loads(b) if b else {}

    def sprints(self, states="active,future"):
        p = f"/rest/agile/1.0/board/{self.board}/sprint?maxResults=50&state={states}"
        return self._api("GET", p).get("values", [])

    def search(self, jql, fields=None, max_results=100):
        res, tok = [], None
        while True:
            body = {"jql": jql, "fields": fields or ["summary"], "maxResults": max_results}
            if tok:
                body["nextPageToken"] = tok
            r = self._api("POST", "/rest/api/3/search/jql", body)
            res += r.get("issues", [])
            tok = r.get("nextPageToken")
            if not tok:
                return res


if __name__ == "__main__":
    m = sys.argv[1] if len(sys.argv) > 1 else "sinbad"
    j = Jira(m)
    print(f"Base   : {j.base}  projet={j.project}  board={j.board}  (config lue du profil)")
    sp = j.sprints()
    print(f"Sprints actifs/futurs : {len(sp)}")
    for s in sp:
        print(f"  - [{(s.get('state') or '?'):6s}] #{s.get('id')}  {s.get('name')}")
    n = len(j.search(f"project={j.project}", ["summary"]))
    print(f"Tickets {j.project} (lecture seule) : {n}")
