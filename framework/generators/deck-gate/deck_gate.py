#!/usr/bin/env python3
"""gate-deck - rend le CONTENU du deck GATE d'une mission (markdown + JSON), ton du profil.

Depuis `profiles/<mission>/gate_deck.yml` (plan des slides). Le slide `jalons` est rempli
automatiquement depuis `key_dates` du profil. Le generateur **ne produit pas** le .pptx :
l'assemblage sur le template reste une etape GARDEE (une seule ecriture Office, via la
coherence des docs). Lecture seule.

  python3 gate_deck.py <mission>           # le deck en markdown (pret a relire)
  python3 gate_deck.py <mission> --json    # le deck en JSON (pour l'assemblage pptx)
"""
import sys, json, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("pmf_profile", ROOT / "framework" / "lib" / "profile.py")
prof = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(prof)

MOIS = ["", "janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout",
        "septembre", "octobre", "novembre", "decembre"]


def _ddmm(v):
    s = str(v)
    try:
        y, m, d = s.split("-")[:3]
        return f"{int(d):02d}/{int(m):02d}"
    except Exception:
        return s


def load(mission):
    return prof._load_yaml(prof.mission_dir(mission) / "deck-gate.yml")


def jalons(profile):
    kd = profile.get("key_dates", {}) or {}
    out = []
    for key, lbl in (("t0", "T0"), ("code_freeze", "Gel du code"), ("mep", "Mise en production (MEP)")):
        if kd.get(key):
            out.append(f"{lbl} : {_ddmm(kd[key])}")
    return out


def render_slides(mission):
    cfg = load(mission)
    profile = prof.load(mission)["profile"]
    slides = []
    for s in cfg.get("slides", []):
        t = s.get("type", "bullets")
        sl = {"type": t, "title": s.get("title", "")}
        if t == "title":
            sl["subtitle"] = s.get("subtitle", "")
        elif t == "jalons":
            sl["bullets"] = jalons(profile)
        elif t == "schema":
            sl["image"] = s.get("image", "")
        else:
            sl["bullets"] = s.get("bullets", []) or []
        slides.append(sl)
    return {"deck": profile.get("name", mission) + " - GATE", "tone": cfg.get("tone"),
            "template": cfg.get("template"), "output": cfg.get("output"), "slides": slides}


def to_md(deck):
    out = [f"# {deck['deck']}", f"*Ton : {deck.get('tone') or 'defaut'} · template : {deck.get('template')}*", ""]
    for i, s in enumerate(deck["slides"], 1):
        out.append(f"## Slide {i} - {s['title']}")
        if s["type"] == "title" and s.get("subtitle"):
            out.append(f"*{s['subtitle']}*")
        elif s["type"] == "schema":
            out.append(f"[Schema a inserer : {s.get('image')}]")
        else:
            for b in s.get("bullets", []):
                out.append(f"- {b}")
        out.append("")
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("usage: gate_deck.py <mission> [--json]"); return 2
    deck = render_slides(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(deck, ensure_ascii=False, indent=2)); return 0
    print(to_md(deck))
    print("\n---\nAssemblage pptx : etape gardee (template -> .pptx), une seule ecriture Office,")
    print("via la coherence des docs. Ce generateur ne produit que le contenu.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
