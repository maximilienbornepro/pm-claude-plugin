#!/usr/bin/env python3
"""Tests du schéma d'archi model-first : couches (abstraction), loupes, couleurs, import draw.io.
python3 framework/harness/test_archi.py"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "framework" / "generators" / "archi"))
import abstraction as A    # noqa: E402
import build_html as B     # noqa: E402
import export_drawio as X  # noqa: E402
import import_drawio as I  # noqa: E402
import validate as V       # noqa: E402

DEMO = json.load(open(ROOT / "profiles" / "demo" / "architecture" / "model.json", encoding="utf-8"))


def _invariants(html):
    return {t: fn(html) for t, fn in V.CHECKS if fn(html)}


def _overview(html):
    return re.search(r'<section class="view" id="v-overview">(.*?)</section>', html, re.S).group(1)


def test_demo_rendu_passe_les_7_invariants_dans_tous_les_modes():
    for mode in A.MODES:
        modes = {L["id"]: (mode if mode != "masque" or A.maskable(L) else "abstrait") for L in A.layers(DEMO)}
        bad = _invariants(B.build_html(DEMO, modes))
        assert not bad, f"{mode}: {bad}"


def test_tout_element_cliquable_porte_une_loupe():
    html = B.build_html(DEMO, {"donnees": "abstrait"})
    blocs = re.findall(r'<g class="(?:nodelink|zonelink)"[^>]*>(.*?)</g>', html, re.S)
    assert blocs and all('class="zoom"' in b for b in blocs)


def test_couche_abstraite_devient_un_bloc_cliquable():
    ov = _overview(B.build_html(DEMO, {"exploitation": "abstrait"}))
    assert 'data-go="exploitation"' in ov and "Exploitation" in ov
    assert ">Supervision<" not in ov          # le membre a disparu au profit du bloc


def test_couche_masquee_absente_de_la_vue_d_ensemble_mais_pas_des_autres_vues():
    html = B.build_html(DEMO, {"partenaires": "masque"})
    assert ">Partner A<" not in _overview(html)
    assert ">Partner A<" in re.search(r'id="v-donnees"(.*?)</section>', html, re.S).group(1)


def test_couche_du_chemin_principal_ne_se_masque_pas():
    try:
        A.parse_set(DEMO, "donnees=masque", {})
    except ValueError:
        return
    raise AssertionError("donnees=masque aurait dû être refusé")


def test_couche_sans_vue_de_detail_en_recoit_une():
    m = json.loads(json.dumps(DEMO))
    m["layers"].append({"id": "acces", "label": "Accès", "members": ["frontend", "bff"]})
    html = B.build_html(m, {"acces": "abstrait"})
    assert 'id="v-couche-acces"' in html and 'data-go="couche-acces"' in html
    assert not _invariants(html)


def test_questions_public_d_abord_puis_chaque_couche():
    q = A.questions(DEMO, None, None)
    assert q[0]["id"] == "_public" and [x["id"] for x in q[1:]] == [L["id"] for L in A.layers(DEMO)]
    assert all(x["raison"] for x in q)
    ops = [x for x in A.questions(DEMO, None, "direction") if x["id"] == "exploitation"][0]
    assert ops["proposition"] == "masque"


def test_couleurs_de_role_et_encart_d_equipe():
    html = B.build_html(DEMO)
    assert "--auth:" in html and "var(--auth)" in html        # token défini dans :root et utilisé
    assert 'class="zone team"' in html
    assert 'class="flow main"' in html                        # flux principal animé


def test_aller_retour_drawio_conserve_les_entites():
    xml, _, _ = X.build_xml(DEMO)
    m = I.build_model(xml)
    assert {e["id"] for e in DEMO["entities"]} <= {e["id"] for e in m["entities"]}


HAND = """<mxfile><diagram id="p1" name="Main"><mxGraphModel><root>
<mxCell id="0"/><mxCell id="1" parent="0"/>
<mxCell id="z" value="SAI INFRA" style="rounded=0;verticalAlign=top;" vertex="1" parent="1"><mxGeometry x="0" y="0" width="400" height="300" as="geometry"/></mxCell>
<mxCell id="kc" value="Identity broker&lt;br&gt;(keycloak)" style="rounded=1;" vertex="1" parent="1"><mxGeometry x="50" y="50" width="120" height="60" as="geometry"/></mxCell>
<mxCell id="fe" value="FRONTEND" style="rounded=1;" vertex="1" parent="1"><mxGeometry x="220" y="50" width="120" height="60" as="geometry"/></mxCell>
<mxCell id="e1" style="edgeStyle=orthogonalEdgeStyle;" edge="1" parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="220" y="80" as="sourcePoint"/><mxPoint x="170" y="80" as="targetPoint"/></mxGeometry></mxCell>
<mxCell id="l1" value="Fetch identity" style="edgeLabel;" vertex="1" connectable="0" parent="e1"><mxGeometry relative="1" as="geometry"/></mxCell>
</root></mxGraphModel></diagram></mxfile>"""


def test_import_drawio_dessine_a_la_main():
    m = I.build_model(HAND)
    ent = {e["id"]: e for e in m["entities"]}
    assert set(ent) == {"kc", "fe"}                              # le libellé de flèche n'est pas une entité
    assert ent["kc"]["zone"] == "z" and [z["id"] for z in m["zones"]] == ["z"]   # zone par imbrication
    assert m["flows"] == [{"from": "fe", "to": "kc", "label": "Fetch identity", "kind": "call"}]
    done = I.deduce_logos(m, I.logo_sources())
    assert ("kc", "keycloak") in done and ("fe", "react") in done and m["logos"]["keycloak"].startswith("data:")


def test_enrich_import_brut_vers_style_par_defaut():
    """Un import brut (sans role ni couleur) ressort enrichi : couleurs de role, chemin principal anime,
    loupes, cadre EKS > Namespace dans la zone englobante, positions explicites, 4 questions systematiques."""
    import enrich as E
    raw = {"zones": [{"id": "infra", "label": "SAI INFRASTRUCTURE", "parent": None},
                     {"id": "zp", "label": "PIPELINE", "parent": "infra"},
                     {"id": "za", "label": "AIFA DAG", "parent": "zp"},
                     {"id": "zr", "label": "SINBAD REPOSITORY", "parent": "infra"},
                     {"id": "zf", "label": "FRONTEND", "parent": "infra"}],
           "entities": [{"id": "in", "label": "/inbox", "zone": "zp"}, {"id": "pr", "label": "Processing", "zone": "za"},
                        {"id": "ou", "label": "Output", "zone": "za"}, {"id": "gw", "label": "API Gateway", "zone": "zr"},
                        {"id": "ev", "label": "EventService", "zone": "zr"}, {"id": "db", "label": "Alert Dashboard", "zone": "zf"},
                        {"id": "sm", "label": "Site Monitoring", "zone": "zf"}],
           "flows": [{"from": "in", "to": "pr"}, {"from": "pr", "to": "ou"}, {"from": "pr", "to": "gw"},
                     {"from": "db", "to": "gw"}, {"from": "in", "to": "ev"}],
           "views": [{"id": "p1", "label": "Big Picture", "members": ["in", "pr", "ou", "gw", "ev", "db", "sm"]}]}
    m, q = E.enrich(raw, "Big Picture")
    z = {x["id"]: x for x in m["zones"]}
    assert z["za"]["color"] == "core" and z["zr"]["color"] == "service" and z["zp"]["color"] == "ops"
    assert z["z-eks"]["parent"] == "infra" and z["z-ns"]["parent"] == "z-eks" and z["zp"]["parent"] == "z-ns"
    assert {x["id"]: x for x in m["entities"]}["gw"]["color"] == "core"          # l'entree API ressort
    assert sum(1 for f in m["flows"] if f.get("main")) == 3                      # pr->ou, pr->gw, db->gw
    assert set(m["views"][0]["layout"]) == set(raw["views"][0]["members"])       # tout est place
    assert "link" not in z["infra"] and z["zr"]["link"] in {v["id"] for v in m["views"]}
    assert [x["couche"] for x in q] == ["Kubernetes / cluster / namespace", "Exploitation",
                                        "REST API / BFF", "SSO / identité"]
    assert [x["present"] for x in q] == [True, False, True, False]               # absent = question, pas de noeud
    assert not _invariants(B.build_html(m))
    # repli d'une couche qui recouvre toute sa zone : le bloc remonte, le cadre redondant disparait
    f = A.apply(m, {"front": "abstrait"})
    blk = {e["id"]: e for e in f["entities"]}["couche-front"]
    assert blk["zone"] == "z-ns" and blk["color"] is None and "couche-front" in f["views"][0]["layout"]
    assert not _invariants(B.build_html(m, {"front": "abstrait", "partners": "abstrait"}))


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
