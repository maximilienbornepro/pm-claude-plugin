#!/usr/bin/env python3
"""cockpit - porte d'entrée unique : « où en est la mission, que fait-on ? » (A8, DM-019).

CALCULE l'état de la mission depuis la DONNÉE - portes (A6), chaîne de traçabilité (A5) - et en
DÉDUIT la suite : une liste d'actions priorisées, chacune avec la commande `pm run …` à lancer et,
en multi-compte, le compte vers lequel elle route (dérivation A1). Rien n'est recalculé de mémoire :
la suite se lit de l'état. Lecture seule ; il n'exécute rien, il montre et route.

    python3 framework/generators/cockpit/cockpit.py [mission]

Dépend de A1 (account_for), A4/A5 (traçabilité), A6 (gates). Les autres générateurs restent appelables
directement ; le cockpit est le point d'entrée qui dit lequel, et dans quel ordre.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(ROOT / "framework" / "generators" / "gate"))
sys.path.insert(0, str(ROOT / "framework" / "generators" / "trace-audit"))
import profile as prof   # noqa: E402
import method as M       # noqa: E402
import gate as GATE      # noqa: E402
import trace_audit as TRACE  # noqa: E402


def etat_gates(mission):
    """Classe les portes : franchies / en attente d'acte (⚠) / bloquées (⛔) / en cours / non entamées."""
    gates = GATE.load_gates(mission)
    sd = M.seuil(mission, "gate_defaut", 90)
    classes = {"franchie": [], "acte": [], "bloquee": [], "en_cours": [], "non_entamee": []}
    details = {}
    for g in gates:
        r = GATE.evaluate(g, default_seuil=sd)
        gid = str(g.get("id"))
        details[gid] = r
        if r["pct"] is None:
            classes["non_entamee"].append(gid)
        elif r["franchie"]:
            classes["franchie"].append(gid)
        elif r["bloquants_ouverts"]:
            classes["bloquee"].append(gid)
        elif r["seuil_atteint"] and not r["acte_ok"]:
            classes["acte"].append(gid)
        else:
            classes["en_cours"].append(gid)
    return gates, classes, details


def etat_trace(mission):
    """(phase_courante, nombre d'items, liste des items en rupture avec où aller)."""
    ordre, phases = TRACE.load_chaine(mission)
    data = TRACE.load_items(mission)
    if not ordre or data is None:
        return None, 0, []
    items = data.get("items") or []
    pc = data.get("phase_courante") or (phases[-1] if phases else "")
    rompus = []
    for it in items:
        r = TRACE.evaluate(it, ordre, phases, pc)
        if r["ruptures"]:
            rompus.append((it.get("id"), r["ou_aller"], [m.get("maillon") for m in r["ruptures"]]))
    return pc, len(items), rompus


def _compte(mission, command):
    """Le compte vers lequel une commande route, en multi-compte (A1), sinon None."""
    try:
        return prof.account_for(mission, command) if prof.is_multi_account() else None
    except Exception:
        return None


def actions_suivantes(mission, cl, rompus):
    """La suite, DÉDUITE de l'état : liste de (label, commande, base_commande), par priorité."""
    actions = []
    for gid in cl["bloquee"]:
        actions.append((f"Lever le bloquant de {gid} (puis tracer l'acte de franchissement)",
                        f"pm run gate {mission} {gid}", "gate"))
    for gid in cl["acte"]:
        actions.append((f"Tracer l'acte humain de franchissement de {gid} (rôle, date, motif)",
                        f"pm run gate {mission} {gid}", "gate"))
    for gid in cl["en_cours"]:
        actions.append((f"Compléter les critères de {gid} pour atteindre le seuil",
                        f"pm run gate {mission} {gid}", "gate"))
    if rompus:
        actions.append((f"Résorber {len(rompus)} rupture(s) de traçabilité",
                        f"pm run trace-audit {mission}", "trace-audit"))
    if cl["non_entamee"] and not (cl["bloquee"] or cl["acte"] or cl["en_cours"]):
        g0 = cl["non_entamee"][0]
        actions.append((f"Ouvrir la porte suivante : {g0}", f"pm run gate {mission} {g0}", "gate"))
    return actions


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 else "demo"
    gates, cl, det = etat_gates(mission)
    pc, n_items, rompus = etat_trace(mission)

    # Projet vierge (ni portes, ni chaîne) : le cockpit n'invente pas d'état, il renvoie vers l'amorçage.
    if not gates and pc is None:
        print(f"Cockpit de la mission {mission}\n")
        print("Mission encore vierge : pas de portes (gate.yml) ni de chaîne de traçabilité.")
        print("\nAmorcer le projet (parcours classique) :")
        print(f"  1. pm run init {mission}            # crée le profil (create-si-absent, dry-run par défaut)")
        print(f"  2. pm run setup {mission}           # complète le profil, champ par champ")
        print(f"  3. pm run drive-scaffold {mission} / notion-scaffold {mission}   # l'arborescence")
        print("\nLe cockpit est une OPTION : il résume l'état quand il y en a un. L'init reste le point de départ.")
        return 0

    print(f"Cockpit de la mission {mission}")
    if pc:
        print(f"Phase : {pc}")
    print()

    # --- état des portes ---
    if gates:
        print("Portes (GTF) :")
        def nom(gid):
            return next((g.get("name", "") for g in gates if str(g.get("id")) == gid), "")
        if cl["franchie"]:
            print(f"  franchies  : {', '.join(cl['franchie'])}")
        for gid in cl["bloquee"]:
            b = ", ".join(det[gid]["bloquants_ouverts"])
            print(f"  ⛔ bloquée  : {gid} ({nom(gid)}) - bloquant {b}")
        for gid in cl["acte"]:
            print(f"  ⚠ à acter  : {gid} ({nom(gid)}) - seuil atteint, acte humain manquant")
        for gid in cl["en_cours"]:
            print(f"  en cours   : {gid} ({nom(gid)}) - {det[gid]['pct']} % (seuil {det[gid]['seuil']} %)")
        if cl["non_entamee"]:
            print(f"  à venir    : {', '.join(cl['non_entamee'])}")
        print()

    # --- état de la traçabilité ---
    if pc is not None:
        if rompus:
            print(f"Traçabilité : {len(rompus)}/{n_items} item(s) en rupture")
            for iid, ou, man in rompus[:5]:
                print(f"  {iid} -> {ou} ({','.join(man)})")
        else:
            print(f"Traçabilité : {n_items} item(s), aucune rupture")
        print()

    # --- la suite, CALCULÉE depuis l'état ---
    actions = []
    for gid in cl["bloquee"]:
        actions.append((f"Lever le bloquant de {gid} (puis tracer l'acte de franchissement)",
                        f"pm run gate {mission} {gid}", "gate"))
    for gid in cl["acte"]:
        actions.append((f"Tracer l'acte humain de franchissement de {gid} (rôle, date, motif)",
                        f"pm run gate {mission} {gid}", "gate"))
    for gid in cl["en_cours"]:
        actions.append((f"Compléter les critères de {gid} pour atteindre le seuil",
                        f"pm run gate {mission} {gid}", "gate"))
    if rompus:
        actions.append((f"Résorber {len(rompus)} rupture(s) de traçabilité",
                        f"pm run trace-audit {mission}", "trace-audit"))
    if cl["non_entamee"] and not (cl["bloquee"] or cl["acte"] or cl["en_cours"]):
        g0 = cl["non_entamee"][0]
        actions.append((f"Ouvrir la porte suivante : {g0}", f"pm run gate {mission} {g0}", "gate"))

    print("Prochaines actions (calculé depuis l'état) :")
    if not actions:
        print("  rien à signaler : portes franchies et traçabilité complète pour la phase.")
    for i, (label, cmd, base) in enumerate(actions, 1):
        acc = _compte(mission, base)
        tag = f"   [{acc}]" if acc else ""
        print(f"  {i}. {label}")
        print(f"       {cmd}{tag}")
    print("\n  Boîte à outils complète : pm list")
    print("Le cockpit calcule la suite depuis l'état ; il ne décide ni n'exécute rien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
