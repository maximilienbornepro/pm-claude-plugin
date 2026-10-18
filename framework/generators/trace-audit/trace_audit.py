#!/usr/bin/env python3
"""trace-audit - audit des RUPTURES de la chaîne de traçabilité (A5, DM-018).

La chaîne (besoin/TR -> ticket -> POC -> test) est déclarée en DONNÉE dans method.yaml (bloc
`tracabilite` : ordre des maillons, propriétaire de chacun, phase à partir de laquelle il est
exigible). Les ITEMS - ce que porte chaque besoin aujourd'hui - vivent dans
`profiles/<mission>/tracabilite.yml`. Cet audit CALCULE, pour la phase courante, les maillons
exigibles MANQUANTS (ruptures) et dit OÙ ALLER (le propriétaire du premier maillon manquant).

Lecture seule : il ne modifie ni les tickets, ni la matrice, ni aucun fichier. Il unifie ce que
disent la matrice IADT et le périmètre, et détecte les trous tôt.

    python3 framework/generators/trace-audit/trace_audit.py [mission]         # vue d'ensemble
    python3 framework/generators/trace-audit/trace_audit.py [mission] <id>    # détail d'un item
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof  # noqa: E402
import yamlmin  # noqa: E402
import method as M  # noqa: E402


def _relie(v):
    """Un maillon est RELIÉ si sa valeur est vraie (true / un identifiant). absent / false = manquant."""
    if v is None or v is False or v == "":
        return False
    return str(v).strip().lower() not in ("false", "non", "0")


def load_chaine(mission):
    """(ordre, phases) de la chaîne, depuis method.yaml > tracabilite."""
    tr = M.section(mission, "tracabilite")
    return (tr.get("ordre") or []), (tr.get("phases") or [])


def load_items(mission):
    path = Path(prof.mission_file(mission, "tracabilite.yml"))
    if not path.exists():
        return None
    return yamlmin.load(path.read_text(encoding="utf-8")) or {}


def evaluate(item, ordre, phases, phase_courante):
    """Rend, pour un item, l'état de chaque maillon et les ruptures (maillons exigibles manquants)."""
    liens = item.get("liens") or {}
    pc = phases.index(phase_courante) if phase_courante in phases else len(phases) - 1
    etat, ruptures = [], []
    for m in ordre:
        nom = m.get("maillon")
        exig_phase = m.get("exigible_des")
        exig_idx = phases.index(exig_phase) if exig_phase in phases else 0
        exigible = exig_idx <= pc
        facultatif = bool(m.get("facultatif"))
        relie = _relie(liens.get(nom))
        if relie:
            statut = "ok"
        elif not exigible:
            statut = "pas_encore"          # exigible seulement à partir d'une phase ultérieure
        elif facultatif:
            statut = "facultatif"
        else:
            statut = "rupture"; ruptures.append(m)
        etat.append((nom, statut, m.get("proprietaire", ""), exig_phase))
    return {"etat": etat, "ruptures": ruptures,
            "ou_aller": ruptures[0].get("proprietaire", "") if ruptures else ""}


MARK = {"ok": "✓", "rupture": "✗", "pas_encore": "·", "facultatif": "~"}


def _detail(item, ordre, phases, pc):
    r = evaluate(item, ordre, phases, pc)
    print(f"Item : {item.get('id','?')} - {item.get('label','')}")
    print(f"Phase courante : {pc}\n")
    print("Chaîne :")
    for nom, statut, prop, exig in r["etat"]:
        suff = {"rupture": f"  MANQUANT (exigible dès {exig}) -> {prop}",
                "pas_encore": f"  (exigible dès {exig})",
                "facultatif": "  (facultatif)"}.get(statut, "")
        print(f"  [{MARK[statut]}] {nom:8}{suff}")
    if r["ruptures"]:
        print(f"\n{len(r['ruptures'])} rupture(s). Où aller : {r['ou_aller']}.")
    else:
        print("\nChaîne complète pour la phase courante.")


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 else "demo"
    target = sys.argv[2] if len(sys.argv) > 2 else None
    ordre, phases = load_chaine(mission)
    if not ordre:
        print(f"[!] pas de chaîne dans profiles/{mission}/method.yaml (bloc `tracabilite > ordre`)."); return 2
    data = load_items(mission)
    if data is None:
        print(f"[!] pas de profiles/{mission}/tracabilite.yml (items de la chaîne)."); return 2
    items = data.get("items") or []
    pc = data.get("phase_courante") or (phases[-1] if phases else "")
    if target:
        it = next((i for i in items if str(i.get("id")) == target), None)
        if not it:
            print(f"[!] item '{target}' introuvable."); return 2
        _detail(it, ordre, phases, pc)
    else:
        rompus = 0
        print(f"Traçabilité de la mission {mission} - phase « {pc} », {len(items)} item(s) :\n")
        print(f"  {'id':8} {'état':16} prochaine action")
        print("  " + "-" * 62)
        for it in items:
            r = evaluate(it, ordre, phases, pc)
            if r["ruptures"]:
                rompus += 1
                etat = f"{len(r['ruptures'])} rupture(s)"
                man = ",".join(m.get("maillon") for m in r["ruptures"])
                action = f"{r['ou_aller']} ({man})"
            else:
                etat, action = "complète", "-"
            print(f"  {str(it.get('id')):8} {etat:16} {action}")
        print(f"\n  {rompus}/{len(items)} item(s) en rupture.  Détail : pm run trace-audit {mission} <id>")
    print("\nAudit en lecture seule : il dit où aller, il ne modifie rien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
