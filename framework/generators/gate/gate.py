#!/usr/bin/env python3
"""gate - score les PORTES (gates) d'une mission, déclarées en donnée, et RECOMMANDE.

A6 (DM-016). La méthode est une DONNÉE : les portes d'une mission vivent dans
`profiles/<mission>/gate.yml`, sous `gates:` (une liste - ex. le GTF : Gate 0 à Gate 6). Chaque porte
porte ses critères (0/0,5/1), son seuil, et éventuellement l'acte humain de franchissement et des
waivers. Ce script COMPTE ; il ne valide pas. Doctrine :

  - aucun franchissement AUTOMATIQUE : seuil atteint ≠ porte franchie ; il faut un ACTE HUMAIN tracé ;
  - un bloquant (critère à 0) se lève par un WAIVER à 8 champs dont une ÉCHÉANCE : un waiver expiré
    REDEVIENT un bloquant (fail-closed) ;
  - un handoff « waivé » n'est pas « recommandé » : le verdict change de nom, pas de nature.

    python3 framework/generators/gate/gate.py [mission]            # vue d'ensemble des gates
    python3 framework/generators/gate/gate.py [mission] <gate-id>  # détail d'une porte
"""
import sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof  # noqa: E402
import yamlmin  # noqa: E402  - parseur YAML imbriqué (gates -> criteria/waivers), sans PyYAML
import method as M  # noqa: E402  - seuil par défaut d'une porte lu dans method.yaml (A4)

WAIVER_FIELDS = ["bloquant", "approbateur", "date", "motif", "echeance", "surveillance", "remediation", "cible"]
ACTE_FIELDS = ["approbateur", "date", "motif"]


def _date(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def evaluate(gate, today=None, default_seuil=90):
    """État d'UNE porte (dict). Rend un dict de résultat, sans rien afficher."""
    today = today or datetime.date.today()
    scale = [float(x) for x in (gate.get("scale") or [0, 0.5, 1])]
    seuil = gate.get("threshold", default_seuil)
    crits = gate.get("criteria") or []
    acte = gate.get("acte_humain") or {}
    scored, bad = [], []
    for c in crits:
        v = c.get("score")
        if v is None or v == "":
            continue                      # critère NON ÉVALUÉ : exclu du calcul (≠ 0)
        try:
            s = float(v)
        except Exception:
            s = 0.0
        if s not in scale:
            bad.append(c.get("id"))
        scored.append((c.get("id"), s))
    bloquants = {cid for cid, s in scored if s == 0.0}
    # Waivers d'abord : un bloquant valablement waivé n'est plus un véto ; son RISQUE est suivi à part
    # (surveillance / remédiation), pas porté par le score. Il sort donc du calcul, comme un non-évalué.
    valides, expire, invalides = {}, [], []
    for w in (gate.get("waivers") or []):
        manque = [f for f in WAIVER_FIELDS if not w.get(f)]
        if manque:
            invalides.append((w.get("bloquant") or "?", manque)); continue
        ech = _date(w.get("echeance"))
        (expire.append((w.get("bloquant"), w.get("echeance"))) if ech and ech < today
         else valides.__setitem__(w.get("bloquant"), w))
    effectif = [(cid, s) for cid, s in scored if cid not in valides]   # hors bloquants waivés
    pct = round(sum(s for _, s in effectif) / len(effectif) * 100) if effectif else None  # None = non entamée
    ouverts = sorted(b for b in bloquants if b not in valides)
    seuil_atteint = pct is not None and pct >= seuil and not ouverts
    acte_ok = all(acte.get(f) for f in ACTE_FIELDS)
    if pct is None:
        verdict = "non entamée"
    elif ouverts or pct < seuil:
        verdict = "NON ATTEINT - handoff non recommandé"
    elif valides:
        verdict = "WAIVÉ - franchissement assumé (trace au dossier)"
    else:
        verdict = "ATTEINT - handoff recommandé"
    return {"pct": pct, "seuil": seuil, "verdict": verdict, "seuil_atteint": seuil_atteint,
            "franchie": seuil_atteint and acte_ok, "acte_ok": acte_ok, "n_crit": len(crits),
            "bloquants_ouverts": ouverts, "waivers_valides": valides,
            "waivers_expire": expire, "waivers_invalides": invalides, "bad_scale": bad}


def load_gates(mission):
    path = prof.mission_file(mission, "gate.yml")
    if not Path(path).exists():
        return []
    g = yamlmin.load(Path(path).read_text(encoding="utf-8")) or {}
    gates = g.get("gates")
    if gates is None and g.get("gate"):          # tolère une porte unique
        gates = [g["gate"]]
    return gates or []


def _detail(gate, seuil_defaut=90):
    r = evaluate(gate, default_seuil=seuil_defaut)
    print(f"Porte : {gate.get('id','?')} - {gate.get('name','')}")
    if gate.get("summary"):
        print(f"  {gate['summary']}")
    if r["pct"] is None:
        print("  (non entamée : aucun critère noté)"); return
    hors = f"   (hors {len(r['waivers_valides'])} critère(s) waivé(s))" if r["waivers_valides"] else ""
    print(f"Score : {r['pct']} %   (seuil {r['seuil']} %){hors}   -   {r['verdict']}")
    if r["seuil_atteint"] and not r["acte_ok"]:
        print("Franchie : NON - seuil atteint, mais aucun ACTE HUMAIN tracé (rôle, date, motif).")
    else:
        print(f"Franchie : {'OUI' if r['franchie'] else 'NON'}.")
    print("\nCritères :")
    for c in (gate.get("criteria") or []):
        v = c.get("score")
        mark = "·  " if (v is None or v == "") else {1.0: "1  ", 0.5: "0,5", 0.0: "0  "}.get(float(v), str(v))
        print(f"  [{mark}] {c.get('id'):5} {c.get('label','')}")
    if r["bloquants_ouverts"]:
        print("\nBloquants OUVERTS :")
        for b in r["bloquants_ouverts"]:
            lbl = next((c.get("label", "") for c in (gate.get("criteria") or []) if c.get("id") == b), "")
            print(f"  - {b} : {lbl}")
    for b, w in r["waivers_valides"].items():
        print(f"  waiver VALIDE : {b} levé par {w['approbateur']} jusqu'au {w['echeance']} (cible : {w['cible']})")
    for b, e in r["waivers_expire"]:
        print(f"  waiver EXPIRÉ : {b} (échu le {e}) - le bloquant redevient OUVERT")
    for b, m in r["waivers_invalides"]:
        print(f"  waiver INVALIDE : {b} - manque {', '.join(m)} (ne lève rien)")
    if r["bad_scale"]:
        print(f"\n[!] scores hors échelle : {r['bad_scale']}")


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 else "demo"
    target = sys.argv[2] if len(sys.argv) > 2 else None
    gates = load_gates(mission)
    if not gates:
        print(f"[!] pas de gates dans profiles/{mission}/gate.yml (clé `gates:`)."); return 2
    sd = M.seuil(mission, "gate_defaut", 90)   # seuil par défaut d'une porte, en donnée (method.yaml, A4)
    if target:
        gate = next((g for g in gates if str(g.get("id")) == target or g.get("name") == target), None)
        if not gate:
            print(f"[!] porte '{target}' introuvable. Portes : {', '.join(str(g.get('id')) for g in gates)}"); return 2
        _detail(gate, sd)
    else:
        print(f"Portes de la mission {mission} ({len(gates)}) :\n")
        print(f"  {'id':7} {'score':6} {'franchie':9} porte")
        print("  " + "-" * 60)
        for g in gates:
            r = evaluate(g, default_seuil=sd)
            sc = "-" if r["pct"] is None else f"{r['pct']}%"
            fr = "-" if r["pct"] is None else ("OUI" if r["franchie"] else "non")
            flag = "  ⚠" if (r["seuil_atteint"] and not r["acte_ok"]) else ("  ⛔" if r["bloquants_ouverts"] else "")
            print(f"  {str(g.get('id')):7} {sc:6} {fr:9} {g.get('name','')}{flag}")
        print("\n  ⚠ seuil atteint mais pas d'acte humain · ⛔ bloquant ouvert")
        print(f"  Détail : pm run gate {mission} <id>")
    print("\nCe générateur RECOMMANDE ; il ne valide pas. Le franchissement est un acte humain tracé.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
