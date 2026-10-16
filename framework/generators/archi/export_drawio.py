#!/usr/bin/env python3
"""export_drawio - model.json -> fichier .drawio (mxGraph), généré, jamais édité à la main.

Page "Overview" = toute l'archi connectée (tous les noeuds + flux), 100% dérivée du modèle.
Pages par écran = une par vue, SI le modèle porte `view_members` (map vue -> [ids]) ; sinon on
n'invente pas le contenu d'une vue et on ne génère que l'overview (+ pages vides signalées).

    python3 export_drawio.py <mission> [-o sortie.drawio]
Lecture seule côté mission : lit model.json, écrit UNIQUEMENT le .drawio de sortie.
"""
import sys, os, json, math, html, base64
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(HERE.parent))
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


# ------------------------------------------------------------------ logos
SHARED_LOGOS = ROOT / "framework" / "assets" / "logos"
_MIME = {".png": "image/png", ".webp": "image/webp", ".svg": "image/svg+xml",
         ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif"}


def _logo_uri(key, model_logos, dirs):
    """Cle de logo -> data-URI utilisable dans un style draw.io, ou None.
    Ordre : `logos` du modele (comme window.LOGOS), puis dossiers (marque de la mission puis
    bibliotheque partagee framework/assets/logos/). draw.io lit `image=data:<mime>,<base64>` :
    le `;base64` est retire (le `;` casserait le style)."""
    uri = (model_logos or {}).get(key)
    if not uri:
        for d in dirs:
            for f in sorted(Path(d).glob(f"{key}.*")):
                if f.suffix.lower() in _MIME:
                    uri = f"data:{_MIME[f.suffix.lower()]};base64," + base64.b64encode(f.read_bytes()).decode()
                    break
            if uri:
                break
    if not uri or not uri.startswith("data:"):
        return None
    return uri.replace(";base64,", ",", 1)


def _zone_ancestors(zid, zone_by_id):
    out, cur = [], zone_by_id.get(zid, {}).get("parent")
    while cur and cur in zone_by_id and cur not in out:
        out.append(cur)
        cur = zone_by_id[cur].get("parent")
    return out


def _edge_anchors(ra, rb):
    """Memes regles que build_html._orth : cote de sortie/entree selon la dominante H/V."""
    ax, ay, aw, ah = ra
    bx, by, bw, bh = rb
    dx, dy = (bx + bw / 2) - (ax + aw / 2), (by + bh / 2) - (ay + ah / 2)
    if abs(dx) >= abs(dy):
        return (1, .5, 0, .5) if dx >= 0 else (0, .5, 1, .5)
    return (.5, 1, .5, 0) if dy >= 0 else (.5, 0, .5, 1)


def _page(name, node_ids, ent, flows, page_id=None, links=None, page_ids=None,
          model=None, logo_dirs=()):
    """Une page draw.io (diagram), meme mise en page que build_html (layout par zones).

    Zones = conteneurs (cadre pointille + titre), noeuds = enfants du conteneur de leur zone
    (coordonnees relatives), logos = cellules `shape=image` sur plaque blanche, flux = aretes
    orthogonales ancrees comme le SVG. Positions/tailles viennent de build_html (une seule logique).

    `page_id`  : id stable du <diagram> (= id de la vue), pour les liens cross-page.
    `links`    : {id shape -> id vue cible} ; un shape lie recoit `link="data:page/id,<cible>"`.
                 draw.io ne lit ce lien que porte par un <object> enveloppant le <mxCell>.
    `page_ids` : ids de pages valides (on n'emet un lien que vers une page existante).
    """
    import build_html as B
    model = model or {}
    links = links or {}
    page_ids = page_ids if page_ids is not None else set()
    pal = dict(B.DEFAULT_PALETTE)
    pal.update(model.get("palette") or {})
    zones = model.get("zones") or []
    zone_by_id = {z["id"]: z for z in zones if "id" in z}
    ent_by_id = {e["id"]: e for e in (model.get("entities") or []) if "id" in e}
    # schema ancien (actors/tools/...) : entites minimales depuis `ent`
    for i, (label, sub) in ent.items():
        ent_by_id.setdefault(i, {"id": i, "label": label, "sub": sub})
    ids = [i for i in node_ids if i in ent_by_id]
    view = next((v for v in (model.get("views") or []) if isinstance(v, dict) and v.get("id") == page_id), {})
    if view.get("layout"):
        nodes, zone_rects = B._layout_explicit(ids, ent_by_id, zones, view["layout"])
    else:
        nodes, zone_rects = B._layout_auto(ids, ent_by_id, zones)
    zrect = {zid: (x, y, w, h, lab) for (x, y, w, h, lab, zid) in zone_rects}

    def cell_parent(zid):
        """Plus proche zone (soi-meme ou ancetre) presente dans la vue, sinon None."""
        for z in ([zid] if zid else []) + _zone_ancestors(zid, zone_by_id):
            if z in zrect:
                return z
        return None

    def zcell(z):
        return f"zone-{z}"

    cells = []
    # zones (conteneurs), parents avant enfants
    def zdepth(z):
        return len(_zone_ancestors(z, zone_by_id))
    for zid in sorted(zrect, key=zdepth):
        x, y, w, h, label = zrect[zid]
        par = cell_parent(zone_by_id.get(zid, {}).get("parent"))
        px, py = (zrect[par][0], zrect[par][1]) if par else (0, 0)
        tgt = (zone_by_id.get(zid, {}).get("link"))
        tgt = tgt if (tgt in page_ids and tgt != page_id) else None
        stroke = pal["accent"] if tgt else pal["border"]
        style = (f"rounded=1;arcSize=4;whiteSpace=wrap;html=1;container=1;collapsible=0;recursiveResize=0;"
                 f"dashed=1;dashPattern=5 5;fillColor=none;strokeColor={stroke};strokeWidth={2 if tgt else 1};"
                 f"verticalAlign=top;align=left;spacingLeft=14;spacingTop=4;fontStyle=1;fontSize=12;"
                 f"fontColor={pal['ink2']};")
        geom = (f'<mxGeometry x="{B._num(x - px)}" y="{B._num(y - py)}" width="{B._num(w)}" '
                f'height="{B._num(h)}" as="geometry"/>')
        pid = _esc(zcell(par)) if par else "1"
        if tgt:
            cells.append(f'<object id="{_esc(zcell(zid))}" label="{_esc(label)}" link="data:page/id,{_esc(tgt)}">'
                         f'<mxCell style="{style}" vertex="1" parent="{pid}">{geom}</mxCell></object>')
        else:
            cells.append(f'<mxCell id="{_esc(zcell(zid))}" value="{_esc(label)}" style="{style}" '
                         f'vertex="1" parent="{pid}">{geom}</mxCell>')

    # noeuds (+ logos en enfants du noeud)
    for i in ids:
        x, y, w, h = nodes[i]
        e = ent_by_id[i]
        label, sub = e.get("label", i), e.get("sub") or ""
        par = cell_parent(e.get("zone"))
        px, py = (zrect[par][0], zrect[par][1]) if par else (0, 0)
        uri = _logo_uri(e.get("logo"), model.get("logos"), logo_dirs) if e.get("logo") else None
        val = ("<b>" + _esc(label) + "</b>" + ("<br><font color=\"" + pal["ink2"] + "\" style=\"font-size:10px\">"
               + _esc(sub) + "</font>" if sub else ""))
        tgt = links.get(i)
        tgt = tgt if (tgt in page_ids and tgt != page_id) else None
        style = (f"rounded=1;arcSize=18;whiteSpace=wrap;html=1;fillColor={pal['surface']};"
                 f"strokeColor={pal['accent'] if tgt else pal['border']};strokeWidth={2 if tgt else 1};"
                 f"fontColor={pal['ink']};fontSize=12;"
                 + ("spacingLeft=38;" if uri else ""))
        geom = (f'<mxGeometry x="{B._num(x - px)}" y="{B._num(y - py)}" width="{B._num(w)}" '
                f'height="{B._num(h)}" as="geometry"/>')
        pid = _esc(zcell(par)) if par else "1"
        if tgt:
            cells.append(f'<object id="{_esc(i)}" label="{_esc(val)}" link="data:page/id,{_esc(tgt)}">'
                         f'<mxCell style="{style}" vertex="1" parent="{pid}">{geom}</mxCell></object>')
        else:
            cells.append(f'<mxCell id="{_esc(i)}" value="{_esc(val)}" style="{style}" '
                         f'vertex="1" parent="{pid}">{geom}</mxCell>')
        if uri:
            lw, p = 26, 3
            ly = h / 2 - lw / 2
            cells.append(f'<mxCell id="{_esc(i)}--plate" value="" style="rounded=1;arcSize=12;html=1;'
                         f'fillColor=#FFFFFF;strokeColor=none;" vertex="1" parent="{_esc(i)}">'
                         f'<mxGeometry x="{12 - p}" y="{B._num(ly - p)}" width="{lw + 2 * p}" height="{lw + 2 * p}" '
                         f'as="geometry"/></mxCell>')
            cells.append(f'<mxCell id="{_esc(i)}--logo" value="" style="shape=image;aspect=fixed;'
                         f'imageAspect=1;image={uri};" vertex="1" parent="{_esc(i)}">'
                         f'<mxGeometry x="12" y="{B._num(ly)}" width="{lw}" height="{lw}" as="geometry"/></mxCell>')

    sset, e_n = set(ids), 0
    for f in flows:
        a, b = f.get("from"), f.get("to")
        if a in sset and b in sset and a != b:
            e_n += 1
            kind = f.get("kind", "")
            start = "classic" if kind in B.PULL_KINDS else "none"  # double fleche = pull/read
            ex, ey, nx, ny = _edge_anchors(nodes[a], nodes[b])
            style = (f"edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=classic;startArrow={start};"
                     f"strokeColor={pal['accent']};strokeWidth=1.6;fontColor={pal['ink2']};fontSize=10;"
                     f"labelBackgroundColor={pal['bg']};exitX={ex};exitY={ey};entryX={nx};entryY={ny};")
            cells.append(
                f'<mxCell id="e{_esc(page_id or name)}_{e_n}" value="{_esc(f.get("label",""))}" style="{style}" '
                f'edge="1" parent="1" source="{_esc(a)}" target="{_esc(b)}">'
                f'<mxGeometry relative="1" as="geometry"/></mxCell>'
            )
    body = ("<mxCell id=\"0\"/><mxCell id=\"1\" parent=\"0\"/>" + "".join(cells))
    did = f' id="{_esc(page_id)}"' if page_id else ""
    return (f'<diagram{did} name="{_esc(name)}"><mxGraphModel dx="900" dy="600" grid="1" '
            f'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
            f'pageWidth="1169" pageHeight="826" math="0" shadow="0" background="{pal["bg"]}">'
            f'<root>{body}</root></mxGraphModel></diagram>')


def build_xml(m, mission_logos=None):
    """model dict -> XML .drawio (mxfile multi-pages : une page par vue). Reutilisable (build_html)."""
    ent, flows, views = _entities(m), m.get("flows", []), m.get("views", [])
    links = _links(m)
    dirs = [d for d in (mission_logos, SHARED_LOGOS) if d]
    pages, missing = [], []
    new_style = bool(views) and isinstance(views[0], dict)
    if new_style:
        page_ids = {v.get("id") for v in views if v.get("members")}
        for v in views:
            vid, name, vmembers = v.get("id"), (v.get("label") or v.get("id")), v.get("members")
            if vmembers:
                pages.append(_page(name, vmembers, ent, flows, page_id=vid, links=links, page_ids=page_ids,
                                    model=m, logo_dirs=dirs))
            else:
                missing.append(vid)
        note = f"{len(pages)} vue(s) (views[].members)"
    else:
        members = m.get("view_members", {})
        pages.append(_page("Overview (tous les flux)", list(ent.keys()), ent, flows, page_id="overview",
                            model=m, logo_dirs=dirs))
        for v in views:
            (pages.append(_page(v, members[v], ent, flows, page_id=v, model=m, logo_dirs=dirs)) if v in members else missing.append(v))
        note = (f"1 overview ({len(ent)} noeuds, {len(flows)} flux)"
                + (f" + {len(members)} vue(s)" if members else ""))
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="pm-framework">' + "".join(pages) + "</mxfile>"
    return xml, note, missing


def write_per_screen(m, out_dir, mission_logos=None):
    """Un .drawio PAR ECRAN (une vue = un fichier <id>.drawio) dans out_dir. Regenere a chaque appel.
    Cree le dossier si besoin ; n'ecrit QUE des .drawio. Retourne la liste des fichiers ecrits."""
    ent, flows, views = _entities(m), m.get("flows", []), m.get("views", [])
    links = _links(m)
    dirs = [d for d in (mission_logos, SHARED_LOGOS) if d]
    page_ids = {v.get("id") for v in views if v.get("members")}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for v in views:
        vid, name, members = v.get("id"), (v.get("label") or v.get("id")), v.get("members")
        if not members:
            continue
        page = _page(name, members, ent, flows, page_id=vid, links=links, page_ids=page_ids,
                     model=m, logo_dirs=dirs)
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<mxfile host="pm-framework">' + page + "</mxfile>"
        f = out / f"{vid}.drawio"
        f.write_text(xml, encoding="utf-8")
        written.append(str(f))
    return written


def main():
    mission = sys.argv[1] if len(sys.argv) > 1 else "sinbad"
    out = None
    if "-o" in sys.argv:
        out = sys.argv[sys.argv.index("-o") + 1]
    # PMF_ARCH_MODEL : rendu depuis un modèle direct, SANS exiger profiles/<mission>/archi.yml
    env_model = os.environ.get("PMF_ARCH_MODEL")
    if env_model:
        model_path = env_model
    else:
        cfg = prof._load_yaml(prof.mission_dir(mission) / "archi.yml")
        model_path = cfg["model_json"]
    m = json.load(open(model_path, encoding="utf-8"))
    xml, overview_note, missing = build_xml(m, prof.mission_dir(mission) / "logos")
    out = out or str(ROOT.parent / "scratchpad" / f"architecture_{mission}.drawio")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(xml, encoding="utf-8")

    print(f"Écrit : {out}")
    print(f"Pages : {overview_note}")
    if missing:
        print(f"Vues sans contenu (ajouter `members` à la vue, ou `view_members`) : "
              f"{', '.join(str(x) for x in missing)}")


if __name__ == "__main__":
    main()
