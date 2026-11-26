#!/usr/bin/env python3
"""dossier - dossier projet en slides 16:9 depuis UNE source, avec aller-retour PowerPoint -> HTML.

Tout vit dans le dossier de la mission, profiles/<mission>/dossier/ :
    dossier.json        la source (unique)
    dossier.pptx        le PowerPoint, éditable à la main
    index.html          la version HTML (même contenu, même charte)
    architecture.html   le schéma d'architecture au gabarit dossier (si une slide `archi` existe)
    .state.json         empreintes du dernier build / de la dernière synchro
    .backup/            copies horodatées avant toute réécriture

Usage :
  dossier.py <mission>                       liste des slides, sources, état PPTX (lecture seule)
  dossier.py <mission> --build [--force]     dossier.json -> dossier.pptx + index.html (+ architecture.html)
  dossier.py <mission> --sync [--dry-run]    dossier.pptx retouché -> dossier.json -> index.html
  dossier.py <mission> --html                régénère seulement index.html
  dossier.py <mission> --pptx out.pptx [--only id1,3]   export ponctuel, sans toucher au dossier

Garde-fou : si dossier.pptx a été modifié à la main depuis le dernier build ou la dernière synchro,
--build refuse (on perdrait les retouches) : lancer --sync d'abord, ou --force (copie de sauvegarde faite).
Écrit UNIQUEMENT dans le dossier de la mission. Dépôt dans un espace partagé : déroulé Office, après accord.
"""
import datetime as dt
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "framework" / "lib"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


prof = _load("pmf_profile", ROOT / "framework" / "lib" / "profile.py")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None


class Dossier:
    def __init__(self, mission):
        self.mdir = Path(prof.mission_dir(mission))
        self.dir = self.mdir / "dossier"
        self.json = self.dir / "dossier.json"
        legacy = self.mdir / "dossier.json"
        if not self.json.exists() and legacy.exists():  # first run: move the source into the folder
            self.dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(legacy), str(self.json))
            print(f"source déplacée : {legacy} -> {self.json}")
        self.pptx, self.html, self.state = self.dir / "dossier.pptx", self.dir / "index.html", self.dir / ".state.json"

    def deck(self):
        return json.loads(self.json.read_text(encoding="utf-8"))

    def save_deck(self, deck):
        self.backup(self.json)
        self.json.write_text(json.dumps(deck, ensure_ascii=False, indent=1), encoding="utf-8")

    def backup(self, p):
        if Path(p).exists():
            b = self.dir / ".backup"; b.mkdir(exist_ok=True)
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            shutil.copy2(p, b / f"{stamp}-{Path(p).name}")

    def read_state(self):
        return json.loads(self.state.read_text()) if self.state.exists() else {}

    def write_state(self):
        self.state.write_text(json.dumps({"pptx": sha(self.pptx), "json": sha(self.json),
                                          "at": dt.datetime.now().isoformat(timespec="seconds")}, indent=1))

    def pptx_edited(self):
        st = self.read_state()
        return self.pptx.exists() and st.get("pptx") and sha(self.pptx) != st["pptx"]

    def ensure_ids(self, deck):
        import pptx_render as R
        changed = False
        for sid, sl in zip(R.slide_ids(deck), deck["slides"]):
            if not sl.get("id"):
                sl["id"] = sid; changed = True
        return changed


def render_html(deck, D):
    import html_render as H
    out = H.render_html(deck, D.mdir, D.dir)
    archi = next((sl for sl in deck["slides"] if sl.get("kind") == "archi"), None)
    if archi:
        sys.path.insert(0, str(ROOT / "framework" / "departements" / "studio" / "generators" / "archi"))
        import dossier_skin as K
        model = json.loads((D.mdir / archi["model"]).read_text(encoding="utf-8"))
        lg = (deck.get("logos") or {}).get("light")
        page = K.page(model, K.data_uri(D.mdir / lg) if lg else None, project=deck.get("project", ""),
                      src_label=archi["model"], src_href="#", foot_right="Dossier projet")
        (D.dir / (archi.get("link") or "architecture.html")).write_text(page, encoding="utf-8")
    return out


def cmd_list(D):
    deck = D.deck()
    import pptx_render as R
    print(f"Dossier projet · {deck.get('project')} · {len(deck['slides'])} slides + sommaire (source : {D.json})")
    for n, (sid, sl) in enumerate(zip(R.slide_ids(deck), deck["slides"]), 1):
        print(f"  {n:02d}  {sl['kind']:<12} {sid:<42} {sl.get('title', '').replace(chr(10), ' ')}")
    st = D.read_state()
    if D.pptx.exists():
        print(f"\nPPTX : {D.pptx}" + ("  ->  MODIFIÉ À LA MAIN depuis le dernier build : lancer --sync" if D.pptx_edited() else "  (à jour)"))
    else:
        print("\nPPTX : pas encore généré (--build)")
    if st.get("at"):
        print(f"Dernier build / synchro : {st['at']}")
    return 0


def cmd_build(D, force=False):
    import pptx_render as R
    deck = D.deck()
    if D.ensure_ids(deck):
        D.save_deck(deck)
    if D.pptx_edited() and not force:
        print(f"REFUS : {D.pptx.name} a été modifié à la main depuis le dernier build. Lancer --sync pour reprendre "
              f"les retouches dans dossier.json, ou --build --force pour l'écraser (une copie sera gardée dans .backup/).")
        return 1
    D.dir.mkdir(parents=True, exist_ok=True)
    D.backup(D.pptx)
    warns = R.render(deck, D.mdir, D.pptx)
    print(f"ok : {D.pptx} ({len(deck['slides']) + 1} slides)")
    for w in warns:
        print("  attention :", w)
    h = render_html(deck, D)
    if h:
        print(f"ok : {h}")
    D.write_state()
    return 0


def cmd_sync(D, dry=False):
    import pptx_sync as Y
    if not D.pptx.exists():
        print("rien à synchroniser : pas de dossier.pptx (--build d'abord)")
        return 1
    deck = D.deck()
    new, report = Y.sync(deck, D.pptx)
    if new == deck:
        print("aucune modification détectée dans le PowerPoint")
    else:
        print("modifications reprises du PowerPoint :")
        for r in report or ["contenu de slides mis à jour"]:
            print("  -", r)
    if dry:
        print("(--dry-run : rien n'est écrit)")
        return 0
    if new != deck:
        D.save_deck(new)
        print(f"ok : {D.json} mis à jour (ancienne version dans .backup/)")
    h = render_html(new, D)
    if h:
        print(f"ok : {h} régénéré")
    D.write_state()
    return 0


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__); return 2
    D = Dossier(argv[0])
    if not D.json.exists():
        print(f"pas de source : {D.json}"); return 1
    if "--build" in argv:
        return cmd_build(D, "--force" in argv)
    if "--sync" in argv:
        return cmd_sync(D, "--dry-run" in argv)
    if "--html" in argv:
        h = render_html(D.deck(), D); print(f"ok : {h}"); return 0
    if "--pptx" in argv:
        import pptx_render as R
        out = Path(argv[argv.index("--pptx") + 1])
        only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
        warns = R.render(D.deck(), D.mdir, out, only)
        print(f"ok : {out}")
        for w in warns:
            print("  attention :", w)
        return 0
    return cmd_list(D)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
