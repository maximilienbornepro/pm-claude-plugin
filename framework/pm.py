#!/usr/bin/env python3
"""pm - point d'entree unique du framework (dispatch vers les generateurs).

Tout est en LECTURE SEULE / dry-run par defaut ; les chemins d'ecriture des generateurs
restent derriere leurs propres flags (--apply...) et la validation en session.

    python3 framework/pm.py list
    python3 framework/pm.py run <generateur> <mission> [args...]
    python3 framework/pm.py missions

Exemples :
    python3 framework/pm.py run sprint-audit sinbad
    PMF_JIRA_ENV=.../scan-jira/.env python3 framework/pm.py run projection sinbad
"""
import sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# nom canonique -> (script relatif, une ligne, lecture seule ?)
# Nomenclature : kebab-case ; prefixe par domaine (jira-/notion-/drive-/deck-/docs-) ;
# nom = le livrable, suffixe -audit pour un generateur en lecture seule ; dossier == nom.
GEN = {
    # --- livrables (le dossier porte le meme nom que la commande) ---
    "projection":          ("framework/generators/projection/project.py",            "charge restante vs capacite -> date de fin V1", True),
    "risks":               ("framework/generators/risks/risks.py",                   "registre des risques (lecture ; ecriture gardee)", True),
    "raci":                ("framework/generators/raci/raci.py",                     "matrice RACI + extraits par role (depuis raci.yml)", True),
    "poc":                 ("framework/generators/poc/poc.py",                       "POC React + Material UI depuis les recits (launcher auto)", True),
    "archi":               ("framework/generators/archi/architecture.py",            "harness du schema d'archi (validate, lecture seule)", True),
    "activity":            ("framework/generators/activity/activity.py",             "suivi d'activite : collect / check / weekly / sync (dry-run)", True),
    "deck-gate":           ("framework/generators/deck-gate/deck_gate.py",           "contenu du deck GATE (slides markdown/JSON ; assemblage pptx garde)", True),
    "transcripts":         ("framework/generators/transcripts/read_transcripts.py",  "normalise transcriptions/CR vers {date,title,url,text} (--dump|--files)", True),
    "partner-report":      ("framework/generators/partner-report/cr_partenaire.py",  "mail de suivi d'un call partenaire (--input ; rendu texte, jamais d'envoi)", True),
    # --- domaine Jira ---
    "jira-images":         ("framework/generators/jira-images/jira_image.py",        "images des tickets Jira via API (check ; --apply garde)", True),
    "jira-changes-audit":  ("framework/generators/jira-changes-audit/changes.py",    "qui a modifie quels tickets, quand, quoi (sections perdues)", True),
    "jira-sprints-audit":  ("framework/generators/jira-sprints-audit/audit_sprints.py","audit des sprints Jira (charge, estimations, blocages)", True),
    # --- domaine Notion ---
    "notion-topics-audit": ("framework/generators/notion-topics-audit/check_sujet.py","valide le FORMAT d'un sujet Notion (--body ; lecture seule)", True),
    "notion-scaffold":     ("framework/generators/scaffold/scaffold_notion.py",      "arbo Notion miroir : pages manquantes (--emit-plan)", True),
    # --- domaine Drive ---
    "drive-scaffold":      ("framework/generators/scaffold/scaffold_drive.py",       "arbo Drive : ce qui manque (--apply cree les dossiers)", True),
    # --- domaine docs / transverse ---
    "docs-coherence-audit":("framework/generators/docs-coherence-audit/check_coherence.py","coherence docs : une sortie est-elle a jour vs ses sources", True),
    "gate":                ("framework/generators/gate/gate.py",                     "score les portes (gates) d'une mission et RECOMMANDE ; franchissement = acte humain", True),
    "method":              ("framework/generators/method/method.py",                 "montre la methode de la mission en donnee (baremes, seuils, trames, tracabilite)", True),
    "templates":           ("framework/generators/templates/templates.py",           "registre des templates (objet x solution : sujets/planning/raci/risks, notion/excel)", True),
    "office":              ("framework/generators/office/office.py",                 "cree un xlsx depuis un template excel si absent, l'edite chirurgicalement si present (OneDrive)", False),
    "weekly-report":       ("framework/generators/weekly-report/collect.py",         "CR hebdo du projet (par semaine, archive) depuis les prompts + mails + artefacts ; demande la semaine", True),
    "trace-audit":         ("framework/generators/trace-audit/trace_audit.py",       "ruptures de la chaine de tracabilite (besoin->ticket->POC->test) ; dit ou aller (lecture seule)", True),
    "cockpit":             ("framework/generators/cockpit/cockpit.py",               "porte d'entree : ou en est la mission, que fait-on ? (etat calcule + suite priorisee)", True),
    "tones":               ("framework/lib/set_tone.py",                             "aligne le ton des agents sur pipeline.yml (dry-run)", True),
    "init":                ("framework/generators/init/init.py",                     "amorce une mission : cree le profil depuis les gabarits (create-si-absent ; dry-run, --apply ecrit)", False),
    "setup":               ("framework/generators/setup/setup.py",                   "onboarding : champs manquants d'un profil + suggestions (lecture seule)", True),
    "preflight":           ("framework/generators/preflight/preflight.py",           "verifie qu'on est connecte aux BONS systemes (Notion/SharePoint/Jira) avant d'ecrire", True),
    "reset":               ("framework/generators/reset/reset.py",                   "TEST : remet a zero un dossier de projet (backup oblige ; dry-run ; --apply supprime)", False),
    "agent":               ("framework/generators/agent/agent.py",                   "lance une sous-tache sur un agent : --account (connecteurs) / --model / --agent (specialite)", True),
}

# Anciens noms -> nom canonique. Retro-compatibilite (routines, pipeline, habitudes).
# A retirer une fois toutes les references migrees.
ALIAS = {
    "sprint-audit": "jira-sprints-audit", "ticket-changes": "jira-changes-audit",
    "gate-deck": "deck-gate", "jira-image": "jira-images", "architecture": "archi",
    "suivi": "activity", "scaffold-drive": "drive-scaffold", "scaffold-notion": "notion-scaffold",
    "cr-partenaire": "partner-report", "notion-sujets": "notion-topics-audit",
    "coherence": "docs-coherence-audit", "tone": "tones",
}


def missions():
    # Profils du PROJET courant (<cwd>/profiles ou $PMF_PROFILES) sinon ceux du framework.
    import os
    env = os.environ.get("PMF_PROFILES")
    d = Path(os.path.expanduser(env)) if env and Path(os.path.expanduser(env)).is_dir() \
        else (Path.cwd() / "profiles" if (Path.cwd() / "profiles").is_dir() else ROOT / "profiles")
    return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.is_dir() else []


def do_list():
    print("Generateurs (python3 framework/pm.py run <nom> <mission> [args]) :\n")
    for name, (_, desc, ro) in GEN.items():
        tag = "lecture seule" if ro else "ecriture"
        print(f"  {name:16s} {desc}   [{tag}]")
    print(f"\nMissions : {', '.join(missions()) or '(aucune)'}")


def do_run(argv):
    if not argv:
        print("usage: pm run <generateur> [args...]"); return 2
    name, rest = argv[0], argv[1:]
    name = ALIAS.get(name, name)
    if name not in GEN:
        print(f"generateur inconnu: {name}. 'pm list' pour la liste."); return 2
    script = ROOT / GEN[name][0]
    return subprocess.call([sys.executable, str(script), *rest])


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 1
    cmd = sys.argv[1]
    if cmd == "list":
        do_list(); return 0
    if cmd == "missions":
        print(" ".join(missions())); return 0
    if cmd == "run":
        return do_run(sys.argv[2:])
    if cmd == "demo":
        return subprocess.call([sys.executable, str(ROOT / "framework" / "demo.py"), *sys.argv[2:]])
    print(f"commande inconnue: {cmd}  (list | run | missions | demo)"); return 2


if __name__ == "__main__":
    sys.exit(main())
