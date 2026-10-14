#!/usr/bin/env python3
"""demo - lance un FAUX projet et simule TOUTES les fonctionnalites du framework.

Ne cree rien : aucune ecriture Notion, Jira, Office, gh-pages ni artefact. Le harnais
ANNONCE ce qu'il creerait, sur une mission bidon (profil `demo`), et execute pour de vrai
les seuls validateurs 100 % hors-ligne (schema d'archi) pour prouver que le moteur tourne.

    python3 framework/demo.py [mission]      # defaut : demo
    python3 framework/pm.py demo [mission]

Garantie : le harnais n'ouvre aucune connexion et n'utilise aucun jeton. Tout ce qui
toucherait un systeme externe est affiche en SIMULE, jamais execute.
"""
import sys, subprocess, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# loader de profil sans dependance (charge par chemin, robuste a l'import)
_spec = importlib.util.spec_from_file_location("pmf_profile", ROOT / "framework" / "lib" / "profile.py")
profile = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(profile)

# --- petit vocabulaire d'affichage -----------------------------------------
N_SIM = 0   # actions simulees
N_REAL = 0  # validateurs reels passes
N_FAIL = 0

def hdr(n, title):
    print(f"\n\033[1m{n}. {title}\033[0m")

def sim(verb, what):
    """Une action qui SERAIT faite (jamais executee)."""
    global N_SIM; N_SIM += 1
    print(f"   ~ SIMULE · {verb} {what}")

def note(txt):
    print(f"     {txt}")

def real(label, ok, detail=""):
    global N_REAL, N_FAIL
    if ok: N_REAL += 1; print(f"   ✓ REEL · {label}{(' - ' + detail) if detail else ''}")
    else:  N_FAIL += 1; print(f"   ✗ REEL · {label}{(' - ' + detail) if detail else ''}")


def _sample(rel):
    """Charge un fichier sample du framework (planning/roadmap), ou {} si absent."""
    try:
        return profile._load_yaml(ROOT / rel) or {}
    except Exception:
        return {}


def walk_tree(node, prefix="", depth=0):
    """Enumere les noeuds d'un arbre Notion/Drive (templates/*.yml)."""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            out.append("  " * depth + str(k))
            out += walk_tree(v, prefix, depth + 1)
    elif isinstance(node, list):
        for it in node:
            if isinstance(it, (dict, list)): out += walk_tree(it, prefix, depth)
            else: out.append("  " * depth + str(it))
    return out


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 else "demo"
    base = profile.mission_dir(mission)
    if not base.is_dir():
        print(f"profil inconnu: {mission} (profils: {', '.join(p.name for p in (ROOT/'profiles').iterdir() if p.is_dir())})")
        return 2

    data = profile.load(mission)
    P = data["profile"]; PIPE = data["pipeline"]
    nroot = P.get("notion", {}).get("project_management_root", "(notion root)")
    droot = P.get("drive", {}).get("root", "(drive root)")
    pkey = P.get("jira", {}).get("project_key", "???")
    board = P.get("jira", {}).get("board", "???")
    kd = P.get("key_dates", {})

    print("=" * 72)
    print(f"  FAUX PROJET · mission '{mission}' · {P.get('name','?')} ({P.get('lang','?')})")
    print(f"  Jira {pkey} board {board} · Notion « {nroot} » · gel {kd.get('code_freeze','?')} · MEP {kd.get('mep','?')}")
    print("  RIEN n'est cree. Chaque ligne SIMULE est annoncee, jamais executee.")
    print("=" * 72)

    # 1. Garde-fous -----------------------------------------------------------
    hdr(1, "Garde-fous actifs (hooks)")
    for h, what in [("garde_office", "refuse toute ecriture Office brute (cat>, rm/mv, openpyxl, .save())"),
                    ("garde_suppression", "refuse rm/mv sur Drive synchronise + deplacement de page Notion"),
                    ("pas_ecraser_jira", "refuse qu'une description Jira soit ecrasee sans relecture"),
                    ("journal_usage", "journalise les actions")]:
        note(f"• {h} : {what}")
    note("=> aucune ecriture externe n'est possible sans validation, meme hors demo.")

    # 2 + 3. Scaffold (miroir Notion <-> Drive) ------------------------------
    tree = {}
    try:
        tree = profile._load_yaml(ROOT / "templates" / "project-management-tree.yml") or {}
    except Exception as e:
        note(f"(gabarit d'arbo illisible: {e})")
    pm = [z for z in (tree.get("project_management") or []) if isinstance(z, dict)]
    pages = [z["notion"] for z in pm if z.get("notion") and z["notion"] != "à confirmer"]
    tbc = [z["drive"] for z in pm if z.get("notion") == "à confirmer"]
    roots = tree.get("root") or []

    hdr(2, "Arborescence Notion (scaffold, lecture seule)")
    sim("je creerais", f"{len(pages)} pages sous « {nroot} » (aucune a la racine de l'espace)")
    note("  " + " · ".join(pages))
    if tbc: note("  a confirmer (pas de page evidente) : " + ", ".join(tbc))
    note("comparaison a un instantane Notion ; les pages deja presentes ne sont pas recreees.")

    hdr(3, "Arborescence Drive (scaffold, miroir de Notion)")
    sim("je creerais", f"les dossiers racine sous « {droot} » : {', '.join(roots)}")
    sim("je creerais", f"les {len(pm)} sous-dossiers de « 02 - Project Management » (miroir des pages Notion)")
    note("create-si-absent, jamais d'ecrasement, aucune action qui notifie.")

    # 4. Architecture (VALIDATEUR REEL) --------------------------------------
    hdr(4, "Schema d'architecture (model-first)")
    arch_model = base / "architecture" / "model.json"
    if arch_model.exists():
        try:
            r = subprocess.run([sys.executable, str(ROOT/"framework"/"generators"/"archi"/"architecture.py"), mission],
                               capture_output=True, text=True, timeout=120)
            ok = r.returncode == 0
            tail = (r.stdout or r.stderr).strip().splitlines()
            real("harness du modele d'archi (7 invariants)", ok, tail[-1] if tail else "")
        except Exception as e:
            real("harness du modele d'archi", False, str(e))
    else:
        note(f"(pas de modele {arch_model}, section simulee)")
    sim("je publierais", "3 cibles au meme md5 : 2 artefacts Claude + gh-pages")
    _logos = sorted(p.stem for p in (ROOT/'framework'/'assets'/'logos').glob('*') if p.suffix.lower() not in ('.md',))
    note(f"logos techno communs dispo : {', '.join(_logos)}")

    # 5-6. Projection + plan de sprints --------------------------------------
    hdr(5, "Rapport de projection (depuis Jira) + roadmap")
    sim("je lirais", f"Jira {pkey} (board {board}) en lecture seule, charge restante vs capacite")
    sim("je publierais", "le rapport sur gh-pages + l'artefact Claude (les deux au meme contenu)")
    npl = {}
    try:
        npl = profile._load_yaml(base / "notion-planning.yml") or {}
    except Exception:
        pass
    rm = _sample(npl.get("roadmap") or "framework/generators/projection/roadmap.sample.yml")
    if rm.get("chantiers"):
        note("roadmap (sample) par chantiers :")
        for c in rm["chantiers"]:
            note(f"   . {c.get('chantier'):28s} [{c.get('periode','?'):>5s}]  {c.get('statut','')}")
        note("jalons : " + " · ".join(f"{j.get('jalon')} {j.get('date')}" for j in rm.get("jalons", [])))
    hdr(6, "Plan de sprints (depuis Jira)")
    sim("je decouperais", "le reste V1 par sprint (sprints du board Jira, aucun ticket deplace)")
    sim("je publierais", "le plan sur gh-pages + l'artefact Claude")

    # 7. Sujets Notion --------------------------------------------------------
    hdr(7, "Sujets de suivi (Notion, format Contexte / Action attendue)")
    sim("je creerais", "le sujet « Caler l'environnement de demo » (Contexte + Action attendue)")
    note("format verifie par check_sujet.py (sections, pas de liste a plat >=3, pas de mention @)")
    note("mentions en texte simple, ecriture chirurgicale, seuls les sujets du TPM, rien sans le oui.")

    # 8. Planning Notion ------------------------------------------------------
    hdr(8, "Planning Notion + slide")
    pl = _sample(npl.get("source") or "framework/generators/notion-planning/planning.sample.yml")
    if pl.get("jalons"):
        note("planning (sample) - jalons :")
        for j in pl["jalons"]:
            note(f"   . {j.get('jalon'):14s} {str(j.get('date','')):12s} [{j.get('statut','')}]  {j.get('contenu','')}")
        if pl.get("phases"):
            note("phases : " + " · ".join(f"{p.get('phase')} ({p.get('statut')})" for p in pl["phases"]))
    sim("je reporterais", "le planning sur la page Notion et la slide du deck (garde « demander-avant »)")

    # 9. CR partenaire --------------------------------------------------------
    hdr(9, "CR d'hebdo partenaire")
    for who, lang in (PIPE.get("deliverables", {}).get("cr_partenaire", {}).get("lang", {}) or {}).items():
        sim("je redigerais", f"le CR {who} en {lang.upper()} (rendu texte, NON envoye)")
    note("l'utilisateur envoie lui-meme ; aucun mail ne part du harnais.")

    # 10. Ticket Jira + image -------------------------------------------------
    hdr(10, "Ticket Jira (texte connecteur + image API)")
    sim("je verifierais puis poserais", f"l'image du ticket {pkey}-1 (API ; l'image ne saute jamais)")
    note("le texte passe par le connecteur sous garde-fou ; l'image par l'API, jamais le connecteur.")

    # 11. Risques -------------------------------------------------------------
    hdr(11, "Registre des risques")
    sim("j'ajouterais", "la ligne de risque R-01 au registre (ecriture Office gardee : fraicheur + 1 ecriture)")

    # 12. Suivi d'activite ----------------------------------------------------
    hdr(12, "Suivi d'activite (prompts -> DB Notion privee)")
    sim("je collecterais", "les prompts pertinents de Claude Code (store JSONL local)")
    sim("je creerais / mettrais a jour", "la DB Notion PRIVEE + le bloc Weekly report (aucune notif)")

    # 13. Coherence des docs --------------------------------------------------
    hdr(13, "Coherence des documents de pilotage")
    sim("je verifierais", "GATE <-> Excel sources <-> PPT <-> PNG (perime / OK / different / manquant)")

    # 14. Routines ------------------------------------------------------------
    hdr(14, "Routines planifiees")
    rdir = ROOT / "framework" / "routines"
    routs = sorted(p.name for p in rdir.iterdir() if p.is_dir() and (p/"SKILL.md").exists()) if rdir.is_dir() else []
    sim("j'enregistrerais", f"{len(routs)} routines (taskId « {mission}-<nom> », titre « {mission.upper()} · ... »)")
    for r in routs: note(f"  • {mission}-{r}")
    note("aucune routine n'envoie de notification.")

    # Resume ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print(f"  RESUME : {N_SIM} actions SIMULEES, {N_REAL} validateur(s) REEL(s) passe(s), {N_FAIL} en echec.")
    print("  \033[1mAUCUNE ECRITURE REELLE\033[0m : ni Notion, ni Jira, ni Office, ni gh-pages, ni artefact.")
    print("=" * 72)
    return 1 if N_FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
