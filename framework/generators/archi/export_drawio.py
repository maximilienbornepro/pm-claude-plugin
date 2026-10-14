#!/usr/bin/env python3
"""export_drawio - model.json -> fichier .drawio (mxGraph), généré, jamais édité à la main.

Page "Overview" = toute l'archi connectée (tous les noeuds + flux), 100% dérivée du modèle.
Pages par écran = une par vue, SI le modèle porte `view_members` (map vue -> [ids]) ; sinon on
n'invente pas le contenu d'une vue et on ne génère que l'overview (+ pages vides signalées).

    python3 export_drawio.py <mission> [-o sortie.drawio]
Lecture seule côté mission : lit model.json, écrit UNIQUEMENT le .drawio de sortie.
"""
import sys, os, json, math, html
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import profile as prof  # noqa: E402


def _entities(m):
    """id -> (label, sub) pour tout ce qui peut être un noeud.
    Supporte l'ancien schéma (actors/tools/...) et le nouveau (`entities`, voir SCHEMA.md)."""
    out = {}
    for key in ("entities", "actors", "tools", "components", "stores", "partner_apps"):
        for e in m.get(key, []) or []:
            if isinstance(e, dict) and "id" in e:
                out[e["id"]] = (e.get("label", e["id"]), e.get("sub", ""))
    return out


def _links(m):
    """id de shape -> id de vue cible (champ `link`), pour les liens inter-pages draw.io."""
    out = {}
    for key in ("entities", "zones", "actors", "tools", "components", "stores", "partner_apps"):
        for e in m.get(key, []) or []:
            if isinstance(e, dict) and e.get("id") and e.get("link"):
                out[e["id"]] = e["link"]
    return out


def _esc(s):
    return html.escape(s or "", quote=True)


def _page(name, node_ids, ent, flows, page_id=None, links=None, page_ids=None):
    """Une page draw.io (diagram) : noeuds en grille + flux entre eux.

    `page_id`  : id stable du <diagram> (= id de la vue), pour les liens cross-page.
    `links`    : {id shape -> id vue cible} ; un shape lié reçoit un lien draw.io
                 `link="data:page/id,<cible>"`. draw.io ne lit ce lien que s'il est porté
                 par un élément <object> enveloppant le <mxCell> (sa `value` doit être un
                 nœud XML) : un attribut `link` posé à nu sur un <mxCell> est ignoré.
    `page_ids` : ids de pages valides (on n'émet un lien que vers une page existante).
    """
    links = links or {}
    page_ids = page_ids if page_ids is not None else set()
    ids = [i for i in node_ids if i in ent]
    n = len(ids) or 1
    cols = max(1, int(math.ceil(math.sqrt(n))))
    cells = []
    for k, i in enumerate(ids):
        x, y = 40 + (k % cols) * 220, 40 + (k // cols) * 130
        label, sub = ent[i]
        val = _esc(label) + ("&#10;" + _esc(sub) if sub else "")
        tgt = links.get(i)
        tgt = tgt if (tgt in page_ids and tgt != page_id) else None
        geom = f'<mxGeometry x="{x}" y="{y}" width="160" height="56" as="geometry"/>'
        if tgt:
            # shape cliquable -> autre page (liseré bleu pour signaler le drill-down)
            style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#2F6FF0;strokeWidth=2;"
            cells.append(
                f'<object id="{_esc(i)}" label="{val}" link="data:page/id,{_esc(tgt)}">'
                f'<mxCell style="{style}" vertex="1" parent="1">{geom}</mxCell></object>'
            )
        else:
            style = "rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#1D1D1F;"
            cells.append(
                f'<mxCell id="{_esc(i)}" value="{val}" style="{style}" '
                f'vertex="1" parent="1">{geom}</mxCell>'
            )
    sset = set(ids)
    e = 0
    for f in flows:
        a, b = f.get("from"), f.get("to")
        if a in sset and b in sset:
            e += 1
            kind = f.get("kind", "")
            start = "classic" if kind in ("read", "pull") else "none"  # double flèche = pull/read
            style = f"endArrow=classic;startArrow={start};html=1;rounded=0;strokeColor=#0033FF;"
            cells.append(
                f'<mxCell id="e{_esc(page_id or name)}_{e}" value="{_esc(f.get("label",""))}" style="{style}" '
                f'edge="1" parent="1" source="{_esc(a)}" target="{_esc(b)}">'
                f'<mxGeometry relative="1" as="geometry"/></mxCell>'
            )
    body = ("<mxCell id=\"0\"/><mxCell id=\"1\" parent=\"0\"/>" + "".join(cells))
    did = f' id="{_esc(page_id)}"' if page_id else ""
    return (f'<diagram{did} name="{_esc(name)}"><mxGraphModel dx="900" dy="600" grid="1" '
            f'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
            f'pageWidth="1169" pageHeight="826" math="0" shadow="0"><root>{body}</root></mxGraphModel></diagram>')


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 else "sinbad"
    out = None
    if "-o" in sys.argv:
        out = sys.argv[sys.argv.index("-o") + 1]
    # PMF_ARCH_MODEL : rendu depuis un modèle direct, SANS exiger profiles/<mission>/architecture.yml
    env_model = os.environ.get("PMF_ARCH_MODEL")
    if env_model:
        model_path = env_model
    else:
        cfg = prof._load_yaml(prof.mission_dir(mission) / "archi.yml")
        model_path = cfg["model_json"]
    m = json.load(open(model_path, encoding="utf-8"))
    ent, flows, views = _entities(m), m.get("flows", []), m.get("views", [])
    links = _links(m)

    pages, missing = [], []
    new_style = bool(views) and isinstance(views[0], dict)
    if new_style:
        # nouveau schéma : une page PAR ÉCRAN, dérivée de views[].members (SCHEMA.md)
        page_ids = {v.get("id") for v in views if v.get("members")}
        for v in views:
            vid = v.get("id")
            name = v.get("label") or vid
            vmembers = v.get("members")
            if vmembers:
                pages.append(_page(name, vmembers, ent, flows,
                                   page_id=vid, links=links, page_ids=page_ids))
            else:
                missing.append(vid)
        overview_note = f"{len(pages)} vue(s) (views[].members)"
    else:
        # ancien schéma : overview synthétique (tous les flux) + éventuel view_members
        members = m.get("view_members", {})  # optionnel : vue -> [ids]
        pages.append(_page("Overview (tous les flux)", list(ent.keys()), ent, flows, page_id="overview"))
        for v in views:
            if v in members:
                pages.append(_page(v, members[v], ent, flows, page_id=v))
            else:
                missing.append(v)
        overview_note = (f"1 overview ({len(ent)} noeuds, {len(flows)} flux)"
                         + (f" + {len(members)} vue(s)" if members else ""))

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="pm-framework">' + "".join(pages) + "</mxfile>"
    out = out or str(ROOT.parent / "scratchpad" / f"architecture_{mission}.drawio")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(xml, encoding="utf-8")

    print(f"Écrit : {out}")
    print(f"Pages : {len(pages)}  ({overview_note})")
    if missing:
        hint = "ajouter `members` à la vue" if new_style else "ajouter `view_members` au modèle"
        print(f"Vues sans contenu ({hint}) : {', '.join(str(x) for x in missing)}")


if __name__ == "__main__":
    main()
