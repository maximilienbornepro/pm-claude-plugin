#!/usr/bin/env python3
"""Generateur de registre des risques - generique, pilote par la config.

Deux responsabilites, strictement separees :

  1. LECTURE (implementee et prouvee ici) : lit le classeur des risques en
     s'appuyant UNIQUEMENT sur le mapping de colonnes de `profiles/<mission>/risks.yml`
     (aucune coordonnee de cellule en dur), et rend le registre courant.
  2. ECRITURE (decrite, GARDEE, jamais executee ici) : le flux pilote par formulaire
     est documente dans SKILL.md. L'ecriture ne part que derriere le flag `write.enabled`
     de la config ET apres validation en session, via le helper d'ecriture chirurgicale
     `framework/harness/onedrive_xlsx.py`. Dans cette passe, le chemin d'ecriture refuse
     de s'executer.

Config lue depuis `profiles/<mission>/risks.yml` (meme parseur sans dependance que profile.py).
Le classeur est synchronise (OneDrive/SharePoint) : ce module ne l'ouvre qu'en lecture.

CLI (lecture seule) :
    python3 risks.py <mission>                 # rend le registre courant (tableau)
    python3 risks.py <mission> --raw           # dump brut {ref: valeur} des cellules lues
    python3 risks.py <mission> --propose        # (stub) montre le flux de proposition, n'ecrit rien
"""
import os
import sys
import glob
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]                                  # .../pm-framework
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(ROOT / "framework" / "harness"))

import profile as prof          # noqa: E402  (mini-YAML sans dependance)
import onedrive_xlsx as ox      # noqa: E402  (ecriture chirurgicale + read_cells)


# ---------------------------------------------------------------- config
def load_config(mission):
    """Lit profiles/<mission>/risks.yml via le loader du framework (0 dependance)."""
    path = prof.mission_dir(mission) / "risks.yml"
    if not path.exists():
        raise SystemExit(f"config absente : {path}")
    return prof._load_yaml(path)


def resolve_file(cfg):
    """Resout le chemin local du classeur, de la facon la plus portable possible.

    Ordre : 1) variable d'env nommee dans la config (file.abs_override_env) ;
            2) racine Drive (env PMF_DRIVE_ROOT) + chemin relatif file.path ;
            3) repli : recherche du motif file.glob sous les dossiers CloudStorage,
               pour la preuve de lecture quand la racine locale est "a confirmer".
    Ne lit jamais une racine en dur propre a un poste."""
    f = cfg["file"]
    env_name = f.get("abs_override_env")
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]

    rel = f.get("path")
    droot = os.environ.get("PMF_DRIVE_ROOT")
    if droot and rel:
        cand = os.path.join(droot, rel)
        if os.path.exists(cand):
            return cand

    pattern = f.get("glob")
    if pattern:
        home = str(Path.home())
        for base in (
            f"{home}/Library/CloudStorage",
            home,
        ):
            hits = glob.glob(os.path.join(base, "**", pattern), recursive=True)
            hits = [h for h in hits if os.path.isfile(h)]
            if hits:
                return sorted(hits, key=os.path.getmtime)[-1]
    raise SystemExit(
        "classeur introuvable : definir "
        f"${env_name} ou $PMF_DRIVE_ROOT, ou ajuster file.glob dans risks.yml"
    )


# ---------------------------------------------------------------- lecture
def read_register(cfg, path):
    """Lit le registre via le mapping de colonnes de la config. LECTURE SEULE.

    Renvoie (meta, header, rows) ou :
      - meta   : lignes d'en-tete du classeur (titre, projet...) au-dessus du tableau
      - header : {champ: libelle lu dans la ligne d'en-tete}
      - rows   : liste de dicts {champ: valeur}, un par risque non vide
    """
    cells = ox.read_cells(path)                         # {ref: texte}, 1re feuille
    cols = cfg["columns"]                               # {champ: lettre}
    lay = cfg["layout"]
    hrow = int(lay["header_row"])
    first = int(lay["first_data_row"])
    last = lay.get("last_data_row")

    # champs mappes a une vraie lettre de colonne (on ignore les "a confirmer")
    fields = {k: v for k, v in cols.items() if isinstance(v, str) and v.isalpha()}

    meta = [cells[f"A{r}"] for r in range(1, hrow) if cells.get(f"A{r}")]
    header = {field: cells.get(f"{col}{hrow}", "") for field, col in fields.items()}

    rows = []
    r = first
    end = int(last) if last else 10_000
    while r <= end:
        rec = {field: cells.get(f"{col}{r}", "") for field, col in fields.items()}
        label_field = "label" if "label" in rec else next(iter(fields))
        if not any(rec.values()):
            if not last:
                break                                   # 1re ligne vide = fin de table
        else:
            rec["_row"] = r
            rows.append(rec)
        r += 1
    return meta, header, rows


# ---------------------------------------------------------------- rendu
def _wrap(text, width):
    out, line = [], ""
    for word in (text or "").split():
        if len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out or [""]


def render_table(cfg, meta, header, rows):
    scale = cfg.get("scale", {})
    levels = scale.get("levels")
    fr = scale.get("labels_fr") or {}
    print("=" * 78)
    for m in meta:
        print(m)
    print("=" * 78)
    print(f"{len(rows)} risques lus  (echelle : {', '.join(levels) if levels else 'a confirmer'})\n")

    for rec in rows:
        label = rec.get("label", "")
        prob = rec.get("probability", "")
        imp = rec.get("impact", "")
        detail = rec.get("detail", "")
        pf = f"{prob}" + (f" ({fr[prob]})" if prob in fr else "")
        imf = f"{imp}" + (f" ({fr[imp]})" if imp in fr else "")
        print(f"• [{rec.get('_row')}] {label}")
        print(f"    Proba : {pf:16s}  Impact : {imf}")
        for ln in _wrap(detail, 72):
            print(f"    {ln}")
        print()


# ---------------------------------------------------------------- ecriture (GARDEE)
def propose(cfg, meta, header, rows):
    """Flux de MISE A JOUR pilote par formulaire - decrit, PAS execute ici.

    Le flux complet est dans SKILL.md : formulaire de validation -> proposition
    cellule par cellule -> ecriture chirurgicale unique via onedrive_xlsx.save(),
    apres controle de fraicheur distant en session. Dans cette passe, aucune
    ecriture n'est possible : la fonction s'arrete sur le garde-fou."""
    print("Flux de proposition (LECTURE SEULE dans cette passe) :")
    print("  1. Annexer les sujets Notion traites/ouverts + la projection Jira (lecture).")
    print("  2. Reevaluer chaque risque, construire la proposition cellule par cellule.")
    print("  3. Afficher le tableau actualise (avant -> apres) et attendre le OUI du formulaire.")
    print("  4. Controle de fraicheur SharePoint (lastModifiedDateTime) EN SESSION.")
    print("  5. backup() horodate, puis UNE SEULE ecriture via set_cells()/save().")
    print()
    if not cfg.get("write", {}).get("enabled", False):
        print("write.enabled = false -> chemin d'ecriture GARDE, rien n'est ecrit. STOP.")
        return
    raise SystemExit(
        "Garde-fou : l'ecriture ne s'execute jamais depuis ce generateur en l'etat. "
        "Elle se fait en session, apres validation, via le helper onedrive_xlsx."
    )


# ---------------------------------------------------------------- CLI
def main(argv):
    mission = next((a for a in argv if not a.startswith("--")), "sinbad")
    cfg = load_config(mission)
    path = resolve_file(cfg)

    if "--raw" in argv:
        for ref, v in sorted(ox.read_cells(path).items(),
                             key=lambda kv: ox._colnum(kv[0])[::-1]):
            print(f"{ref}: {v}")
        return 0

    meta, header, rows = read_register(cfg, path)

    if "--propose" in argv:
        render_table(cfg, meta, header, rows)
        propose(cfg, meta, header, rows)
        return 0

    render_table(cfg, meta, header, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
