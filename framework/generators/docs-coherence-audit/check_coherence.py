#!/usr/bin/env python3
"""Controle de coherence des documents - LECTURE SEULE.

Verifie qu'une sortie (derived) est bien **a jour** vis-a-vis de ses sources :
c'est le cas typique GATE deck <- Excel sources <- PNG derives, ou tout artefact
genere a partir d'autres. N'ecrit rien : il signale ce qui est perime ou manquant.

La carte des dependances vit dans la config de mission
profiles/<mission>/coherence.yml (`chains`). Deux regles :
  - `newer`     : la sortie doit exister et etre **plus recente** que toutes ses sources ;
  - `identical` : la sortie doit avoir le **meme md5** qu'une source unique (copie exacte).

    python3 check_coherence.py [--mission sinbad] [--root /chemin/racine]

Code retour 0 si tout est coherent, 1 sinon. A derouler apres toute modif d'un
fichier de la chaine (deck, Excel, PNG, page publiee).
"""
import argparse, hashlib, os, sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof   # noqa: E402


def _resolve(p, root):
    p = os.path.expanduser(str(p))
    if root and not os.path.isabs(p):
        p = os.path.join(root, p)
    return Path(p)


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


def check(chains, root):
    issues = []
    for c in chains:
        der = _resolve(c["derived"], root)
        srcs = [_resolve(s, root) for s in (c.get("sources") or [])]
        rule = c.get("rule", "newer")
        if not der.exists():
            issues.append(("MANQUANT", str(der), "la sortie n'existe pas"))
            continue
        miss = [str(s) for s in srcs if not s.exists()]
        if miss:
            issues.append(("SOURCE?", str(der), "source(s) introuvable(s) : " + ", ".join(miss)))
            continue
        if rule == "identical":
            if len(srcs) != 1:
                issues.append(("CONFIG", str(der), "rule identical attend exactement 1 source"))
            elif _md5(der) != _md5(srcs[0]):
                issues.append(("DIFFERENT", str(der), f"md5 != {srcs[0]}"))
        else:  # newer
            dmt = der.stat().st_mtime
            stale = [str(s) for s in srcs if s.stat().st_mtime > dmt]
            if stale:
                issues.append(("PERIME", str(der), "plus ancien que : " + ", ".join(stale)))
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mission", default="sinbad")
    ap.add_argument("--root", help="prefixe de chemin (sinon coherence.yml > root, sinon chemins tels quels)")
    a = ap.parse_args()
    cfg = prof._load_yaml(prof.mission_dir(a.mission) / "docs-coherence.yml")
    root = a.root or cfg.get("root") or ""
    root = os.path.expanduser(root)
    chains = cfg.get("chains") or []
    issues = check(chains, root)
    print(f"Coherence : {len(chains)} chaines verifiees.")
    if issues:
        for kind, der, why in issues:
            print(f"  [{kind}] {der} - {why}")
        print("\nIncoherences detectees : regenerer / resynchroniser les sorties ci-dessus.")
        sys.exit(1)
    print("Tout est coherent (chaque sortie est a jour vis-a-vis de ses sources).")


if __name__ == "__main__":
    main()
