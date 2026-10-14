#!/usr/bin/env python3
"""build_html - modele (model.json) -> schema d'architecture interactif (un seul HTML autonome).

Moteur generique model-first : on ne dessine plus de HTML a la main, on declare le modele
(voir SCHEMA.md) et ce module genere le HTML navigable, valide par le harness `validate.py`
(7 invariants). Aucune dependance externe (stdlib only).

    python3 build_html.py <model.json> -o <sortie.html>

Par vue (`views[]`) :
  - noeuds = les `entities` dont l'id est dans `members` ; position par `layout` si fourni,
    sinon auto-placement (regroupement par zone, zones imbricables via `parent`, puis grille) ;
  - cadres de zones (rectangles de regroupement, titres) ;
  - flux entre membres en fleches rectilignes (segments H/V) ; `kind` pull/read = double fleche ;
    marqueurs de fleche a id unique par vue ;
  - logos via window.LOGOS (plate blanche) ; entite sans logo = boite titree (label + sub) ;
  - palette -> variables CSS sur :root ;
  - navigation : objet JS `names`, elements `data-go`, fonctions go()/back(), fil d'Ariane ;
  - viewBox sur chaque SVG ; une seule vue visible a la fois.
"""
import json
import math
import sys
from pathlib import Path

# --------------------------------------------------------------- geometrie
NODE_W = 164
NODE_H = 62
GAP = 36
ZPAD = 26          # marge interieure d'une zone
ZTITLE = 32        # hauteur du bandeau de titre d'une zone
MARGIN = 34        # marge autour du diagramme

PULL_KINDS = {"pull", "read"}   # convention KNOWLEDGE : double fleche (le composant TIRE la donnee)

DEFAULT_PALETTE = {
    "bg": "#0f141b", "surface": "#19212c", "ink": "#e8ebf0",
    "ink2": "#a2abba", "accent": "#6fa2d6", "border": "#2a303b",
}


# ------------------------------------------------------------------- utils
def esc(t):
    return (str(t) if t is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _num(v):
    r = round(float(v), 1)
    return str(int(r)) if r == int(r) else str(r)


# ------------------------------------------------------- arbre des zones/noeuds
def _zone_ancestors(zid, zone_by_id):
    """Chaine d'ancetres (du plus proche au plus lointain) d'une zone."""
    out, seen = [], set()
    cur = zone_by_id.get(zid, {}).get("parent")
    while cur and cur in zone_by_id and cur not in seen:
        seen.add(cur)
        out.append(cur)
        cur = zone_by_id[cur].get("parent")
    return out


def _build_tree(member_ids, ent_by_id, zones):
    """Construit la foret d'items (zones imbriquees + entites) pour une vue.

    Retourne la liste des items racines. Un item entite = {type:'entity', id, label, sub, logo}.
    Un item zone = {type:'zone', id, label, children:[...]}.
    """
    zone_by_id = {z["id"]: z for z in zones}
    members = [m for m in member_ids if m in ent_by_id]

    # zones pertinentes : celles d'un membre + tous leurs ancetres
    relevant = set()
    for mid in members:
        z = ent_by_id[mid].get("zone")
        if z and z in zone_by_id:
            relevant.add(z)
            relevant.update(_zone_ancestors(z, zone_by_id))

    def entity_item(eid):
        e = ent_by_id[eid]
        return {"type": "entity", "id": eid, "label": e.get("label", eid),
                "sub": e.get("sub"), "logo": e.get("logo")}

    def zone_item(zid):
        z = zone_by_id[zid]
        children = []
        # sous-zones pertinentes (ordre du modele)
        for sz in zones:
            if sz["id"] in relevant and sz.get("parent") == zid:
                children.append(zone_item(sz["id"]))
        # entites membres directement dans cette zone (ordre du modele)
        for mid in members:
            if ent_by_id[mid].get("zone") == zid:
                children.append(entity_item(mid))
        return {"type": "zone", "id": zid, "label": z.get("label", zid), "children": children}

    roots = []
    # zones racines (sans parent pertinent)
    for z in zones:
        if z["id"] in relevant:
            p = z.get("parent")
            if not p or p not in relevant:
                roots.append(zone_item(z["id"]))
    # entites hors zone (ou zone non pertinente)
    for mid in members:
        z = ent_by_id[mid].get("zone")
        if not z or z not in relevant:
            roots.append(entity_item(mid))
    return roots


# ----------------------------------------------------------- placement (grille)
def _grid_dims(n):
    cols = max(1, int(math.ceil(math.sqrt(n))))
    rows = int(math.ceil(n / cols))
    return cols, rows


def _measure(items):
    """Mesure chaque item (recursif pour les zones) et pose leurs (x,y) locaux en grille.
    Retourne (largeur, hauteur) du bloc occupe par `items`."""
    if not items:
        return 0.0, 0.0
    for it in items:
        if it["type"] == "zone":
            iw, ih = _measure(it["children"])
            it["inner_w"], it["inner_h"] = iw, ih
            it["w"] = iw + 2 * ZPAD
            it["h"] = ih + ZTITLE + ZPAD
        else:
            it["w"], it["h"] = NODE_W, NODE_H

    n = len(items)
    cols, rows = _grid_dims(n)
    col_w = [0.0] * cols
    row_h = [0.0] * rows
    for k, it in enumerate(items):
        r, c = divmod(k, cols)
        col_w[c] = max(col_w[c], it["w"])
        row_h[r] = max(row_h[r], it["h"])
    x_col, acc = [0.0] * cols, 0.0
    for c in range(cols):
        x_col[c] = acc
        acc += col_w[c] + GAP
    y_row, acc = [0.0] * rows, 0.0
    for r in range(rows):
        y_row[r] = acc
        acc += row_h[r] + GAP
    for k, it in enumerate(items):
        r, c = divmod(k, cols)
        it["x"] = x_col[c] + (col_w[c] - it["w"]) / 2
        it["y"] = y_row[r] + (row_h[r] - it["h"]) / 2
    total_w = sum(col_w) + (cols - 1) * GAP
    total_h = sum(row_h) + (rows - 1) * GAP
    return total_w, total_h


def _place_abs(items, ox, oy, nodes, zone_rects):
    """Convertit les positions locales en absolu ; remplit nodes{id:(x,y,w,h)} et zone_rects."""
    for it in items:
        ax, ay = ox + it["x"], oy + it["y"]
        if it["type"] == "zone":
            zone_rects.append((ax, ay, it["w"], it["h"], it["label"], it["id"]))
            _place_abs(it["children"], ax + ZPAD, ay + ZTITLE, nodes, zone_rects)
        else:
            nodes[it["id"]] = (ax, ay, NODE_W, NODE_H)


def _layout_auto(member_ids, ent_by_id, zones):
    roots = _build_tree(member_ids, ent_by_id, zones)
    _measure(roots)
    nodes, zone_rects = {}, []
    _place_abs(roots, MARGIN, MARGIN, nodes, zone_rects)
    return nodes, zone_rects


def _layout_explicit(member_ids, ent_by_id, zones, layout):
    """Positions explicites (model `layout`). Les membres sans coordonnees sont empiles."""
    zone_by_id = {z["id"]: z for z in zones}
    nodes = {}
    fallback_y = MARGIN
    max_x = 0.0
    for mid in member_ids:
        if mid not in ent_by_id:
            continue
        if layout and mid in layout and isinstance(layout[mid], (list, tuple)) and len(layout[mid]) == 2:
            x, y = float(layout[mid][0]) + MARGIN, float(layout[mid][1]) + MARGIN
        else:
            x, y = MARGIN, fallback_y
            fallback_y += NODE_H + GAP
        nodes[mid] = (x, y, NODE_W, NODE_H)
        max_x = max(max_x, x)

    # cadres de zones = bbox des membres de la zone (+ de ses sous-zones), marge selon profondeur
    def depth(zid):
        d, cur, seen = 0, zone_by_id.get(zid, {}).get("parent"), set()
        while cur and cur in zone_by_id and cur not in seen:
            seen.add(cur)
            d += 1
            cur = zone_by_id[cur].get("parent")
        return d

    def in_zone(eid, zid):
        cur, seen = ent_by_id[eid].get("zone"), set()
        while cur and cur not in seen:
            if cur == zid:
                return True
            seen.add(cur)
            cur = zone_by_id.get(cur, {}).get("parent")
        return False

    zone_rects = []
    depths = {z["id"]: depth(z["id"]) for z in zones}
    max_depth = max(depths.values()) if depths else 0
    for z in zones:
        zid = z["id"]
        pts = [nodes[e] for e in nodes if in_zone(e, zid)]
        if not pts:
            continue
        pad = ZPAD + (max_depth - depths[zid]) * (ZPAD // 2 + 6)
        x0 = min(p[0] for p in pts) - pad
        y0 = min(p[1] for p in pts) - pad - ZTITLE
        x1 = max(p[0] + p[2] for p in pts) + pad
        y1 = max(p[1] + p[3] for p in pts) + pad
        zone_rects.append((x0, y0, x1 - x0, y1 - y0, z.get("label", zid), zid))
    return nodes, zone_rects


# ------------------------------------------------------------------- rendu SVG
def _node_svg(x, y, label, sub, logo_key, logos, link=None):
    """Noeud. Si `link` (id de vue cible) : cliquable (data-go) + liseré accent + chevron."""
    cls = "node linked" if link else "node"
    s = [f'<rect class="{cls}" x="{_num(x)}" y="{_num(y)}" width="{_num(NODE_W)}" '
         f'height="{_num(NODE_H)}" rx="11"/>']
    text_cx = x + NODE_W / 2
    if logo_key and logo_key in logos:
        lw, lh = 26, 26
        lx, ly = x + 12, y + NODE_H / 2 - lh / 2
        p = 3
        s.append(f'<rect x="{_num(lx - p)}" y="{_num(ly - p)}" width="{_num(lw + 2 * p)}" '
                 f'height="{_num(lh + 2 * p)}" rx="4" fill="#ffffff"/>')
        s.append(f'<image data-logo="{esc(logo_key)}" x="{_num(lx)}" y="{_num(ly)}" '
                 f'width="{_num(lw)}" height="{_num(lh)}" preserveAspectRatio="xMidYMid meet"/>')
        text_cx = x + 12 + lw + (NODE_W - (12 + lw)) / 2
    if sub:
        s.append(f'<text class="nlabel" x="{_num(text_cx)}" y="{_num(y + NODE_H / 2 - 2)}" '
                 f'text-anchor="middle">{esc(label)}</text>')
        s.append(f'<text class="nsub" x="{_num(text_cx)}" y="{_num(y + NODE_H / 2 + 15)}" '
                 f'text-anchor="middle">{esc(sub)}</text>')
    else:
        s.append(f'<text class="nlabel" x="{_num(text_cx)}" y="{_num(y + NODE_H / 2 + 5)}" '
                 f'text-anchor="middle">{esc(label)}</text>')
    if link:
        # chevron discret (coin haut-droit) = signe « on peut y aller »
        s.append(f'<text class="linkcue" x="{_num(x + NODE_W - 14)}" y="{_num(y + 19)}" '
                 f'text-anchor="middle">&#8250;</text>')
        return (f'<g class="nodelink" data-go="{esc(link)}" role="button" tabindex="0" '
                f'aria-label="{esc(label)} - voir {esc(link)}">{"".join(s)}</g>')
    return "".join(s)


def _zone_svg(x, y, w, h, label, link=None):
    """Cadre de zone. Si `link` : cliquable (data-go) + liseré accent + chevron au titre."""
    cls = "zone linked" if link else "zone"
    s = (f'<rect class="{cls}" x="{_num(x)}" y="{_num(y)}" width="{_num(w)}" '
         f'height="{_num(h)}" rx="14"/>'
         f'<text class="ztitle" x="{_num(x + 16)}" y="{_num(y + 21)}" '
         f'text-anchor="start">{esc(label)}</text>')
    if link:
        s += (f'<text class="linkcue" x="{_num(x + w - 16)}" y="{_num(y + 21)}" '
              f'text-anchor="middle">&#8250;</text>')
        return (f'<g class="zonelink" data-go="{esc(link)}" role="button" tabindex="0" '
                f'aria-label="{esc(label)} - voir {esc(link)}">{s}</g>')
    return s


def _orth(ra, rb):
    """Connecteur orthogonal (segments H/V uniquement) entre deux rects.
    Retourne (d, label_x, label_y)."""
    ax, ay, aw, ah = ra
    bx, by, bw, bh = rb
    acx, acy = ax + aw / 2, ay + ah / 2
    bcx, bcy = bx + bw / 2, by + bh / 2
    dx, dy = bcx - acx, bcy - acy
    if abs(dx) >= abs(dy):                       # dominante horizontale
        sx = ax + aw if dx >= 0 else ax
        ex = bx if dx >= 0 else bx + bw
        mx = (sx + ex) / 2
        pts = [(sx, acy), (mx, acy), (mx, bcy), (ex, bcy)]
        lx, ly = mx, (acy + bcy) / 2 - 8
    else:                                        # dominante verticale
        sy = ay + ah if dy >= 0 else ay
        ey = by if dy >= 0 else by + bh
        my = (sy + ey) / 2
        pts = [(acx, sy), (acx, my), (bcx, my), (bcx, ey)]
        lx, ly = (acx + bcx) / 2, my - 8
    d = "M" + " L".join(f"{_num(px)} {_num(py)}" for px, py in pts)
    return d, lx, ly


def _flow_svg(ra, rb, label, double, mid):
    d, lx, ly = _orth(ra, rb)
    start = f' marker-start="url(#{mid})"' if double else ""
    s = f'<path class="flow" d="{d}" marker-end="url(#{mid})"{start}/>'
    if label:
        s += (f'<text class="flabel" x="{_num(lx)}" y="{_num(ly)}" '
              f'text-anchor="middle">{esc(label)}</text>')
    return s


def _marker(mid):
    return (f'<defs><marker id="{mid}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" '
            'markerHeight="8" orient="auto-start-reverse"><path d="M2 2 L8 5 L2 8" fill="none" '
            'stroke="context-stroke" stroke-width="1.8" stroke-linecap="round" '
            'stroke-linejoin="round"/></marker></defs>')


def _resolve_link(link, view_ids, vid):
    """Garde-fou : un lien n'est actif que s'il pointe vers une AUTRE vue existante."""
    return link if (link and link in view_ids and link != vid) else None


def _render_view(view, ent_by_id, zones, flows, logos, view_ids):
    vid = view["id"]
    members = [m for m in (view.get("members") or []) if m in ent_by_id]
    layout = view.get("layout")
    if layout:
        nodes, zone_rects = _layout_explicit(members, ent_by_id, zones, layout)
    else:
        nodes, zone_rects = _layout_auto(members, ent_by_id, zones)
    zone_link = {z["id"]: z.get("link") for z in zones}

    mid = f"arw-{vid}"
    body = [_marker(mid)]
    # zones d'abord (fond), puis flux, puis noeuds (au-dessus)
    for (x, y, w, h, label, zid) in zone_rects:
        link = _resolve_link(zone_link.get(zid), view_ids, vid)
        body.append(_zone_svg(x, y, w, h, label, link))
    mset = set(nodes)
    for f in flows:
        a, b = f.get("from"), f.get("to")
        if a in mset and b in mset and a != b:
            double = f.get("kind") in PULL_KINDS
            body.append(_flow_svg(nodes[a], nodes[b], f.get("label", ""), double, mid))
    for eid, (x, y, w, h) in nodes.items():
        e = ent_by_id[eid]
        link = _resolve_link(e.get("link"), view_ids, vid)
        body.append(_node_svg(x, y, e.get("label", eid), e.get("sub"), e.get("logo"), logos, link))

    # viewBox : etendue des noeuds et zones + marge
    xs = [MARGIN]
    ys = [MARGIN]
    for (x, y, w, h) in nodes.values():
        xs.append(x + w)
        ys.append(y + h)
    for (x, y, w, h, _l, _zid) in zone_rects:
        xs.append(x + w)
        ys.append(y + h)
        xs.append(x)
        ys.append(y)
    vb_w = max(xs) + MARGIN
    vb_h = max(ys) + MARGIN
    svg = (f'<svg viewBox="0 0 {_num(vb_w)} {_num(vb_h)}" role="img" '
           f'aria-label="{esc(view.get("label", vid))}" preserveAspectRatio="xMidYMid meet">'
           f'{"".join(body)}</svg>')
    return svg


# ------------------------------------------------------------------- page HTML
_CSS = """
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);margin:0;
font-family:"IBM Plex Sans",system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
padding:clamp(14px,3vw,34px)}
.bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
#home{font:600 13px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent);
background:var(--surface);border:1px solid var(--border);border-radius:9px;padding:6px 11px;cursor:pointer}
#trail{color:var(--ink2);font:12px ui-monospace,SFMono-Regular,Menlo,monospace}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.navbtn{font:600 12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ink2);
background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:6px 11px;cursor:pointer}
.navbtn.active{color:var(--accent);border-color:var(--accent)}
.view .back{font:600 12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent);
background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:5px 10px;cursor:pointer;margin-bottom:10px}
svg{width:100%;height:auto;max-width:1200px;display:block}
.node{fill:var(--surface);stroke:var(--border);stroke-width:1.4}
.zone{fill:none;stroke:var(--border);stroke-width:1.2;stroke-dasharray:5 5;opacity:.95}
.ztitle{fill:var(--ink2);font-weight:700;font-size:13px}
.nlabel{fill:var(--ink);font-weight:600;font-size:13px}
.nsub{fill:var(--ink2);font-size:11px}
.flow{fill:none;stroke:var(--accent);stroke-width:1.6}
.flabel{fill:var(--ink2);font-size:11px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.node.linked{stroke:var(--accent);stroke-width:1.9}
.zone.linked{stroke:var(--accent);opacity:1}
.nodelink,.zonelink{cursor:pointer}
.nodelink:hover .node.linked,.zonelink:hover .zone.linked{stroke-width:2.4}
.nodelink:focus,.zonelink:focus{outline:none}
.linkcue{fill:var(--accent);font-weight:700;font-size:15px;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
[hidden]{display:none!important}
"""

_JS = """
(function(){
var cur="__OV__",hist=[];
var trail=document.getElementById("trail");
function render(id){
  var vs=document.querySelectorAll(".view");
  for(var i=0;i<vs.length;i++){vs[i].hidden=(vs[i].id!=="v-"+id);}
  if(trail){trail.textContent=(id==="__OV__")?"":("\\u203a "+(names[id]||id));}
  cur=id;try{scrollTo(0,0);}catch(e){}
  var gs=document.querySelectorAll("[data-go]");
  for(var j=0;j<gs.length;j++){
    var on=(gs[j].getAttribute("data-go")===id);
    if(gs[j].classList){gs[j].classList.toggle("active",on);}
  }
}
function go(id){if(id!==cur){hist.push(cur);}render(id);}
function back(){render(hist.length?hist.pop():"__OV__");}
window._go=go;window._back=back;
var gs=document.querySelectorAll("[data-go]");
for(var i=0;i<gs.length;i++){(function(b){b.addEventListener("click",function(){go(b.getAttribute("data-go"));});})(gs[i]);}
var bk=document.querySelectorAll("[data-back]");
for(var k=0;k<bk.length;k++){bk[k].addEventListener("click",back);}
var home=document.getElementById("home");
if(home){home.addEventListener("click",function(){hist=[];render("__OV__");});}
try{var L=window.LOGOS||{};var im=document.querySelectorAll("image[data-logo]");
for(var m=0;m<im.length;m++){var kk=im[m].getAttribute("data-logo");
if(L[kk]){im[m].setAttributeNS("http://www.w3.org/1999/xlink","href",L[kk]);im[m].setAttribute("href",L[kk]);}}}catch(e){}
render("__OV__");
})();
"""


def build_html(model):
    """Genere la page HTML complete (chaine) depuis un dict modele conforme a SCHEMA.md."""
    meta = model.get("meta", {})
    title = meta.get("project") or "Architecture"
    palette = dict(DEFAULT_PALETTE)
    palette.update(model.get("palette") or {})
    logos = model.get("logos") or {}
    zones = model.get("zones") or []
    entities = model.get("entities") or []
    flows = model.get("flows") or []
    views = model.get("views") or []
    ent_by_id = {e["id"]: e for e in entities if "id" in e}

    if not views:
        raise ValueError("Le modele ne declare aucune vue (`views`).")
    if not all(isinstance(v, dict) and "id" in v for v in views):
        raise ValueError(
            "Schema non supporte : `views` doit etre une liste d'objets {id, label, members} "
            "(nouveau schema model-first, voir SCHEMA.md). L'ancien schema (views = liste d'ids) "
            "n'est pas rendu par build_html."
        )
    overview = views[0]["id"]

    names = {v["id"]: v.get("label", v["id"]) for v in views}

    # :root de base : un seul bloc plat, tous les tokens de la palette (invariant Tokens)
    root_tokens = "".join(f"--{k}:{v};" for k, v in palette.items())
    root_css = f":root{{{root_tokens}color-scheme:{'dark' if meta.get('theme') == 'dark' else 'light'};}}"

    nav = "".join(
        f'<button class="navbtn" data-go="{esc(v["id"])}">{esc(v.get("label", v["id"]))}</button>'
        for v in views
    )

    view_ids = {v["id"] for v in views}
    sections = []
    for v in views:
        vid = v["id"]
        svg = _render_view(v, ent_by_id, zones, flows, logos, view_ids)
        back = "" if vid == overview else '<button class="back" data-back>&lsaquo; Retour</button>'
        hidden = "" if vid == overview else " hidden"
        sections.append(f'<section class="view" id="v-{esc(vid)}"{hidden}>{back}{svg}</section>')

    js = _JS.replace("__OV__", overview)

    html = (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f'<title>{esc(title)}</title>'
        f'<style>{root_css}{_CSS}</style></head><body>'
        f'<div class="bar"><span id="home">&#8962; {esc(title)}</span><span id="trail"></span></div>'
        f'<nav class="nav">{nav}</nav>'
        f'<div class="stage">{"".join(sections)}</div>'
        f'<script>window.LOGOS = {json.dumps(logos, ensure_ascii=False)};</script>'
        f'<script>var names = {json.dumps(names, ensure_ascii=False)};{js}</script>'
        '</body></html>'
    )
    return html


def build_html_file(model_path, out_path):
    model = json.load(open(model_path, encoding="utf-8"))
    html = build_html(model)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(html, encoding="utf-8")
    return out_path


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python3 build_html.py <model.json> -o <sortie.html>")
        sys.exit(2)
    model_path = argv[0]
    out = None
    if "-o" in argv:
        out = argv[argv.index("-o") + 1]
    if not out:
        out = str(Path(model_path).with_suffix(".html"))
    build_html_file(model_path, out)
    print(f"Ecrit : {out}")


if __name__ == "__main__":
    main()
