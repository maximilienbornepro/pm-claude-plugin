#!/usr/bin/env python3
"""scaffold Notion - LECTURE SEULE (dry-run).

Compare le miroir Notion attendu (templates/project-management-tree.yml, colonne
`notion`) a un instantane des pages reelles sous `notion.project_management_root`,
et liste ce qui MANQUERAIT. Ne cree rien, ne deplace rien, ne supprime rien.

L'instantane des pages Notion est produit par Claude via le connecteur (le connecteur
n'est pas appelable depuis un script). On le passe en JSON : une liste de titres de
pages (chaines) presents sous Project Management.

    python3 scaffold_notion.py --pages pages.json
    claude-produit-le-json | python3 scaffold_notion.py --pages -

Une entree du miroir marquee `notion: "à confirmer"` (ex. SPV) n'a pas de page evidente :
elle est listee a part comme "a arbitrer" (le scaffold proposerait une page, apres
arbitrage et dry-run, jamais d'ecriture ici).
"""
import argparse
import json
import sys
import unicodedata
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]                        # .../pm-framework
sys.path.insert(0, str(ROOT / 'framework' / 'lib'))
import profile as prof                         # noqa: E402
import links                                    # noqa: E402

ACONF = "à confirmer"


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().casefold()


def folder_link(mission, drive_folder):
    """Lien vers le dossier, adapte au file_store du profil (SharePoint navigateur, OneDrive/local chemin)."""
    try:
        profile = prof.load(mission)["profile"]
    except Exception:
        return None
    return links.folder_link(profile, f"02 - Project Management/{drive_folder}")


def _store_label(mission):
    """Nom lisible du magasin de fichiers du profil (SharePoint / OneDrive / Drive / local)."""
    try:
        s = (prof.load(mission)["profile"].get("file_store") or "sharepoint").lower()
    except Exception:
        s = "sharepoint"
    return {"sharepoint": "SharePoint", "onedrive": "OneDrive",
            "local": "le dossier local", "drive": "le Drive"}.get(s, "le Drive")


def _page_body(link, store_label):
    """Gabarit du corps d'une page creee : lien dossier (TOUJOURS), role, placeholders, et
    une checklist 'ce qui manque pour etre complete'. Rien n'est invente : tout est a renseigner."""
    if link:
        head = f"📁 [Ouvrir le dossier dans {store_label}]({link})"
        manque_lien = []
    else:
        head = f"📁 Ouvrir le dossier dans {store_label} : `<lien du dossier a renseigner>`"
        manque_lien = [f"Ajouter le lien vers le dossier {store_label} (non resolu automatiquement)"]
    checklist = manque_lien + [
        "Decrire le role reel de la page (remplacer le placeholder ci-dessus)",
        "Lister les fichiers cles du dossier en tableau (Titre | Fichier | Dossier | Contenu ; "
        "lien par fichier : URL encodee + ?web=1)",
        "Preciser le responsable / la frequence de mise a jour si pertinent",
    ]
    return (
        f"{head}\n\n"
        "**A quoi sert cette page**\n"
        "<placeholder : role de la page en une phrase factuelle - ex. « Suivi de… », « Reference de… »>\n\n"
        "**Contenu attendu**\n"
        "- <placeholder : premier element attendu>\n"
        "- <placeholder : documents lies, en tableau>\n\n"
        "**A completer pour etre legitime**\n"
        + "\n".join(f"- [ ] {c}" for c in checklist)
    )


def emit_plan(mission, rows, missing, databases=None):
    databases = databases or {}
    """Spec de creation par page manquante, pour que Claude cree via le connecteur APRES le test jetable.
    Chaque page porte TOUJOURS un lien vers son dossier (Drive/SharePoint/OneDrive), un role placeholder
    et une checklist de ce qui manque pour etre legitime."""
    root = ""
    try:
        root = prof.load(mission)["profile"]["notion"]["project_management_root"]
    except Exception:
        pass
    store_label = _store_label(mission)
    drive_by_notion = {r['notion']: r.get('drive', '') for r in rows if r.get('notion')}
    nb_by_title = {r['notion']: r.get('notion_db') for r in rows if r.get('notion')}
    plan = []
    for title in missing:
        folder = drive_by_notion.get(title, "")
        link = folder_link(mission, folder) if folder else None
        entry = {"title": title, "parent_root": root, "drive_folder": folder,
                 "body_markdown": _page_body(link, store_label)}
        dbk = nb_by_title.get(title)
        if dbk:
            entry["database"] = _db_block(dbk, databases)   # page qui porte une base (Gantt, Suivi des sujets)
        plan.append(entry)
    return plan


def _db_block(db_key, databases):
    """Spec d'une base Notion a creer dans la page (titre, vue, proprietes) + EXEMPLES du sample."""
    spec = databases.get(db_key) or {}
    rows = []
    sample_path, rows_key = spec.get("sample"), spec.get("rows_from")
    if sample_path:
        try:
            s = prof._load_yaml(ROOT / sample_path) or {}
            rows = (s.get(rows_key) or [])[:5] if rows_key else []
        except Exception:
            rows = []
    return {"title": spec.get("title", db_key), "views": spec.get("views", []),
            "properties": spec.get("properties", []), "exemples": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', help="JSON (liste de titres de pages reelles) ; '-' = stdin")
    ap.add_argument('--mission', default='sinbad', help="profil, pour les liens SharePoint et le parent Notion")
    ap.add_argument('--emit-plan', action='store_true',
                    help="emet la spec de creation des pages manquantes (JSON) ; N'ECRIT PAS dans Notion")
    args = ap.parse_args()

    try:
        pm_front = (prof.load(args.mission)["profile"].get("pm_front") or "notion").lower()
    except Exception:
        pm_front = "notion"
    if pm_front != "notion":
        print(f"[!] Mission '{args.mission}' : pm_front = '{pm_front}' (pas Notion).")
        print("    L'espace de pilotage est un Drive : aucune page Notion a creer ici.")
        print("    L'arbo et l'index (un README/doc par dossier) sont geres par le scaffold Drive.")
        return 0

    tree = prof._load_yaml(ROOT / 'templates' / 'project-management-tree.yml')
    rows = tree['project_management']
    notion_only = tree.get('notion_only') or []        # pages Notion sans dossier Drive (ex. Hebdo)
    databases = tree.get('databases') or {}            # bases portees par une page (Planning Gantt, Sujets)
    pages = rows + notion_only
    wanted = [r['notion'] for r in pages if r.get('notion') and r['notion'] != ACONF]
    aconf = [r for r in rows if r.get('notion') == ACONF]

    if not args.pages:
        print("Pas d'instantane (--pages) : voici le miroir attendu a verifier dans Notion.")
        for w in wanted:
            print(f"  - {w}")
        if aconf:
            print("\nA arbitrer (pas de page evidente) :")
            for r in aconf:
                print(f"  ? {r['drive']}  (page Notion a definir)")
        sys.exit(0)

    raw = sys.stdin.read() if args.pages == '-' else Path(args.pages).read_text(encoding='utf-8')
    titles = json.loads(raw)
    if isinstance(titles, dict):                # tolere {"pages": [...]}
        titles = titles.get('pages') or titles.get('titles') or []
    have = {_norm(t) for t in titles}

    present = [w for w in wanted if _norm(w) in have]
    missing = [w for w in wanted if _norm(w) not in have]

    print(f"Miroir Notion (Project Management)")
    print(f"Attendus : {len(wanted)}   presents : {len(present)}   manquants : {len(missing)}")
    print()
    for w in wanted:
        print(f"  [{'x' if _norm(w) in have else ' '}] {w}")
    print()
    if missing:
        print("Dry-run : pages ATTENDUES absentes (a creer apres validation, creer-si-absent) :")
        for m in missing:
            print(f"  + {m}")
    else:
        print("Toutes les pages attendues du miroir sont presentes. (idempotent)")
    if aconf:
        print("\nA arbitrer (miroir `à confirmer`, pas de page evidente) :")
        for r in aconf:
            there = any(_norm(r['drive'].split(' - ')[-1]) in h or 'spv' in h
                        for h in have) if 'SPV' in r['drive'] else False
            print(f"  ? {r['drive']}"
                  + ("  (une page type SPV semble exister)" if there else "  (aucune page evidente)"))
    if args.emit_plan and missing:
        plan = emit_plan(args.mission, pages, missing, databases)
        print("\n--- PLAN DE CREATION (pages manquantes) ---")
        print("Le script N'ECRIT PAS dans Notion. Claude cree ces pages via le connecteur UNIQUEMENT")
        print("apres : (1) validation du contenu, (2) test « page jetable » confirmant l'absence de")
        print("notification, (3) creation sous le parent, jamais a la racine de l'espace.")
        print(json.dumps(plan, ensure_ascii=False, indent=2))

    print("\nLecture seule : ce script ne cree, ne deplace et ne supprime rien.")


if __name__ == '__main__':
    main()
