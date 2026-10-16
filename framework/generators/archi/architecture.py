#!/usr/bin/env python3
"""architecture - pilote du schéma d'archi (stack-imagery), piloté par la config de mission.

Trois modes (dispatch sur les flags) ; tous lisent `profiles/<mission>/architecture.yml` :

    python3 architecture.py <mission>                       # défaut : VALIDER (lecture seule)
    python3 architecture.py <mission> [--target source|theme|golden]
    python3 architecture.py <mission> --render [-o sortie.html]
    python3 architecture.py <mission> --export drawio [-o sortie.drawio]

- défaut  : lance les 7 invariants de `validate.py` sur l'artefact HTML de la mission
            (chemin lu dans la config, surchargeable par PMF_ARCH_HTML). Ne publie rien.
- --render: génère le HTML interactif depuis le MODÈLE de la mission (`model_json` de la config,
            surchargeable par PMF_ARCH_MODEL) vers une sortie de SCRATCHPAD `<mission>_generated.html`.
            N'écrase JAMAIS `source_html` : la source canonique reste la source de vérité.
- --export: appelle `export_drawio.py` (une page draw.io par écran) pour la mission.

La publication (3 cibles au même md5) reste une écriture gardée, hors de ce périmètre.
"""
import sys, os
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(HERE.parent))
import profile as prof   # noqa: E402
import validate as V     # noqa: E402

KEYMAP = {"source": "source_html", "theme": "theme_html", "golden": "golden_html"}


def _opt(flag):
    """Valeur d'un flag `--x valeur` sur la ligne de commande, ou None."""
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("-"):
            return sys.argv[i + 1]
    return None


def _cfg(mission):
    return prof._load_yaml(prof.mission_dir(mission) / "archi.yml")


def do_validate(mission):
    target = _opt("--target") or "source"
    cfg = _cfg(mission)
    path = os.environ.get("PMF_ARCH_HTML") or cfg[KEYMAP[target]]
    if not Path(path).exists():
        print(f"[!] artefact introuvable : {path}"); sys.exit(2)
    html = open(path, encoding="utf-8").read()

    print(f"Architecture {mission} - harness (lecture seule)")
    print(f"Cible : {target}  ->  {path}\n")
    ok = True
    for titre, fn in V.CHECKS:
        viol = fn(html)
        if viol:
            ok = False
            print(f"ECHEC  {titre}")
            for x in viol[:10]:
                print(f"       - {x}")
            if len(viol) > 10:
                print(f"       … (+{len(viol)-10} autres)")
        else:
            print(f"OK     {titre}")
    print("\n" + ("TOUT PASSE - prêt pour publication (gardée)." if ok
                  else "DES INVARIANTS SONT CASSES - ne pas publier."))
    sys.exit(0 if ok else 1)


def do_render(mission):
    import build_html as B  # noqa: E402
    # PMF_ARCH_MODEL : rendu depuis un modèle direct, SANS exiger profiles/<mission>/architecture.yml
    env_model = os.environ.get("PMF_ARCH_MODEL")
    cfg = None if env_model else _cfg(mission)
    model_path = env_model or cfg["model_json"]
    if not Path(model_path).exists():
        print(f"[!] modèle introuvable : {model_path}"); sys.exit(2)
    out = _opt("-o") or str(ROOT.parent / "scratchpad" / f"{mission}_generated.html")

    # garde-fou : ne JAMAIS écrire sur source_html / theme_html / golden_html de la mission
    protected = {os.path.realpath(cfg[v]) for v in KEYMAP.values() if cfg and cfg.get(v)}
    if os.path.realpath(out) in protected:
        print(f"[!] refus : la sortie {out} est un artefact canonique de la mission (source/theme/golden).")
        sys.exit(2)

    print(f"Architecture {mission} - rendu model-first")
    print(f"Modèle : {model_path}")
    B.build_html_file(model_path, out)
    print(f"Écrit  : {out}   (scratchpad, source_html intacte)")

    # draw.io PAR ECRAN : regenere a chaque rendu, dans le dossier configure (archi.yml > drawio_dir),
    # surchargeable par PMF_ARCH_DRAWIO_DIR. Un fichier <vue>.drawio par ecran. N'ecrit que des .drawio.
    ddir = (cfg.get("drawio_dir") if cfg else None) or os.environ.get("PMF_ARCH_DRAWIO_DIR")
    if ddir:
        import export_drawio as X  # noqa: E402
        import json as _json
        model = _json.load(open(model_path, encoding="utf-8"))
        files = X.write_per_screen(model, ddir, prof.mission_dir(mission) / "logos")
        print(f"draw.io par écran ({len(files)}) -> {ddir}")
        for f in files:
            print(f"   . {Path(f).name}")


def do_export(mission):
    fmt = None
    if "--export" in sys.argv:
        i = sys.argv.index("--export")
        if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("-"):
            fmt = sys.argv[i + 1]
    if fmt not in (None, "drawio"):
        print(f"[!] format d'export non supporté : {fmt} (seul 'drawio' est géré)"); sys.exit(2)
    import export_drawio as X  # noqa: E402
    argv = ["export_drawio", mission]
    out = _opt("-o")
    if out:
        argv += ["-o", out]
    saved = sys.argv
    try:
        sys.argv = argv
        X.main()
    finally:
        sys.argv = saved


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "sinbad"
    if "--render" in sys.argv:
        do_render(mission)
    elif "--export" in sys.argv:
        do_export(mission)
    else:
        do_validate(mission)


if __name__ == "__main__":
    main()
