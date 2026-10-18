#!/usr/bin/env python3
"""init - amorce une mission : crée son profil à partir des gabarits (A8bis, DM-019).

Parcours CLASSIQUE de démarrage d'un projet, indépendant de l'orchestrateur `cockpit` (qui, lui, est
une OPTION pour résumer l'état d'une mission déjà amorcée). `init` pose les fichiers de
`profiles/<mission>/` qui MANQUENT, à partir des gabarits du moteur ; il ne touche jamais un fichier
existant (create-si-absent, idempotent - cf. FRAMEWORK « ne jamais écraser l'existant »).

Dry-run par DÉFAUT : montre ce qui serait créé. `--apply` écrit réellement.

    python3 framework/generators/init/init.py <mission>            # plan (dry-run)
    python3 framework/generators/init/init.py <mission> --apply     # crée les fichiers manquants
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof  # noqa: E402

# Fichier de profil -> gabarit source (dans le moteur). Les gabarits inline sont posés tels quels.
GABARITS = {
    "profile.yml": ROOT / "config" / "profile.example.yml",
    "pipeline.yml": ROOT / "config" / "pipeline.example.yml",
    "gate.yml": ROOT / "framework" / "generators" / "gate" / "gtf.sample.yml",
}

# Fichiers posés depuis un contenu inline (méthode, traçabilité, routage) : squelettes à remplir.
INLINE = {
    "method.yaml": (
        "# La méthode de la mission, en DONNÉE (A4). Barèmes, seuils, trames, chaîne de traçabilité.\n"
        "# Les outils lisent ici et calculent ; le modèle ne produit que la preuve. À remplir au fil de l'eau.\n\n"
        "baremes: {}\n\n"
        "seuils:\n"
        "  gate_defaut: 90\n\n"
        "trames: {}\n\n"
        "tracabilite:\n"
        "  phases: [cadrage, build, recette, prod]\n"
        "  ordre: []            # ex. - { maillon: ticket, proprietaire: \"PM\", exigible_des: cadrage }\n"
    ),
    "tracabilite.yml": (
        "# Les items de la chaîne de traçabilité (données de la mission). La DÉFINITION de la chaîne\n"
        "# (ordre, propriétaires, phases) vit dans method.yaml > tracabilite.\n\n"
        "phase_courante: cadrage\n"
        "items: []              # ex. - { id: TR-01, label: \"...\", liens: { besoin: true, ticket: false } }\n"
    ),
    "routing.yml": (
        "# Exceptions de routage de compte UNIQUEMENT (le compte se dérive des métadonnées, A1/DM-010).\n"
        "# Vide = tout est dérivé. Remplir seulement les commandes qui échappent à la politique du profil.\n"
    ),
}


def plan(mission):
    """(à_créer, déjà_là) : chemins relatifs, selon ce qui existe dans profiles/<mission>/."""
    base = Path(prof.mission_dir(mission))
    noms = list(GABARITS) + list(INLINE)
    a_creer, deja = [], []
    for nom in noms:
        (deja if (base / nom).exists() else a_creer).append(nom)
    return base, a_creer, deja


def contenu(nom):
    if nom in INLINE:
        return INLINE[nom]
    src = GABARITS[nom]
    return src.read_text(encoding="utf-8") if src.exists() else f"# gabarit {src.name} introuvable\n"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    apply = "--apply" in sys.argv
    if not args:
        print("usage: pm run init <mission> [--apply]"); return 2
    mission = args[0]
    base, a_creer, deja = plan(mission)

    print(f"Amorçage de la mission {mission}  ->  {base}")
    print(f"  (dossier {'existant' if base.exists() else 'à créer'})\n")
    if deja:
        print("Déjà présents (laissés tels quels) :")
        for n in deja:
            print(f"  = {n}")
        print()
    if not a_creer:
        print("Rien à créer : le profil est déjà amorcé.")
    else:
        print(f"{'Créés' if apply else 'À créer'} depuis les gabarits :")
        for n in a_creer:
            print(f"  + {n}")

    if a_creer and apply:
        base.mkdir(parents=True, exist_ok=True)
        for n in a_creer:
            (base / n).write_text(contenu(n), encoding="utf-8")
        print("\nÉcrit.")
    elif a_creer:
        print("\n(dry-run : rien écrit. Relancer avec --apply pour créer.)")

    print("\nSuite du parcours classique :")
    print(f"  pm run setup {mission}            # compléter le profil, champ par champ")
    print(f"  pm run drive-scaffold {mission} / notion-scaffold {mission}   # l'arborescence (create-si-absent)")
    print(f"  pm run cockpit {mission}          # (option) où en est la mission, que fait-on ?")
    return 0


if __name__ == "__main__":
    sys.exit(main())
