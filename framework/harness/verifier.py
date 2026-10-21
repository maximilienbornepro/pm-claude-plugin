#!/usr/bin/env python3
"""verifier - lint du framework (A3). Refuse un plugin incoherent AVANT publication.

Controles (ERREUR = sortie 1 ; AVERTISSEMENT = signale, n'echoue pas) :
  1. GEN : chaque commande du registre pointe un script qui existe.
  2. ALIAS : chaque alias vise une commande canonique reelle.
  3. Dossiers : pas de dossier de generateur orphelin (non atteint par GEN).
  4. meta : cost, mcp_deps, status bien formes (valeurs admises).
  5. meta : chaque commande 1:1 avec un SKILL.md DEVRAIT porter un bloc meta (AVERTISSEMENT).
  6. routing.yml de chaque mission : chaque entree est une commande reelle (canonique ou alias).

    python3 framework/harness/verifier.py          # tout le framework + tous les profils
"""
import sys, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof          # noqa: E402
import generator_meta as gm     # noqa: E402

COSTS = {"heavy-local", "light"}
STATUTS = {"draft", "stable"}
CONNECTEURS = {"jira", "notion", "m365", "figma", "drive", "outlook", "teams", "confluence", "chrome"}  # chrome = Claude in Chrome (lecture Slack)

errors, warns = [], []
def err(m): errors.append(m)
def warn(m): warns.append(m)


def _pm():
    spec = importlib.util.spec_from_file_location("_pm", ROOT / "framework" / "pm.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def main():
    pm = _pm()
    GEN, ALIAS = pm.GEN, getattr(pm, "ALIAS", {})
    metas = gm.load_all()                               # {dossier: {...}}

    # 1. scripts de GEN existants
    for cmd, t in GEN.items():
        if not (ROOT / t[0]).exists():
            err(f"GEN[{cmd}] : script introuvable {t[0]}")

    # 2. cibles d'ALIAS valides
    for a, canon in ALIAS.items():
        if canon not in GEN:
            err(f"ALIAS[{a}] vise une commande inconnue : {canon}")

    # 3. dossiers de generateurs orphelins (non atteints par une commande). Exception : un generateur
    # SKILL-ONLY (meta `exec: skill`, ex. notion-planning : pur connecteur, aucun script `pm run`) est
    # legitime sans entree GEN ; on valide quand meme sa meta.
    dirs_utilises = {Path(t[0]).parent.name for t in GEN.values()}
    for sk in (ROOT / "framework" / "generators").glob("*/SKILL.md"):
        d = sk.parent.name
        if d in dirs_utilises:
            continue
        meta = (metas.get(d) or {}).get("meta") or {}
        if meta.get("exec") == "skill":
            if meta.get("cost") not in COSTS:
                err(f"{d} (skill) : cost invalide '{meta.get('cost')}'")
            if meta.get("status") not in STATUTS:
                err(f"{d} (skill) : status invalide '{meta.get('status')}'")
            inc = set(meta.get("mcp_deps") or []) - CONNECTEURS
            if inc:
                err(f"{d} (skill) : mcp_deps inconnu(s) {sorted(inc)}")
        else:
            warn(f"dossier generateur non atteint par GEN (ni skill-only) : {d}")

    # 4. + 5. meta bien formees + completude
    cmd_dir = {cmd: Path(t[0]).parent.name for cmd, t in GEN.items()}
    for cmd in sorted(GEN):
        d = cmd_dir[cmd]
        g = metas.get(d)
        if not g:                                       # pas de SKILL.md (ex. tones -> lib)
            continue
        meta = g.get("meta") or {}
        # un dossier PARTAGE par plusieurs commandes (ex. scaffold) ne peut pas porter une meta
        # unique : son routage reste une exception explicite dans routing.yml, pas un oubli.
        partage = sum(1 for c, dd in cmd_dir.items() if dd == d) > 1
        if not meta:
            if not partage:
                warn(f"{cmd} ({d}) : aucun bloc meta")
            continue
        if meta.get("cost") not in COSTS:
            err(f"{cmd} : cost invalide '{meta.get('cost')}' (admis : {sorted(COSTS)})")
        if meta.get("status") not in STATUTS:
            err(f"{cmd} : status invalide '{meta.get('status')}' (admis : {sorted(STATUTS)})")
        inconnus = set(meta.get("mcp_deps") or []) - CONNECTEURS
        if inconnus:
            err(f"{cmd} : mcp_deps inconnu(s) {sorted(inconnus)} (admis : {sorted(CONNECTEURS)})")
        # A2 : un generateur qui ecrit de l'Office doit renvoyer au DEROULE COMMUN (pointeur, pas copie)
        if meta.get("writes") == "office":
            txt = (ROOT / "framework" / "generators" / d / "SKILL.md").read_text(encoding="utf-8")
            if "_deroule-office" not in txt:
                err(f"{cmd} : writes=office mais ne renvoie pas au deroule commun (_deroule-office.md)")

    # 6. routing.yml de chaque mission -> commandes reelles. On lint les profils LIVRES AVEC LE
    # FRAMEWORK (ROOT/profiles), pas ceux du projet courant (qui peuvent router des generateurs de
    # mission absents du framework) : le lint doit etre deterministe, independant du cwd.
    connus = set(GEN) | set(ALIAS)
    try:
        root = ROOT / "profiles"
        for m in sorted(p.name for p in root.iterdir() if p.is_dir()):
            rp = root / m / "routing.yml"
            if not rp.exists():
                continue
            routing = (prof._load_yaml(rp) or {}).get("routing") or {}
            for cmd in routing:
                if cmd not in connus:
                    err(f"routing {m} : commande inconnue '{cmd}'")
    except Exception as e:
        warn(f"profils illisibles : {e}")

    # 7. REGISTRE de templates (trackers/<solution>/<objet>.yml) : bien formes, coherents (DM-020).
    try:
        import templates as TPL
        n = 0
        for sol in TPL.solutions():
            for obj in TPL.catalog().get(sol, []):
                n += 1
                tpl = TPL.load(sol, obj)
                if not tpl:
                    err(f"template {sol}/{obj} : illisible"); continue
                if tpl.get("object") != obj or tpl.get("solution") != sol:
                    err(f"template {sol}/{obj} : object/solution ne collent pas au chemin")
                if not tpl.get("title"):
                    err(f"template {sol}/{obj} : pas de title")
                for k, v in (tpl.get("options") or {}).items():
                    if not isinstance(v, list):
                        err(f"template {sol}/{obj} : option '{k}' n'est pas une liste")
                for k, v in (tpl.get("legende") or {}).items():
                    if not isinstance(v, list):
                        err(f"template {sol}/{obj} : legende '{k}' n'est pas une liste")
        print(f"{n} templates (objet x solution) verifies.")
    except Exception as e:
        warn(f"registre de templates illisible : {e}")

    # rapport
    for w in warns: print(f"  AVERT  {w}")
    for e in errors: print(f"  ERREUR {e}")
    n_meta = sum(1 for g in metas.values() if g.get("meta"))
    print(f"\n{len(GEN)} commandes, {len(ALIAS)} alias, {n_meta} generateurs avec meta.")
    if errors:
        print(f"ECHEC : {len(errors)} erreur(s), {len(warns)} avertissement(s)."); return 1
    print(f"OK : 0 erreur, {len(warns)} avertissement(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
