#!/usr/bin/env python3
"""Empeche le connecteur Atlassian de reecrire une description de ticket - generique.

Le connecteur ecrit sans relire : il remplace la version courante, meme si quelqu'un
l'a modifiee entre-temps (c'est ce qui fait disparaitre des sections entieres). On
force a passer par l'ecriture versionnee du framework, qui relit le ticket juste avant
d'ecrire et abandonne si la description a change.

Ce qui reste permis par le connecteur : statut, resume, assignation, libelles,
commentaires, liens. Seule la description est bloquee.

Auteurs proteges (dont la version fait toujours foi) : liste optionnelle via la variable
d'environnement PMF_JIRA_PROTECTED (noms separes par des virgules). Purement informatif
dans le message ; le blocage s'applique a toute ecriture de description.
"""
import json
import os
import sys

PROTEGES = [p.strip() for p in os.environ.get("PMF_JIRA_PROTECTED", "").split(",") if p.strip()]

_qui = f" (notamment {', '.join(PROTEGES)})" if PROTEGES else ""
RAISON = (
    "Ecriture de description refusee : le connecteur Atlassian remplace la version courante "
    "sans la relire, et peut ecraser le travail de quelqu'un" + _qui + ". "
    "Passer par l'ecriture versionnee du framework, qui relit le ticket juste avant d'ecrire "
    "et abandonne si la description a change. Le connecteur reste utilisable pour le statut, "
    "le resume, l'assignation, les libelles, les liens et les commentaires."
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


def main():
    try:
        entree = json.load(sys.stdin)
    except Exception:
        return  # entree illisible : on ne bloque rien

    if not contient_description(entree.get("tool_input") or {}):
        return

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
