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
  - viewBox sur chaque SVG ; une seule vue visible a la fois ;
  - element cliquable (`link`) = loupe (comme le schema par defaut) ;
  - `color` (token de palette ou #hex) sur entite / zone / couche : bordure + titre colores ;
    zone `style: "team"` = encart d'equipe (tirets colores, titre gras) ;
  - flux `main: true` = anime (chemin principal de la donnee) ; `kind: auth` = pointilles roses ;
  - couches (`layers`) : la vue d'ensemble est abstraite selon les modes (voir abstraction.py).
"""
import json
import math
import sys
import base64
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
# Couleurs de ROLE (reprises du schema SINBAD par defaut) : toujours posees sur :root, surchargeables
# par la palette du modele. Une entite/zone/couche les reference par `color`.
ROLE_COLORS = {
    "core": "#a66bff",      # plateforme / coeur (violet)
    "service": "#44c07a",   # services applicatifs, namespace (vert)
    "auth": "#f07ab8",      # identite / OIDC (rose)
    "storage": "#e2571e",   # stockage objet S3 (orange)
    "db": "#2e73b8",        # base de donnees (bleu)
    "cluster": "#326ce5",   # Kubernetes (bleu k8s)
    "risk": "#ff5757",      # securite / SOC (rouge)
    "ops": "#e0b35a",       # exploitation (ambre)
    "partner": "#3fcbe6",   # partenaire (cyan)
    "partner2": "#8fc457",  # partenaire 2 (vert clair)
    "ext": "#9aa6b4",       # acteur externe (gris)
}


# ------------------------------------------------------------------- utils
def esc(t):
    return (str(t) if t is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_PAL = {}


def _col(c):
    """`color` d'un element -> valeur CSS : token de palette (var(--x)) ou #hex ; sinon None."""
    if not c:
        return None
    c = str(c)
    if c in _PAL:
        return f"var(--{c})"
    if c.startswith("#") and len(c) in (4, 7, 9):
        return c
    return None


def _zoom(cx, cy):
    """Loupe (coin haut-droit d'un bloc cliquable), comme le schema par defaut."""
    return (f'<circle class="zoom" cx="{_num(cx)}" cy="{_num(cy)}" r="6"/>'
            f'<path class="zoom" d="M{_num(cx + 4)} {_num(cy + 4)} l5 5"/>')


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
    # zones presentes DANS CETTE VUE, et pour chacune le nombre de niveaux de sous-zones presentes
    # sous elle : la marge d'un cadre depend de ce qu'il contient ici, pas de tout le modele.
    present = {z["id"] for z in zones if any(in_zone(e, z["id"]) for e in nodes)}

    def height(zid, seen=()):
        kids = [z["id"] for z in zones if z.get("parent") == zid and z["id"] in present and z["id"] not in seen]
        return 0 if not kids else 1 + max(height(k, seen + (zid,)) for k in kids)

    for z in zones:
        zid = z["id"]
        if zid not in present:
            continue
        pts = [nodes[e] for e in nodes if in_zone(e, zid)]
        hz = height(zid)
        pad = ZPAD + hz * (ZPAD // 2 + 6)
        x0 = min(p[0] for p in pts) - pad
        # un bandeau de titre par niveau d'imbrication : le titre d'une zone ne passe pas sous sa sous-zone
        y0 = min(p[1] for p in pts) - pad - ZTITLE * (1 + hz)
        x1 = max(p[0] + p[2] for p in pts) + pad
        y1 = max(p[1] + p[3] for p in pts) + pad
        zone_rects.append((x0, y0, x1 - x0, y1 - y0, z.get("label", zid), zid))
    return nodes, zone_rects


# ------------------------------------------------------------------- rendu SVG
def _wrap(label, width_px, px_per_char=7.2, max_lines=2):
    """Coupe un libelle en <= max_lines lignes tenant dans width_px (estimation 13px gras).
    Retourne (lignes, tronque?)."""
    cap = max(4, int(width_px / px_per_char))
    words, lines, cur = str(label).split(), [], ""
    for w in words:
        while len(w) > cap:                           # mot plus long qu'une ligne : coupe dure
            if cur:
                lines.append(cur); cur = ""
            lines.append(w[:cap]); w = w[cap:]
        cand = (cur + " " + w).strip()
        if len(cand) <= cap:
            cur = cand
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    cut = len(lines) > max_lines
    if cut:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(1, cap - 1)].rstrip() + "\u2026"
    return lines, cut


def _node_svg(x, y, label, sub, logo_key, logos, link=None, color=None):
    """Noeud. `color` : bordure + titre colores. Si `link` (id de vue cible) : cliquable (data-go) + loupe.
    Le libelle tient dans le bloc (2 lignes max, ellipse sinon, libelle complet en infobulle) et ne passe
    jamais sous le logo."""
    cls = "node linked" if link else "node"
    c = _col(color)
    st = f' style="stroke:{c}"' if c else ""
    tc = f' style="fill:{c}"' if c else ""
    s = [f'<rect class="{cls}" x="{_num(x)}" y="{_num(y)}" width="{_num(NODE_W)}" '
         f'height="{_num(NODE_H)}" rx="11"{st}/>']
    left, right = x + 12, x + NODE_W - (22 if link else 12)
    if logo_key and logo_key in logos:
        lw, lh = 26, 26
        lx, ly = x + 12, y + NODE_H / 2 - lh / 2
        p = 3
        s.append(f'<rect x="{_num(lx - p)}" y="{_num(ly - p)}" width="{_num(lw + 2 * p)}" '
                 f'height="{_num(lh + 2 * p)}" rx="4" fill="#ffffff"/>')
        s.append(f'<image data-logo="{esc(logo_key)}" x="{_num(lx)}" y="{_num(ly)}" '
                 f'width="{_num(lw)}" height="{_num(lh)}" preserveAspectRatio="xMidYMid meet"/>')
        left = lx + lw + p + 8
    text_cx = (left + right) / 2
    lines, cut = _wrap(label, right - left, max_lines=2 if sub else 3)
    n = len(lines) + (1 if sub else 0)
    lh_ = 15
    y0 = y + NODE_H / 2 - (n - 1) * lh_ / 2 + 4
    for i, ln in enumerate(lines):
        s.append(f'<text class="nlabel" x="{_num(text_cx)}" y="{_num(y0 + i * lh_)}" '
                 f'text-anchor="middle"{tc}>{esc(ln)}</text>')
    if sub:
        sl, _ = _wrap(sub, right - left, px_per_char=6.2, max_lines=1)
        s.append(f'<text class="nsub" x="{_num(text_cx)}" y="{_num(y0 + len(lines) * lh_)}" '
                 f'text-anchor="middle">{esc(sl[0])}</text>')
    if cut or (sub and len(str(sub)) > int((right - left) / 6.2)):
        s.insert(0, f'<title>{esc(label)}{(" - " + esc(sub)) if sub else ""}</title>')
    if link:
        # loupe (coin haut-droit) = signe « on peut y aller », comme le schema par defaut
        s.append(_zoom(x + NODE_W - 15, y + 14))
        return (f'<g class="nodelink" data-go="{esc(link)}" role="button" tabindex="0" '
                f'aria-label="{esc(label)} - voir {esc(link)}">{"".join(s)}</g>')
    if cut:
        return f'<g>{"".join(s)}</g>'
    return "".join(s)


def _zone_svg(x, y, w, h, label, link=None, color=None, style=None, logo=None, logos=None):
    """Cadre de zone. `color` : tirets + titre colores ; `style: team` = encart d'equipe.
    `logo` : petit logo devant le titre (cle de `logos`). Si `link` : cliquable (data-go) + loupe au titre."""
    cls = "zone linked" if link else "zone"
    if style == "team":
        cls += " team"
    c = _col(color)
    st = f' style="stroke:{c}"' if c else ""
    tc = f' style="fill:{c}"' if c else ""
    s = (f'<rect class="{cls}" x="{_num(x)}" y="{_num(y)}" width="{_num(w)}" '
         f'height="{_num(h)}" rx="14"{st}/>')
    tx = x + 16
    if logo and logos and logo in logos:
        s += (f'<rect x="{_num(x + 12)}" y="{_num(y + 7)}" width="20" height="20" rx="4" fill="#ffffff"/>'
              f'<image data-logo="{esc(logo)}" x="{_num(x + 14)}" y="{_num(y + 9)}" width="16" height="16" '
              f'preserveAspectRatio="xMidYMid meet"/>')
        tx = x + 40
    s += (f'<text class="ztitle" x="{_num(tx)}" y="{_num(y + 21)}" '
          f'text-anchor="start"{tc}>{esc(label)}</text>')
    if link:
        s += _zoom(x + w - 18, y + 15)
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


def _flow_svg(ra, rb, label, double, mid, kind=None, main=False):
    d, lx, ly = _orth(ra, rb)
    start = f' marker-start="url(#{mid})"' if double else ""
    cls = "flow" + (" main" if main else "") + (" auth" if kind == "auth" else "")
    s = f'<path class="{cls}" d="{d}" marker-end="url(#{mid})"{start}/>'
    if label:
        lc = " lauth" if kind == "auth" else (" lmain" if main else "")
        s += (f'<text class="flabel{lc}" x="{_num(lx)}" y="{_num(ly)}" '
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
    zone_by_id = {z["id"]: z for z in zones}

    mid = f"arw-{vid}"
    body = [_marker(mid)]
    # zones d'abord (fond), puis flux, puis noeuds (au-dessus)
    for (x, y, w, h, label, zid) in zone_rects:
        z = zone_by_id.get(zid, {})
        link = _resolve_link(z.get("link"), view_ids, vid)
        body.append(_zone_svg(x, y, w, h, label, link, z.get("color"), z.get("style"), z.get("logo"), logos))
    mset = set(nodes)
    for f in flows:
        if f.get("_only_in") and f["_only_in"] != vid:
            continue                       # flux rebranche sur un bloc de couche : vue d'ensemble seule
        a, b = f.get("from"), f.get("to")
        if a in mset and b in mset and a != b:
            double = f.get("kind") in PULL_KINDS
            body.append(_flow_svg(nodes[a], nodes[b], f.get("label", ""), double, mid,
                                  f.get("kind"), bool(f.get("main"))))
    for eid, (x, y, w, h) in nodes.items():
        e = ent_by_id[eid]
        link = _resolve_link(e.get("link"), view_ids, vid)
        body.append(_node_svg(x, y, e.get("label", eid), e.get("sub"), e.get("logo"), logos, link,
                              e.get("color")))

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
    # origine = coin haut-gauche réel (un cadre de zone peut déborder à gauche/en haut d'un layout explicite)
    x_min = min([MARGIN] + [x for (x, _y, _w, _h) in nodes.values()]
                + [x for (x, _y, _w, _h, _l, _z) in zone_rects]) - MARGIN
    y_min = min([MARGIN] + [y for (_x, y, _w, _h) in nodes.values()]
                + [y for (_x, y, _w, _h, _l, _z) in zone_rects]) - MARGIN
    x_min, y_min = min(0, x_min), min(0, y_min)
    if layout:                                   # couche masquée : on recadre sur ce qui reste
        x_min = min([x for (x, _y, _w, _h) in nodes.values()] + [x for (x, _y, _w, _h, _l, _z) in zone_rects] or [0]) - MARGIN
        y_min = min([y for (_x, y, _w, _h) in nodes.values()] + [y for (_x, y, _w, _h, _l, _z) in zone_rects] or [0]) - MARGIN
    vb_w = max(xs) + MARGIN - x_min
    vb_h = max(ys) + MARGIN - y_min
    svg = (f'<svg viewBox="{_num(x_min)} {_num(y_min)} {_num(vb_w)} {_num(vb_h)}" role="img" '
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
.tool{font:600 12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent);
background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:6px 11px;cursor:pointer;text-decoration:none}
.tool:hover{border-color:var(--accent)}
.spacer{flex:1}
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
.zoom{fill:none;stroke:var(--ink2);stroke-width:1.4}
.nodelink:hover .zoom,.zonelink:hover .zoom{stroke:var(--accent)}
.nodelink,.zonelink{transition:transform .15s ease}
.nodelink:hover{transform:translateY(-2px)}
.zone.team{stroke-width:1.5;stroke-dasharray:6 5;opacity:1}
.zone.team + .ztitle,.team ~ .ztitle{font-weight:800}
.flow.main{stroke-width:2.4;stroke-dasharray:7 7;animation:dash 1s linear infinite}
.flow.auth{stroke:var(--auth);stroke-dasharray:3 4}
.flabel.lmain{fill:var(--accent);font-weight:600}
.flabel.lauth{fill:var(--auth);font-weight:600}
@keyframes dash{to{stroke-dashoffset:-14}}
.view:not([hidden]){animation:vin .35s ease both}
@keyframes vin{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.flow.main,.view:not([hidden]){animation:none}.nodelink:hover{transform:none}}
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
var cp=document.getElementById("copy-drawio");
if(cp){cp.addEventListener("click",function(){
  try{var xml=decodeURIComponent(escape(window.atob(window.__DRAWIO_B64||"")));
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(xml).then(function(){cp.textContent="\\u2713 Copié";
        setTimeout(function(){cp.textContent="\\u2317 Copier .drawio";},1500);},
        function(){cp.textContent="Copie refusée";});
    }else{cp.textContent="Copie indisponible";}
  }catch(e){cp.textContent="Copie indisponible";}
});}
render("__OV__");
})();
"""


def build_html(model, modes=None):
    """Genere la page HTML complete (chaine) depuis un dict modele conforme a SCHEMA.md.
    `modes` : profondeur des couches dans la vue d'ensemble ({couche: detail|abstrait|masque}) ;
    sans couches (`layers`) dans le modele, rien ne change."""
    import abstraction as ABS  # sibling (archi/)
    model = ABS.apply(model, modes)
    meta = model.get("meta", {})
    title = meta.get("project") or "Architecture"
    palette = dict(DEFAULT_PALETTE)
    palette.update(ROLE_COLORS)
    palette.update(model.get("palette") or {})
    _PAL.clear()
    _PAL.update(palette)
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

    # draw.io (une page par vue) embarque : lien de telechargement + copie du XML.
    # NB artefact Claude : le telechargement est bloque par le bac a sable -> le bouton Copier
    # (presse-papier) est le fallback qui marche partout ; sur gh-pages / en local, le lien telecharge.
    drawio_tools, drawio_script = "", ""
    try:
        import export_drawio as XDR  # sibling (archi/)
        xml, _, _ = XDR.build_xml(model)
        b64 = base64.b64encode(xml.encode("utf-8")).decode("ascii")
        href = "data:application/xml;base64," + b64
        drawio_tools = (
            '<span class="spacer"></span>'
            f'<a class="tool" download="{esc(title)}.drawio" href="{href}" '
            'title="Telecharger le .drawio (actif sur gh-pages / en local ; bloque dans l\'artefact Claude)">'
            '&#8681; .drawio</a>'
            '<button class="tool" id="copy-drawio" '
            'title="Copier le XML draw.io (fonctionne partout, artefact compris)">&#9143; Copier .drawio</button>'
        )
        drawio_script = f'<script>window.__DRAWIO_B64 = {json.dumps(b64)};</script>'
    except Exception:
        pass

    html = (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f'<title>{esc(title)}</title>'
        f'<style>{root_css}{_CSS}</style></head><body>'
        f'<div class="bar"><span id="home">&#8962; {esc(title)}</span><span id="trail"></span>{drawio_tools}</div>'
        f'<nav class="nav">{nav}</nav>'
        f'<div class="stage">{"".join(sections)}</div>'
        f'{drawio_script}'
        f'<script>window.LOGOS = {json.dumps(logos, ensure_ascii=False)};</script>'
        f'<script>var names = {json.dumps(names, ensure_ascii=False)};{js}</script>'
        '</body></html>'
    )
    return html


def build_html_file(model_path, out_path, modes=None):
    """Rend le modele. Sans `modes`, lit `abstraction.json` a cote du modele s'il existe."""
    model = json.load(open(model_path, encoding="utf-8"))
    if modes is None:
        import abstraction as ABS  # sibling (archi/)
        _pub, modes = ABS.load(Path(model_path).with_name("abstraction.json"))
    html = build_html(model, modes)
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
