#!/usr/bin/env python3
"""setup - onboarding d'un profil (LECTURE SEULE).

Detecte ce qui MANQUE ou reste `a confirmer` dans un profil de mission, et pour chaque
trou propose une valeur en SONDANT le disque (dossiers OneDrive, depots locaux, roles du
RACI...). Ne renvoie que le diagnostic + les suggestions : la saisie se fait par un
formulaire cliquable, et l'ecriture dans le profil n'arrive qu'apres validation (voir SKILL).

  python3 setup.py <mission>            # le formulaire d'onboarding (lisible)
  python3 setup.py <mission> --json     # les champs + suggestions (pour construire le formulaire)

N'ecrit rien.
"""
import sys, os, json, glob, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("pmf_profile", ROOT / "framework" / "lib" / "profile.py")
prof = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(prof)

ACONF = ("a confirmer", "à confirmer")


def _raw(mission, name):
    p = prof.mission_dir(mission) / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _exists(path):
    try:
        return bool(path) and Path(os.path.expanduser(str(path))).exists()
    except Exception:
        return False


def _glob_onedrive():
    """Dossiers locaux qui ressemblent a la biblio SharePoint/OneDrive de la mission."""
    pats = [
        "~/Library/CloudStorage/OneDrive-*/**/*inbad*",
        "~/Library/CloudStorage/OneDrive-*/Shortcuts/*",
        "~/Library/CloudStorage/OneDrive-*",
    ]
    out = []
    for pat in pats:
        for h in glob.glob(os.path.expanduser(pat), recursive=False):
            if Path(h).is_dir() and h not in out:
                out.append(h)
    return out[:8]


def _roles(mission):
    try:
        d = prof._load_yaml(prof.mission_dir(mission) / "raci.yml")
        r = d.get("roles") or []
        return [x.get("key") or x.get("label") or str(x) for x in r] if isinstance(r, list) else []
    except Exception:
        return []


def detect(mission):
    profile = prof.load(mission)["profile"]
    gaps = []

    def add(gid, label, why, current, suggestion, where, kind="value"):
        gaps.append({"id": gid, "label": label, "why": why, "current": current,
                     "suggestion": suggestion, "where": where, "kind": kind})

    # 1. racine des depots locaux (SINBAD_ROOT)
    sroot = os.environ.get("SINBAD_ROOT")
    default_sroot = os.path.expanduser("~/Documents/Sinbad")
    if not sroot and _exists(default_sroot):
        add("env.SINBAD_ROOT", "Racine des depots locaux (SINBAD_ROOT)",
            "depots stack-imagery / scan-jira (schema d'archi, images Jira)",
            "non defini (defaut utilise)", default_sroot, "variable d'env", "env")
    elif not sroot and not _exists(default_sroot):
        add("env.SINBAD_ROOT", "Racine des depots locaux (SINBAD_ROOT)",
            "depots stack-imagery / scan-jira introuvables au defaut",
            "introuvable", "<chemin vers le dossier Sinbad clone>", "variable d'env", "env")

    # 2. racine du Drive synchronise (drive.root)
    droot = (profile.get("drive") or {}).get("root")
    if not _exists(droot):
        add("drive.root", "Dossier local du Drive/SharePoint synchronise",
            "classeurs Office (risques, roadmap, planning), cohérence des docs",
            droot or "(vide)", _glob_onedrive() or ["<chemin OneDrive synchronise>"],
            "profile.yml > drive.root", "path")

    # 3. equipe (RACI)
    team = profile.get("team")
    if not team:
        roles = _roles(mission)
        sugg = [{"name": "<nom>", "role": r} for r in roles] or [{"name": "<nom>", "role": "<role>"}]
        add("team", "Equipe (noms <-> roles)",
            "le RACI a besoin des personnes derriere chaque role",
            "[] (vide)", sugg, "profile.yml > team", "list")

    # 4. source des dates du planning
    npl = _raw(mission, "notion-planning.yml")
    if any(a in npl.lower() for a in ACONF):
        add("notion_planning.source", "Source des dates du planning",
            "d'ou le report planning tire gel/MEP/jalons",
            "a confirmer",
            ["framework/generators/notion-planning/planning.sample.yml (sample a copier/adapter)",
             "03 - Roadmap/Roadmap_SINBAD.xlsx", "04 - Planning/Planning_SINBAD.xlsx"],
            "notion-planning.yml > source", "value")

    # 5. carte de coherence des docs
    dc = _raw(mission, "docs-coherence.yml")
    if any(a in dc.lower() for a in ACONF):
        base = (droot or "${SINBAD_PM_ROOT}") + "/02 - Project Management"
        add("docs_coherence.root", "Racine de la carte de coherence",
            "verifier GATE <-> Excel <-> PPT <-> PNG a jour",
            "a confirmer", base, "docs-coherence.yml > root + chains", "value")

    # 6. autres `a confirmer` residuels (prose / partenaires) - informatif
    extra = []
    for name in ("partenaires.yml", "profile.yml", "routines.yml"):
        for ln in _raw(mission, name).splitlines():
            low = ln.lower()
            if any(a in low for a in ACONF) and "root" not in low:
                extra.append(f"{name}: {ln.strip()[:90]}")
    return {"mission": mission, "name": profile.get("name", mission),
            "gaps": gaps, "info_aconfirmer": extra[:12]}


def to_form(d):
    out = [f"Onboarding du profil « {d['name']} » ({d['mission']})", "=" * 56, ""]
    if not d["gaps"]:
        out.append("Profil complet : aucun champ bloquant a renseigner. (idempotent)")
    else:
        out.append(f"{len(d['gaps'])} champ(s) a renseigner (chacun avec une suggestion) :\n")
        for i, g in enumerate(d["gaps"], 1):
            out.append(f"[{i}] {g['label']}   ({g['where']})")
            out.append(f"     a quoi ca sert : {g['why']}")
            out.append(f"     actuel         : {g['current']}")
            sug = g["suggestion"]
            if isinstance(sug, list):
                out.append("     suggestions    :")
                for s in sug:
                    out.append(f"        - {json.dumps(s, ensure_ascii=False) if isinstance(s, dict) else s}")
            else:
                out.append(f"     suggestion     : {sug}")
            out.append("")
    if d["info_aconfirmer"]:
        out.append("Pour info (non bloquant, `a confirmer` residuels) :")
        for e in d["info_aconfirmer"]:
            out.append(f"   . {e}")
    out.append("")
    out.append("Rien n'est ecrit : ces champs se remplissent par formulaire cliquable, puis")
    out.append("on applique au profil apres ton OK (voir le SKILL setup).")
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print("usage: setup.py <mission> [--json]"); return 2
    d = detect(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(d, ensure_ascii=False, indent=2)); return 0
    print(to_form(d)); return 0


if __name__ == "__main__":
    sys.exit(main())
