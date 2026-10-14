#!/usr/bin/env python3
"""Hook PreToolUse : interdit toute suppression/deplacement destructeur - generique.

Deux cibles, codees en dur (regles consortium) :

 1) Drive synchronise (OneDrive/SharePoint) : rm / rmdir / unlink / trash / mv d'un
    fichier ou dossier synchronise. La synchro propage la suppression vers le
    SharePoint partage, et un fichier Office supprime puis recree perd son
    identifiant d'element SharePoint et cesse de se synchroniser. On REFUSE : on
    reecrit TOUJOURS en place (cat copie > fichier), jamais rm/mv.

 2) Notion : deplacer une page (notion-move-pages) recree des droits explicites et
    NOTIFIE tout le conteneur (mail d'invitation a tous les membres). On REFUSE tout
    deplacement ; pour retirer une page d'une base, on ne la deplace pas : on
    PROPOSE la suppression a l'utilisateur, qui la fait dans Notion (aucune notif).

Complement de garde_office.py (qui vise l'ECRITURE des fichiers Office), de
pas_ecraser_jira.py (descriptions Jira) et de la carte framework/NOTIFICATIONS.md.

Portabilite : marqueur du Drive synchronise via PMF_SYNC_MARKER (defaut "OneDrive").
La LECTURE et la COPIE (cat, cp) restent autorisees ; seul le destructeur est bloque.
"""
import json, os, re, sys

MARKER = os.environ.get("PMF_SYNC_MARKER", "OneDrive")
# chemin synchronise : contient le marqueur ; on autorise les espaces (ex. « 06 - Risques »),
# on s'arrete aux guillemets et separateurs shell.
PATH = MARKER + r'[^"\'|>&;\n]*'


def deny(msg):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": msg,
    }}))
    sys.exit(0)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool = data.get("tool_name", "") or ""
    inp = data.get("tool_input") or {}

    # --- Notion : aucun deplacement de page --------------------------------
    if tool.endswith("notion-move-pages") or tool.endswith("notion-move-page"):
        deny("Deplacement de page Notion refuse : un deplacement recree des droits "
             "explicites et NOTIFIE tout le conteneur (mail d'invitation a tous les membres). "
             "Pour retirer une page d'une base, ne la deplace pas : PROPOSE la suppression "
             "a l'utilisateur, qui la fait dans Notion (le connecteur ne supprime pas, et "
             "une suppression ne notifie personne).")

    # --- Drive synchronise : pas de rm / mv / trash ------------------------
    if tool == "Bash":
        cmd = inp.get("command", "")
        if "onedrive_xlsx.py" in cmd:   # le helper fait ses reecritures en place
            sys.exit(0)
        destructeur = (
            re.search(r'\b(?:rm|rmdir|unlink|trash)\b[^\n|;&]*["\']?' + PATH, cmd)
            or re.search(r'\bmv\b[^\n|;&]*["\']?' + PATH, cmd)
        )
        if destructeur:
            deny("Suppression/deplacement refuse sur le Drive synchronise (" + MARKER + ") : "
                 "la synchro propage la suppression vers l'espace partage, et un fichier Office "
                 "recree perd son identifiant d'element et cesse de se synchroniser. On reecrit "
                 "TOUJOURS en place (cat copie > fichier), jamais rm/mv. Regle du Drive partage.")

    sys.exit(0)


if __name__ == "__main__":
    main()
