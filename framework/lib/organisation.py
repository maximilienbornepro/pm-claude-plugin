"""organisation - lit framework/organisation.yml et le confronte aux composants réels du plugin.

    python3 framework/lib/organisation.py            # écarts (composant non rattaché, rattachement fantôme)
    python3 framework/lib/organisation.py --catalogue  # régénère framework/SKILLS.md par département

Utilisé par le vérificateur, le catalogue, le guide et l'écran « agence ».
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import yamlmin  # noqa: E402


def load():
    return yamlmin.load((ROOT / "framework" / "organisation.yml").read_text(encoding="utf-8"))


def components():
    """Ce qui existe vraiment dans le plugin, par type."""
    spec = importlib.util.spec_from_file_location("pmf_pm", ROOT / "framework" / "pm.py")
    pm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pm)
    gens = set(pm.GEN)
    gens |= {p.parent.name for p in (ROOT / "framework" / "generators").glob("*/SKILL.md")
             if "exec: skill" in p.read_text(encoding="utf-8")}  # skill-only generators (meeting-agenda...)
    return {
        "generators": gens,
        "skills": {p.parent.name for p in (ROOT / "framework" / "skills").glob("*/SKILL.md")},
        "agents": {p.stem for p in (ROOT / "framework" / "agents").glob("*.md")},
        "routines": {p.parent.name for p in (ROOT / "framework" / "routines").glob("*/SKILL.md")},
        "hooks": {p.stem for p in (ROOT / "framework" / "hooks").glob("*.py") if not p.stem.startswith("_")},
    }


def assignments(org=None):
    """{(type, name): department id} ; charte -> 'charte', renforts -> 'renforts'."""
    org = org or load()
    out = {}
    for d in org["departements"]:
        for t in ("generators", "skills", "agents", "routines"):
            for n in d.get(t) or []:
                out[(t, n)] = d["id"]
    for t in ("generators", "skills"):
        for n in (org.get("charte") or {}).get(t) or []:
            out[(t, n)] = "charte"
    for n in (org.get("renforts") or {}).get("agents") or []:
        out[("agents", n)] = "renforts"
    for h in org.get("garde_fous") or []:
        out[("hooks", h["name"])] = "garde_fous"
    return out


def check():
    """Return a list of errors (empty when every component is placed exactly where it exists)."""
    org = load()
    have = components()
    asg = assignments(org)
    errs = []
    builtin_agents = set((org.get("renforts") or {}).get("agents") or [])
    for t, names in have.items():
        for n in sorted(names):
            if (t, n) not in asg:
                errs.append(f"organisation : {t[:-1]} « {n} » rattaché à aucun département (framework/organisation.yml)")
    for (t, n), dep in asg.items():
        if n not in have.get(t, set()) and not (t == "agents" and n in builtin_agents):
            errs.append(f"organisation : {t[:-1]} « {n} » ({dep}) n'existe pas dans le plugin")
    seen = {}
    for d in org["departements"]:
        for t in ("generators", "skills", "agents", "routines"):
            for n in d.get(t) or []:
                if (t, n) in seen and seen[(t, n)] != d["id"]:
                    errs.append(f"organisation : {t[:-1]} « {n} » rattaché à deux départements ({seen[(t, n)]}, {d['id']})")
                seen[(t, n)] = d["id"]
    return errs


def _first_sentence(path):
    t = Path(path).read_text(encoding="utf-8")
    m = re.search(r'^description:\s*"?(.+?)"?\s*$', t, re.M)
    d = m.group(1) if m else ""
    if d.strip() in (">", "|", ""):
        m = re.search(r"^description:\s*[>|]\s*\n((?:\s+.+\n)+)", t, re.M)
        d = " ".join(line.strip() for line in m.group(1).splitlines()) if m else ""
    return re.split(r"(?<=[.!?])\s", d.strip())[0]


def catalogue_md():
    org = load()
    spec = importlib.util.spec_from_file_location("pmf_pm", ROOT / "framework" / "pm.py")
    pm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pm)

    def gdesc(n):
        if n in pm.GEN:
            return pm.GEN[n][1]
        return _first_sentence(ROOT / "framework" / "generators" / n / "SKILL.md")

    def rows(kind, names):
        out = []
        for n in names:
            if kind == "generators":
                d = gdesc(n)
            elif kind == "skills":
                d = _first_sentence(ROOT / "framework" / "skills" / n / "SKILL.md")
            elif kind == "agents":
                p = ROOT / "framework" / "agents" / f"{n}.md"
                d = _first_sentence(p) if p.exists() else "agent générique de Claude Code"
            else:
                d = _first_sentence(ROOT / "framework" / "routines" / n / "SKILL.md")
            label = org["types"][{"generators": "generator", "skills": "skill", "agents": "agent", "routines": "routine"}[kind]]["label"]
            out.append(f"| `{n}` | {label} | {d} |")
        return out

    lines = ["# Catalogue du plugin, par département", "",
             "Généré depuis `framework/organisation.yml` (`python3 framework/lib/organisation.py --catalogue`) : ne pas",
             "éditer à la main. Le plugin s'organise comme un PMO aligné sur le fonctionnement réel de Claude Code",
             "(voir `framework/ORGANISATION.md`) : Claude principal est le chef de projet ; les skills sont des",
             "classeurs qu'il suit, les générateurs des machines qu'il lance, les sous-agents les seuls vrais collègues.", ""]
    for d in org["departements"]:
        lines += [f"## {d['label']} - {d['role']}", "", f"{d['mission'][:1].upper()}{d['mission'][1:]}.", "",
                  "| Composant | Type | Ce qu'il fait |", "|---|---|---|"]
        for kind in ("agents", "skills", "generators", "routines"):
            lines += rows(kind, d.get(kind) or [])
        lines.append("")
    ch = org["charte"]
    lines += [f"## {ch['label']} (transverse)", "", f"{ch['mission'][:1].upper()}{ch['mission'][1:]}.", "",
              "| Composant | Type | Ce qu'il fait |", "|---|---|---|"]
    lines += rows("skills", ch.get("skills") or []) + rows("generators", ch.get("generators") or []) + [""]
    lines += ["## Renforts (agents génériques de Claude Code)", "", org["renforts"]["mission"][:1].upper() + org["renforts"]["mission"][1:] + ".", "",
              ", ".join(f"`{a}`" for a in org["renforts"]["agents"]), ""]
    lines += ["## Garde-fous (hooks)", "", "| Hook | Contrôle | Peut bloquer |", "|---|---|---|"]
    lines += [f"| `{h['name']}` | {h['controle']} | {'oui' if h['bloque'] else 'non'} |" for h in org["garde_fous"]] + [""]
    lines += ["## Services partagés (connecteurs)", "", ", ".join(s["label"] for s in org["services"]) + ".", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    if "--catalogue" in sys.argv:
        (ROOT / "framework" / "SKILLS.md").write_text(catalogue_md(), encoding="utf-8")
        print("ok : framework/SKILLS.md régénéré")
    else:
        errs = check()
        print("\n".join(errs) if errs else "organisation : tous les composants sont rattachés")
        sys.exit(1 if errs else 0)
