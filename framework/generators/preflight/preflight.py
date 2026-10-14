#!/usr/bin/env python3
"""preflight - verifie que les systemes CONNECTES sont bien ceux de la mission (LECTURE SEULE).

Le risque : un meme compte Claude peut avoir PLUSIEURS Notion / SharePoint connectes. Sans garde,
un generateur pourrait ecrire dans le MAUVAIS Notion. Ce preflight ancre l'identite attendue (depuis
le profil) et dit, systeme par systeme, comment confirmer qu'on est bien connecte au bon avant toute
ecriture. Il NE REMPLACE PAS la verification Notion (seul le connecteur, donc Claude, peut la faire) :
il la cadre et verifie ce qui est verifiable par script (Drive local, Jira si env present).

    python3 preflight.py <mission>

N'ecrit rien.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof  # noqa: E402


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 else "sinbad"
    P = prof.load(mission)["profile"]
    n = P.get("notion", {}) or {}
    d = P.get("drive", {}) or {}
    j = P.get("jira", {}) or {}

    print(f"PREFLIGHT « {P.get('name', mission)} » - verifier qu'on est connecte aux BONS systemes")
    print("=" * 70)

    # --- Notion (connecteur : seul Claude peut verifier) ---
    print("\n[Notion]  (verification par Claude via le connecteur - OBLIGATOIRE avant toute ecriture)")
    pmr = n.get("project_management_root")
    wsr = n.get("workspace_root")
    print(f"  racine Project Management attendue : {pmr or '(non defini)'}")
    print(f"     titre attendu : {n.get('expect_pm_title') or '(a confirmer)'}")
    print(f"  page workspace attendue            : {wsr or '(non defini)'}")
    print(f"     titre attendu : {n.get('expect_workspace_title') or '(a confirmer)'}")
    print("  >> Claude DOIT faire : notion-fetch de la racine Project Management, puis :")
    print("       - 404 / introuvable        -> MAUVAIS workspace connecte : NE RIEN ECRIRE,")
    print("                                      demander a l'utilisateur de basculer la connexion Notion.")
    print("       - titre != titre attendu   -> idem (mauvais espace).")
    print("       - trouve + titre == attendu-> workspace CORRECT, ecriture possible (sous garde-fous).")

    # --- Drive / SharePoint (verifiable par script : existence du chemin local) ---
    print("\n[Drive / SharePoint]")
    site = d.get("web_site")
    root = d.get("root")
    root_exp = os.path.expanduser(str(root)) if root else None
    exists = bool(root_exp) and Path(root_exp).is_dir()
    print(f"  site attendu   : {site or '(non defini)'}")
    print(f"  racine locale  : {root_exp or '(non defini)'}")
    print(f"  -> {'OK, le dossier local existe' if exists else 'ABSENT : dossier local introuvable (synchro ? mauvais poste ?)'}")
    print("  >> Avant d'ecrire un fichier Office : confirmer qu'il est bien SOUS cette racine, et que le")
    print("     'web_site' correspond a la mission (un autre site = mauvais SharePoint).")

    # --- Jira (verifiable si env present) ---
    print("\n[Jira]")
    print(f"  instance : {j.get('instance')}   cloud_id : {j.get('cloud_id')}   projet : {j.get('project_key')}")
    env = os.environ.get("JIRA_EMAIL") and os.environ.get("JIRA_TOKEN") or os.environ.get("PMF_JIRA_ENV")
    if env:
        try:
            import jira as jmod  # noqa: E402
            J = jmod.Jira(mission)
            res = J.search(f"project = {j.get('project_key')}", max_results=1)
            ok = isinstance(res, dict) or res is not None
            print(f"  -> connexion Jira OK, projet « {j.get('project_key')} » accessible.")
        except Exception as e:
            print(f"  -> ATTENTION : projet « {j.get('project_key')} » non confirme ({str(e)[:80]}).")
    else:
        print("  -> (pas d'identifiants Jira en env : verification sautee ; cloud_id/projet font foi dans le profil.)")

    print("\n" + "=" * 70)
    print("Regle : tant que le preflight Notion n'est pas VERT (racine trouvee + bon titre),")
    print("        AUCUNE ecriture Notion. Idem : pas d'ecriture Office hors de la racine Drive attendue.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
