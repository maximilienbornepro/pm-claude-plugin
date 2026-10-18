#!/usr/bin/env python3
"""Tests - registre de templates (objet × solution) + câblage scaffold (DM-020).
python3 framework/harness/test_templates.py"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(ROOT / "framework" / "generators" / "scaffold"))
os.environ["PMF_PROFILES"] = str(ROOT / "profiles")
import templates as T  # noqa: E402
import scaffold_notion as SN  # noqa: E402

REQUIRED = {"object", "solution", "title"}


def test_catalog():
    cat = T.catalog()
    assert set(T.OBJECTS) <= set(cat.get("notion", []))               # notion : les 4 objets
    assert {"raci", "risks"} <= set(cat.get("excel", []))             # excel : raci + risks
    assert "clickup" in T.solutions()                                  # dossier prévu


def test_tous_les_templates_bien_formes():
    for sol in T.solutions():
        for obj in T.catalog()[sol]:
            tpl = T.load(sol, obj)
            assert tpl, f"{sol}/{obj} ne charge pas"
            assert REQUIRED <= set(tpl), f"{sol}/{obj} : clés manquantes {REQUIRED - set(tpl)}"
            assert tpl["solution"] == sol and tpl["object"] == obj, f"{sol}/{obj} : object/solution incohérents"
            for k, v in (tpl.get("options") or {}).items():
                assert isinstance(v, list), f"{sol}/{obj} : option {k} n'est pas une liste"
            for k, v in (tpl.get("legende") or {}).items():
                assert isinstance(v, list), f"{sol}/{obj} : legende {k} n'est pas une liste"


def test_sujets_notion_etats_et_thematiques():
    t = T.load("notion", "sujets")
    assert "Thematique:select" in t["properties"]                     # la propriété Thématique
    assert t["options"]["Thematique"]                                 # des thématiques
    assert "en revue" in t["options"]["Statut"]                       # les états par sujet
    vues = [v.get("name") for v in t["views"]]
    assert "Par thematique" in vues


def test_excel_base_sur_sinbad():
    r = T.load("excel", "risks")
    assert r["columns"] == ["Risk", "Probability", "Impact", "Detail"]  # structure réelle SINBAD
    assert r["legende"]["probability"] == ["High", "Medium", "Low"]     # échelle réelle
    a = T.load("excel", "raci")
    assert a["layout"] == "matrix" and a.get("per_role_sheets") is True  # matrice + feuilles par rôle


def test_risks_pointe_le_bareme():
    assert "baremes.risque" in (T.load("notion", "risks").get("bareme_ref") or "")
    assert "baremes.risque" in (T.load("excel", "risks").get("bareme_ref") or "")


def test_scaffold_lit_le_template():
    # _db_block('sujets') via la solution notion -> doit porter les OPTIONS (états + thématiques)
    db = SN._db_block("sujets", {}, "notion")
    assert db["title"] == "Suivi des sujets" and db["solution"] == "notion"
    assert "Thematique" in db["options"] and "Statut" in db["options"]
    assert db["exemples"]                                             # exemples repris du template


def test_load_absent_rend_none():
    assert T.load("clickup", "sujets") is None
    assert T.load("notion", "objet_inexistant") is None


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
