#!/usr/bin/env python3
"""Empeche le connecteur Atlassian d'ECRASER une description de ticket - generique.

Le connecteur ecrit sans relire : il remplace la version courante, meme si quelqu'un
l'a modifiee entre-temps (c'est ce qui fait disparaitre des sections entieres). On
force a passer par l'ecriture versionnee du framework, qui relit le ticket juste avant
d'ecrire et abandonne si la description a change - DES QU'UNE DESCRIPTION EXISTE.

Exception : si la description actuelle du ticket est VIDE (ticket fraichement cree,
`createJiraIssue` ne persistant pas toujours la description), il n'y a rien a ecraser.
Le hook laisse alors ecrire par le connecteur. C'est le seul cas ou le connecteur peut
poser une description.

Verification de la description : le hook interroge Jira. Identifiants charges depuis
PMF_JIRA_ENV (fichier .env de la mission) ou depuis l'environnement (JIRA_BASE /
JIRA_EMAIL / JIRA_TOKEN). S'il ne peut pas CONFIRMER que la description est vide (cle
introuvable, Jira injoignable, pas d'identifiants), il REFUSE : on ne risque pas un
ecrasement.

Ce qui reste toujours permis par le connecteur : statut, resume, assignation, libelles,
commentaires, liens.

Auteurs proteges (informatif dans le message) : variable PMF_JIRA_PROTECTED (noms
separes par des virgules).
"""
import base64
import json
import os
import sys
import urllib.request

PROTEGES = [p.strip() for p in os.environ.get("PMF_JIRA_PROTECTED", "").split(",") if p.strip()]

_qui = f" (notamment {', '.join(PROTEGES)})" if PROTEGES else ""
RAISON = (
    "Ecriture de description refusee : le connecteur Atlassian remplace la version courante "
    "sans la relire, et peut ecraser le travail de quelqu'un" + _qui + ". "
    "Passer par l'ecriture versionnee du framework, qui relit le ticket juste avant d'ecrire "
    "et abandonne si la description a change. Le connecteur reste utilisable pour le statut, "
    "le resume, l'assignation, les libelles, les liens et les commentaires. "
    "(Un ticket a la description vide est la seule exception : le connecteur peut alors l'ecrire.)"
)


def contient_description(valeur):
    """La description peut arriver a la racine ou sous « fields »."""
    if isinstance(valeur, dict):
        if any(cle.lower() == "description" for cle in valeur):
            return True
        return any(contient_description(v) for v in valeur.values())
    if isinstance(valeur, list):
        return any(contient_description(v) for v in valeur)
    return False


def trouver_cle(valeur):
    """Repere la cle du ticket (issueIdOrKey, issueKey, key...) dans le tool_input."""
    if isinstance(valeur, dict):
        for cle, v in valeur.items():
            if cle.lower() in ("issueidorkey", "issuekey", "issueid", "key") and isinstance(v, str) and v.strip():
                return v.strip()
        for v in valeur.values():
            trouve = trouver_cle(v)
            if trouve:
                return trouve
    elif isinstance(valeur, list):
        for v in valeur:
            trouve = trouver_cle(v)
            if trouve:
                return trouve
    return None


def _charger_env():
    """Identifiants Jira depuis PMF_JIRA_ENV (si present) puis l'environnement."""
    env_path = os.environ.get("PMF_JIRA_ENV")
    if env_path and os.path.exists(env_path):
        try:
            for l in open(env_path):
                l = l.strip()
                if not l or l.startswith("#") or "=" not in l:
                    continue
                k, v = l.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
        except OSError:
            pass


def _adf_vide(desc):
    """Vrai si la description Jira est absente ou sans aucun texte."""
    if desc is None:
        return True
    if isinstance(desc, str):
        return desc.strip() == ""
    if isinstance(desc, dict):
        textes = []

        def _collect(n):
            if isinstance(n, dict):
                if n.get("type") == "text" and n.get("text"):
                    textes.append(n["text"])
                for v in n.values():
                    _collect(v)
            elif isinstance(n, list):
                for v in n:
                    _collect(v)

        _collect(desc)
        return "".join(textes).strip() == ""
    return False


def description_actuelle_vide(cle):
    """Interroge Jira. Rend True seulement si on a pu CONFIRMER une description vide."""
    _charger_env()
    base = os.environ.get("JIRA_BASE", "").rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_TOKEN", "")
    if not (base and email and token):
        return False
    auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
    url = f"{base}/rest/api/3/issue/{cle}?fields=description"
    req = urllib.request.Request(url, headers={"Authorization": auth, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
    except Exception:
        return False
    return _adf_vide((data.get("fields") or {}).get("description"))


def main():
    try:
        entree = json.load(sys.stdin)
    except Exception:
        return  # entree illisible : on ne bloque rien

    tool_input = entree.get("tool_input") or {}
    if not contient_description(tool_input):
        return  # pas d'ecriture de description : rien a controler

    cle = trouver_cle(tool_input)
    if cle and description_actuelle_vide(cle):
        return  # ticket vide : rien a ecraser, on laisse ecrire

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": RAISON,
            }
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
