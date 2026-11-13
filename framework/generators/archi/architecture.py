#!/usr/bin/env python3
"""architecture - pilote du schéma d'archi (stack-imagery), piloté par la config de mission.

Trois modes (dispatch sur les flags) ; tous lisent `profiles/<mission>/architecture.yml` :

    python3 architecture.py <mission>                       # défaut : VALIDER (lecture seule)
    python3 architecture.py <mission> [--target source|theme|golden]
    python3 architecture.py <mission> --render [-o sortie.html]
    python3 architecture.py <mission> --export drawio [-o sortie.drawio]
    python3 architecture.py <mission> --import <fichier.drawio> [-o model.json] [--logos-from <src>]
    python3 architecture.py <mission> --import <fichier.drawio> --enrich [--page "Big Picture"] [--no-cluster]
    python3 architecture.py <mission> --suggest                       # questions d'abstraction (JSON)
    python3 architecture.py <mission> --render [--public P] [--set couche=mode,...] [--apply-suggestions]

- défaut  : lance les 7 invariants de `validate.py` sur l'artefact HTML de la mission
            (chemin lu dans la config, surchargeable par PMF_ARCH_HTML). Ne publie rien.
- --render: génère le HTML interactif depuis le MODÈLE de la mission (`model_json` de la config,
            surchargeable par PMF_ARCH_MODEL) vers une sortie de SCRATCHPAD `<mission>_generated.html`.
            N'écrase JAMAIS `source_html` : la source canonique reste la source de vérité.
- --export: appelle `export_drawio.py` (une page draw.io par écran) pour la mission.
- --import: appelle `import_drawio.py` (un .drawio -> model.json reconstruit), sortie SCRATCHPAD par
            défaut ; ne touche jamais le model.json/source/theme/golden de la mission. Les logos sont
            déduits des libellés depuis la bibliothèque partagée + le schéma par défaut de la mission
            (source_html) + profiles/<mission>/logos (ou --logos-from).
- --suggest: liste les questions à poser à la personne (public, puis profondeur de chaque couche)
            avec la proposition motivée du générateur. Lecture seule.
- --public / --set / --apply-suggestions (avec --render) : profondeur des couches dans la vue
            d'ensemble ; enregistrée dans abstraction.json à côté du modèle (fichier local de la
            mission, écrit seulement si l'un de ces flags est passé).

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
    modes = _abstraction(model_path, write=True)
    B.build_html_file(model_path, out, modes)
    print(f"Écrit  : {out}   ({'scratchpad, ' if not _opt('-o') else ''}source_html intacte)")

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


def _abstraction(model_path, write=False):
    """Modes des couches : abstraction.json (à côté du modèle) + flags --public/--set/--apply-suggestions.
    N'écrit abstraction.json que si un de ces flags est passé (choix explicite de la personne)."""
    import json as _json
    import abstraction as A  # noqa: E402
    model = _json.load(open(model_path, encoding="utf-8"))
    if not A.layers(model):
        return None
    conf = Path(model_path).with_name("abstraction.json")
    public, modes = A.load(conf)
    modes = {**A.default_modes(model), **modes}
    changed = False
    if _opt("--public"):
        if _opt("--public") not in A.PUBLICS:
            print(f"[!] public inconnu : {_opt('--public')} ({', '.join(A.PUBLICS)})"); sys.exit(2)
        public, changed = _opt("--public"), True
    if "--apply-suggestions" in sys.argv:
        modes.update({L["id"]: A.suggest(model, L, public)[0] for L in A.layers(model)}); changed = True
    if _opt("--set"):
        try:
            A.parse_set(model, _opt("--set"), modes); changed = True
        except ValueError as e:
            print(f"[!] {e}"); sys.exit(2)
    if write and changed:
        A.save(conf, public, modes)
        print(f"Abstraction enregistrée : {conf}")
    print("Couches : " + ", ".join(f"{k}={v}" for k, v in modes.items()) + (f"  (public : {public})" if public else ""))
    return modes


def do_suggest(mission):
    """Questions à poser à la personne pour construire la vue d'ensemble avec elle (lecture seule)."""
    import json as _json
    import abstraction as A  # noqa: E402
    env_model = os.environ.get("PMF_ARCH_MODEL")
    model_path = env_model or _cfg(mission)["model_json"]
    model = _json.load(open(model_path, encoding="utf-8"))
    if not A.layers(model):
        print(_json.dumps({"couches": [], "conseil": "Le modèle ne déclare pas de `layers` : proposer d'en "
                           "regrouper les entités (données, traitement, API, identité, partenaires, exploitation, "
                           "acteurs) pour pouvoir abstraire la vue d'ensemble. Voir SCHEMA.md."},
                          ensure_ascii=False, indent=2))
        return
    public, modes = A.load(Path(model_path).with_name("abstraction.json"))
    public = _opt("--public") or public
    print(_json.dumps(A.questions(model, {**A.default_modes(model), **modes}, public), ensure_ascii=False, indent=2))


def do_import(mission):
    """`--import <fichier.drawio>` : reconstruit un model.json depuis un .drawio.
    Sortie par defaut dans le SCRATCHPAD (ne touche jamais le model.json de la mission)."""
    src = _opt("--import")
    if not src:
        print("[!] usage : architecture.py <mission> --import <fichier.drawio> [-o model.json]")
        sys.exit(2)
    if not Path(src).exists():
        print(f"[!] .drawio introuvable : {src}"); sys.exit(2)
    import import_drawio as I  # noqa: E402
    out = _opt("-o") or str(ROOT.parent / "scratchpad" / f"{mission}_imported.model.json")
    # garde-fou : ne jamais ecraser un artefact canonique de la mission
    cfg = None
    try:
        cfg = _cfg(mission)
    except Exception:
        pass
    protected = set()
    if cfg:
        for v in list(KEYMAP.values()) + ["model_json"]:
            if cfg.get(v):
                protected.add(os.path.realpath(cfg[v]))
    if os.path.realpath(out) in protected:
        print(f"[!] refus : {out} est un artefact canonique de la mission (modele/source/theme/golden).")
        sys.exit(2)
    model = I.build_model(open(src, encoding="utf-8").read())
    # logos : bibliothèque partagée + schéma par défaut de la mission + ses logos de marque
    srcs = [_opt("--logos-from")]
    if cfg:
        srcs += [cfg.get("source_html"), str(prof.mission_dir(mission) / "logos")]
    deduced = I.deduce_logos(model, I.logo_sources([x for x in srcs if x and Path(x).exists()]))
    import json as _json
    questions = None
    if "--enrich" in sys.argv:   # roles, couleurs, chemin principal, loupes, cadre EKS, etages, couches
        import enrich as E  # noqa: E402
        try:
            model, questions = E.enrich(model, _opt("--page"), "--no-cluster" not in sys.argv)
        except ValueError as e:
            print(f"[!] {e}"); sys.exit(2)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    _json.dump(model, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Architecture {mission} - import draw.io -> modele")
    print(f"Source : {src}")
    print(f"Ecrit  : {out}   (scratchpad ; a relire, completer les logos, puis --render + harness)")
    print(f"Modele : {len(model['zones'])} zone(s), {len(model['entities'])} entite(s), "
          f"{len(model['flows'])} flux, {len(model['views'])} vue(s)")
    print(f"Logos déduits : {len(deduced)}" + (" - " + ", ".join(sorted({k for _, k in deduced})) if deduced else ""))
    if questions:
        print("\nQuestions de couches à poser (systématiques) :")
        for q in questions:
            print(f"  - [{q['couche']}] {q['question']}\n      proposition : {q['proposition']}")


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
    elif "--import" in sys.argv:
        do_import(mission)
    elif "--suggest" in sys.argv:
        do_suggest(mission)
    else:
        do_validate(mission)


if __name__ == "__main__":
    main()
