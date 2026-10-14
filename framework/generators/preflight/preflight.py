#!/usr/bin/env python3
"""preflight - verifie que TOUS les connecteurs de la session pointent bien la mission (LECTURE SEULE).

Risque : un meme compte Claude peut avoir plusieurs Notion / SharePoint / Figma connectes. Sans garde,
un generateur peut ecrire au MAUVAIS endroit. Regle : on n'ecrit sur un connecteur que s'il est
RENSEIGNE dans `profile.connections` ET que l'identite reellement connectee CORRESPOND.

Ce script enumere les connecteurs attendus, dit pour chacun l'identite attendue (profil) et l'outil
d'identite que Claude doit appeler pour confirmer le compte connecte. Il NE PEUT PAS appeler les
connecteurs lui-meme (seul Claude le peut) : il cadre la verification et bloque ce qui n'est pas
renseigne. Ce qui est verifiable par script (racine Drive locale) est verifie ici.

    python3 preflight.py <mission>

N'ecrit rien. Sortie : OK / A VERIFIER (par Claude) / BLOQUANT (non renseigne).
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof  # noqa: E402

# connecteur -> (libelle, champs attendus, outil d'identite que Claude appelle, comment comparer)
CONNECTORS = [
    ("notion", "Notion",
     ["workspace_id", "workspace_name", "account"],
     "notion-get-self",
     "workspace.id == workspace_id ET workspace.name == workspace_name"),
    ("microsoft365", "Microsoft 365 (SharePoint / OneDrive / Outlook / Teams)",
     ["account", "tenant"],
     "get_me (+ get_granted_scopes)",
     "mail/userPrincipalName == account (le tenant du mail == tenant)"),
    ("figma", "Figma",
     ["account", "team_key"],
     "whoami",
     "email == account ET le team_key figure dans les plans"),
    ("jira", "Jira / Atlassian",
     ["cloud_id", "url"],
     "getAccessibleAtlassianResources",
     "un resource.cloudId == cloud_id (url == url)"),
]


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 else "sinbad"
    P = prof.load(mission)["profile"]
    conns = P.get("connections", {}) or {}

    print(f"PREFLIGHT « {P.get('name', mission)} » - tous les connecteurs doivent pointer la mission")
    print("=" * 72)
    print("Regle : on N'ECRIT PAS sur un connecteur tant qu'il n'est pas RENSEIGNE dans le profil")
    print("        (profile.connections) ET que l'identite connectee CORRESPOND (verif par Claude).\n")

    blocking = 0
    for key, label, fields, tool, how in CONNECTORS:
        cfg = conns.get(key) or {}
        missing = [f for f in fields if not cfg.get(f)]
        if not cfg or missing:
            blocking += 1
            why = "non renseigne" if not cfg else f"champs manquants : {', '.join(missing)}"
            print(f"[BLOQUANT] {label}")
            print(f"   {why} dans profile.connections.{key}")
            print(f"   -> RENSEIGNER d'abord (appeler {tool}, noter l'identite), puis re-preflight. "
                  f"Aucune ecriture sur {label} entre-temps.\n")
            continue
        print(f"[A VERIFIER] {label}")
        for f in fields:
            print(f"   attendu {f} = {cfg.get(f)}")
        print(f"   -> Claude appelle {tool} et confirme : {how}")
        print(f"      si different / introuvable => MAUVAIS compte connecte, NE PAS ECRIRE sur {label}.\n")

    # Verifiable par script : racine Drive locale
    d = P.get("drive", {}) or {}
    root = d.get("root")
    root_exp = os.path.expanduser(str(root)) if root else None
    exists = bool(root_exp) and Path(root_exp).is_dir()
    print("[Drive local]")
    print(f"   site attendu : {d.get('web_site') or '(non defini)'}")
    print(f"   racine locale: {root_exp or '(non defini)'}")
    print(f"   -> {'OK, dossier present' if exists else 'ABSENT : synchro ? mauvais poste ? -> pas d ecriture Office'}\n")

    print("=" * 72)
    if blocking:
        print(f"{blocking} connecteur(s) BLOQUANT(s) : profil incomplet -> AUCUNE ecriture tant que non renseigne + verifie.")
        return 1
    print("Tous les connecteurs sont renseignes. Claude DOIT maintenant confirmer chaque identite")
    print("(outils ci-dessus) : une seule non-conformite = pas d'ecriture sur ce connecteur.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
