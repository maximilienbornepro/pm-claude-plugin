#!/usr/bin/env python3
"""generator_meta - lit les metadonnees declarees dans le frontmatter des SKILL.md des generateurs.

A1 (plan d'action, axe 1) : chaque generateur declare dans son `SKILL.md`, sous `meta:`, de quoi
PILOTER le dispositif sans le recoder : son cout (`cost`), ses connecteurs (`mcp_deps`), ce qu'il
produit/consomme (`produces`/`consumes`), son statut. Le ROUTAGE des comptes se DERIVE de `cost`
(gros fichiers locaux -> compte "lourd"/perso ; sinon -> compte par defaut) : `routing.yml` ne garde
alors que les EXCEPTIONS a cette derivation.

Pas de dependance : pas de PyYAML sur le poste. On parse le petit sous-ensemble YAML du bloc `meta`
nous-memes (scalaires + listes en ligne `[a, b]`), c'est suffisant et robuste.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]            # framework/lib -> framework -> racine du depot
GEN_DIR = ROOT / "framework" / "generators"


def _scalar(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):          # liste en ligne : [a, b] ou []
        inner = v[1:-1].strip()
        return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()] if inner else []
    return v.strip("'\"")


def _parse_meta(text):
    """Extrait le bloc `meta:` du frontmatter et ses cles indentees `  cle: valeur`."""
    fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not fm:
        return {}
    lines = fm.group(1).splitlines()
    meta, in_meta, indent = {}, False, None
    for ln in lines:
        if re.match(r"^meta:\s*$", ln):
            in_meta = True
            continue
        if in_meta:
            m = re.match(r"^(\s+)([A-Za-z_][\w-]*):\s*(.*)$", ln)
            if not m:                                   # fin du bloc meta (ligne non indentee)
                if ln.strip() and not ln.startswith(" "):
                    break
                continue
            if indent is None:
                indent = len(m.group(1))
            if len(m.group(1)) < indent:                # on est sorti du bloc
                break
            meta[m.group(2)] = _scalar(m.group(3)) if m.group(3) != "" else []
    return meta


def load_all():
    """{nom_de_commande: {skill_name, meta, desc}} pour chaque framework/generators/*/SKILL.md.

    La CLE est le nom du DOSSIER, qui est le nom de commande (`pm run <dossier>`) et la cle de
    `routing.yml` - convention du registre GEN : « dossier == nom ». Le `name:` du frontmatter est
    le nom du SKILL pour Claude Code, qui peut differer (ex. deck-gate/gate-deck) : on le garde a
    part, sans s'en servir comme cle."""
    out = {}
    for sk in sorted(GEN_DIR.glob("*/SKILL.md")):
        text = sk.read_text(encoding="utf-8")
        has_fm = bool(re.match(r"^---\s*\n", text))
        name_m = re.search(r"(?m)^name:\s*(.+)$", text) if has_fm else None
        desc_m = re.search(r"(?m)^description:\s*(.+)$", text) if has_fm else None
        out[sk.parent.name] = {"skill_name": (name_m.group(1).strip() if name_m else None),
                               "has_frontmatter": has_fm,
                               "meta": _parse_meta(text),
                               "desc": (desc_m.group(1).strip() if desc_m else "")}
    return out


def derive_account(meta, default_account, heavy_account, policy="by-connector"):
    """Le compte DERIVE d'un generateur, selon la POLITIQUE de la mission (topologie des comptes) :

    - `by-connector` (defaut, ISOLATION) : les comptes sont differencies par leurs connecteurs.
      Un generateur qui touche un connecteur (`mcp_deps` non vide) va au compte qui l'a
      (`default_account`) ; sinon c'est du local -> compte "lourd"/perso (`heavy_account`).
    - `by-cost` (TOUS LES COMPTES ONT TOUS LES CONNECTEURS, ex. SINBAD) : va sur perso ce qui est
      LOURD (`cost: heavy-local`) OU PUREMENT LOCAL (aucun `mcp_deps`, ex. reset/tones) ; le compte
      par defaut ne garde que le LEGER qui TOUCHE un connecteur (projection, risks, jira...).
      (La seule difference avec `by-connector` : un generateur LOURD qui touche un connecteur part
      sur perso ici - on deleste - alors que l'isolation l'enverrait au compte qui a le connecteur.)

    Les deux signaux (`cost`, `mcp_deps`) sont declares sur chaque generateur, pour que l'une ou
    l'autre politique s'applique sans retoucher les meta. `mcp_deps` sert aussi au preflight."""
    meta = meta or {}
    deps = meta.get("mcp_deps") or []
    if policy == "by-cost":
        return heavy_account if (meta.get("cost") == "heavy-local" or not deps) else default_account
    return default_account if deps else heavy_account


def registry():
    """(command -> dossier, ALIAS) lus depuis framework/pm.py. Resout le cas multi-commande
    (ex. notion-scaffold/drive-scaffold -> dossier `scaffold`) et les scripts hors generators/
    (ex. tones -> lib). Permet d'etre ALIAS-aware (gate-deck -> deck-gate)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_pm_registry", ROOT / "framework" / "pm.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cmd_dir = {name: Path(t[0]).parent.name for name, t in mod.GEN.items()}
    return cmd_dir, dict(getattr(mod, "ALIAS", {}))


def meta_for(command):
    """Les meta du generateur derriere une COMMANDE (canonique ou alias). {} si introuvable ou
    si le dossier n'a pas de SKILL.md (ex. tones -> lib, ou un dossier multi-commande sans meta)."""
    try:
        cmd_dir, alias = registry()
    except Exception:
        return (load_all().get(command) or {}).get("meta") or {}
    canon = alias.get(command, command)
    d = cmd_dir.get(canon, canon)
    return (load_all().get(d) or {}).get("meta") or {}


def derive_for(command, default_account, heavy_account, policy="by-connector"):
    """Compte derive pour une COMMANDE (alias/multi-commande resolus). None si aucune meta
    (le caller applique alors le defaut)."""
    meta = meta_for(command)
    return derive_account(meta, default_account, heavy_account, policy) if meta else None


if __name__ == "__main__":
    import json
    print(json.dumps(load_all(), ensure_ascii=False, indent=1))
