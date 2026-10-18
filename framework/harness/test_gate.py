#!/usr/bin/env python3
"""Tests A6 - mécanisme des portes (gate). python3 framework/harness/test_gate.py

Teste `evaluate()` sur des portes construites à la main (déterministe, sans fichier) + un parse
du profil demo via yamlmin. Date de référence figée pour que l'expiration des waivers soit stable."""
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(ROOT / "framework" / "generators" / "gate"))
import yamlmin          # noqa: E402
import gate as G        # noqa: E402

TODAY = datetime.date(2026, 10, 18)


def _w(bloquant, echeance, **over):
    """Un waiver COMPLET (8 champs) ; `over` pour en casser/dater un."""
    w = {"bloquant": bloquant, "approbateur": "CP", "date": "2026-01-01", "motif": "m",
         "echeance": echeance, "surveillance": "revue", "remediation": "R", "cible": "c"}
    w.update(over)
    return w


def test_franchie_avec_acte():
    g = {"criteria": [{"id": "A", "score": 1}, {"id": "B", "score": 1}],
         "acte_humain": {"approbateur": "Sponsor", "date": "2026-10-01", "motif": "comité"}}
    r = G.evaluate(g, today=TODAY)
    assert r["pct"] == 100 and r["seuil_atteint"] and r["acte_ok"] and r["franchie"]
    assert r["verdict"].startswith("ATTEINT")


def test_seuil_atteint_sans_acte_pas_franchie():
    g = {"criteria": [{"id": "A", "score": 1}, {"id": "B", "score": 1}]}
    r = G.evaluate(g, today=TODAY)
    assert r["seuil_atteint"] and not r["acte_ok"] and not r["franchie"]


def test_acte_incomplet_ne_compte_pas():
    g = {"criteria": [{"id": "A", "score": 1}],
         "acte_humain": {"approbateur": "Sponsor", "date": "2026-10-01"}}  # motif manquant
    r = G.evaluate(g, today=TODAY)
    assert not r["acte_ok"] and not r["franchie"]


def test_bloquant_sans_waiver_reste_ouvert():
    g = {"criteria": [{"id": "A", "score": 1}, {"id": "B", "score": 0}]}
    r = G.evaluate(g, today=TODAY)
    assert "B" in r["bloquants_ouverts"] and not r["seuil_atteint"]
    assert r["verdict"].startswith("NON ATTEINT")


def test_waiver_valide_leve_le_bloquant():
    g = {"criteria": [{"id": "A", "score": 1}, {"id": "B", "score": 0}],
         "waivers": [_w("B", "2026-12-31")]}          # échéance future
    r = G.evaluate(g, today=TODAY)
    assert r["bloquants_ouverts"] == [] and "B" in r["waivers_valides"]
    assert r["verdict"].startswith("WAIVÉ")


def test_waiver_expire_ne_leve_pas():
    g = {"criteria": [{"id": "A", "score": 1}, {"id": "B", "score": 0}],
         "waivers": [_w("B", "2026-09-01")]}          # échéance passée
    r = G.evaluate(g, today=TODAY)
    assert "B" in r["bloquants_ouverts"] and ("B", "2026-09-01") in r["waivers_expire"]
    assert "B" not in r["waivers_valides"]


def test_waiver_incomplet_ne_leve_pas():
    g = {"criteria": [{"id": "A", "score": 1}, {"id": "B", "score": 0}],
         "waivers": [_w("B", "2026-12-31", remediation="")]}   # un champ vide -> invalide
    r = G.evaluate(g, today=TODAY)
    assert "B" in r["bloquants_ouverts"] and r["waivers_invalides"]
    assert "B" not in r["waivers_valides"]


def test_non_evalue_exclu_du_calcul():
    # un critère sans score ne compte pas (≠ 0) : 2x1 + 1 non noté -> 100 %, pas 66 %
    g = {"criteria": [{"id": "A", "score": 1}, {"id": "B", "score": 1}, {"id": "C"}]}
    r = G.evaluate(g, today=TODAY)
    assert r["pct"] == 100 and "C" not in r["bloquants_ouverts"]


def test_aucun_score_non_entamee():
    g = {"criteria": [{"id": "A"}, {"id": "B"}]}
    r = G.evaluate(g, today=TODAY)
    assert r["pct"] is None and r["verdict"] == "non entamée"


def test_demo_parse_7_gates():
    d = yamlmin.load((ROOT / "profiles" / "demo" / "gate.yml").read_text(encoding="utf-8"))
    gates = {g["id"]: g for g in d["gates"]}
    assert len(gates) == 7 and set(gates) == {f"gate{i}" for i in range(7)}
    # gate3 du demo : waiver expiré -> bloquant rouvert
    r3 = G.evaluate(gates["gate3"], today=TODAY)
    assert "G3.2" in r3["bloquants_ouverts"]
    # gate0 du demo : franchie (acte humain présent)
    assert G.evaluate(gates["gate0"], today=TODAY)["franchie"]


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    ok = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS {fn.__name__}"); ok += 1
        except AssertionError as e:
            print(f"  FAIL {fn.__name__}: {e or 'assertion'}")
        except Exception as e:
            print(f"  ERR  {fn.__name__}: {e}"); traceback.print_exc()
    print(f"\n{ok}/{len(fns)} tests OK")
    sys.exit(0 if ok == len(fns) else 1)
