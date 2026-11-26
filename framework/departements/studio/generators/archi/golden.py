#!/usr/bin/env python3
"""golden - rendu d'un modele d'archi au style EXACT du schema de reference (gh-pages).

Meme feuille de style (golden_style.css, copiee telle quelle), meme coquille (menu, theme, fil
d'Ariane, scene), meme vocabulaire SVG : cartes `g.blk` / `rect.bg` cliquables en entier avec loupe,
boites `.box`, flux `.flow` (anime) / `.arr` / `.auth`, libelles `.lbl`, cadres de compte, de cluster
(onglet Kubernetes) et de namespace.

Mise en page de la vue d'ensemble (l'harmonie du schema de reference) :
  - colonne centrale = ce qui vit dans le compte cloud : stockage en tete, puis le cluster et son
    namespace, les blocs empiles pleine largeur dans l'ordre des flux, deux petits blocs cote a cote ;
  - colonne de gauche = les sources (ce qui alimente le centre) ;
  - colonne de droite = exploitation, API et applications externes, alignees sur le bloc qu'elles touchent ;
  - rangee du bas = les acteurs (utilisateurs, systemes) ; leurs fleches montent.
Sous-vues : bouton retour, legende en tete, fleche pointillee « depuis … » qui montre d'ou l'on vient,
chaine de traitement de gauche a droite, sorties en dessous, la suite cliquable en bout de chaine.
Sequences : participants, lignes de vie pointillees, messages numerotes (vues `kind: sequence`).
Import draw.io : uniquement fige dans le modele (`views[].drawio`, via architecture.py import-view, par
prompt) ; un diagramme de sequence importe est rendu en sequence, un schema en boites et zones. Aucune
edition ni import dans le navigateur (decision du 24/11/2026 : le schema se construit par prompt + template).
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSS = (HERE / "golden_style.css").read_text(encoding="utf-8")

ROLE_TOK = {
    "core": "var(--sai)", "service": "var(--grn)", "auth": "var(--kc)", "storage": "var(--s3)",
    "db": "var(--rds)", "cluster": "#326CE5", "risk": "var(--soc)", "ops": "var(--amb)",
    "partner": "var(--air)", "partner2": "var(--ksatc)", "ext": "var(--ext)",
}
TITLE_COLORED = {"service", "auth", "partner", "partner2", "ops", "db", "storage", "risk"}

RX_CLUSTER = re.compile(r"kubernetes|\beks\b|\baks\b|\bgke\b|\bk8s\b|cluster", re.I)
RX_NS = re.compile(r"namespace", re.I)
RX_CLOUD = re.compile(r"infra|aws|azure|gcp|cloud|vpc|compte|account|region|eu-west|datacenter|on-?prem", re.I)
RX_ACTOR = re.compile(r"utilisateur|user|operat|analyst|client|syst[eè]mes? (it|tiers)|it systems?|\bsi\b", re.I)
RX_OPS = re.compile(r"exploitation|supervision|monitoring|observab|\bops\b|ci/?cd|d[ée]ploiement", re.I)
RX_DB = re.compile(r"postgres|\brds\b|database|base de donn|mysql|mongo|\bsql\b", re.I)


# ----------------------------------------------------------------- utilitaires
def esc(t):
    return (str(t if t is not None else "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def n(v):
    v = float(v)
    return str(int(round(v))) if abs(v - round(v)) < 1e-6 else f"{v:.1f}"


def tok(color):
    if not color:
        return None
    c = str(color)
    if c.startswith("#") or c.startswith("var("):
        return c
    return ROLE_TOK.get(c, f"var(--{c})")


def tw(text, size="tm"):
    """Largeur estimee d'un texte (px) selon la classe golden."""
    per = {"t": 8.4, "tm": 7.5, "s": 6.4, "lbl": 6.7}[size]
    return len(str(text or "")) * per


def wrap(text, width, size="tm", max_lines=2):
    words, lines, cur = str(text or "").split(), [], ""
    cap = max(4, int(width / {"t": 8.4, "tm": 7.5, "s": 6.4, "lbl": 6.7}[size]))
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= cap:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: cap - 1].rstrip() + "…"
    return [l if len(l) <= cap else l[: cap - 1] + "…" for l in lines] or [""]


def zoom(cx, cy):
    return (f'<circle class="zoom" cx="{n(cx)}" cy="{n(cy)}" r="6"/>'
            f'<path class="zoom" d="M{n(cx + 4)} {n(cy + 4)} l5 5"/>')


def plate(x, y, w, h, key, logos, pad=3):
    if not key or key not in logos:
        return ""
    return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="5" fill="#ffffff"/>'
            f'<image data-logo="{esc(key)}" x="{n(x + pad)}" y="{n(y + pad)}" width="{n(w - 2 * pad)}" '
            f'height="{n(h - 2 * pad)}" preserveAspectRatio="xMidYMid meet"/>')


def marker(mid):
    return (f'<defs><marker id="{mid}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" '
            'markerHeight="7" orient="auto-start-reverse"><path d="M2 2 L8 5 L2 8" fill="none" '
            'stroke="context-stroke" stroke-width="1.8" stroke-linecap="round" '
            'stroke-linejoin="round"/></marker></defs>')


def path(cls, pts, mid, style="", dash=False):
    d = "M" + " L".join(f"{n(x)} {n(y)}" for x, y in pts)
    st = f' style="{style}"' if style else ""
    da = ' stroke-dasharray="5 4"' if dash else ""
    return f'<path class="{cls}"{st} d="{d}" fill="none"{da} marker-end="url(#{mid})"/>'


def lbl(x, y, text, anchor="middle", color=None):
    if not text:
        return ""
    st = f' style="fill:{color}"' if color else ' style="fill:var(--muted)"'
    return f'<text class="lbl" x="{n(x)}" y="{n(y)}" text-anchor="{anchor}"{st}>{esc(text)}</text>'


def flow_cls(f):
    if f.get("kind") == "auth":
        return "auth"
    return "flow" if f.get("main") else "arr"


# ----------------------------------------------------------------- modele
class Model:
    def __init__(self, model):
        self.m = model
        self.zones = {z["id"]: z for z in (model.get("zones") or []) if "id" in z}
        self.ents = {e["id"]: e for e in (model.get("entities") or []) if "id" in e}
        self.flows = model.get("flows") or []
        self.views = model.get("views") or []
        self.view_ids = {v["id"] for v in self.views}
        self.logos = model.get("logos") or {}
        self.children = {}
        for z in self.zones.values():
            self.children.setdefault(z.get("parent"), []).append(z["id"])
        self.frame = {zid: self._frame_kind(z) for zid, z in self.zones.items()}

    def chain(self, zid):
        out, seen = [], set()
        while zid and zid in self.zones and zid not in seen:
            seen.add(zid)
            out.append(zid)
            zid = self.zones[zid].get("parent")
        return list(reversed(out))          # du plus haut au plus bas

    def _contains_cluster(self, zid):
        stack = list(self.children.get(zid, []))
        while stack:
            c = stack.pop()
            z = self.zones[c]
            if z.get("color") == "cluster" or RX_CLUSTER.search(z.get("label", "")):
                return True
            stack += self.children.get(c, [])
        return False

    def _frame_kind(self, z):
        if z.get("style") == "team":
            return None
        lab = z.get("label", "")
        if z.get("color") == "cluster" or RX_CLUSTER.search(lab):
            return "cluster"
        if RX_NS.search(lab):
            return "ns"
        if not z.get("parent") and (RX_CLOUD.search(lab) or self._contains_cluster(z["id"])):
            return "cloud"
        return None

    def link_ok(self, link, vid):
        return link if (link and link in self.view_ids and link != vid) else None

    def subtree_ents(self, zid):
        zs, stack = set(), [zid]
        while stack:
            c = stack.pop()
            zs.add(c)
            stack += self.children.get(c, [])
        return [e for e in self.ents.values() if e.get("zone") in zs]

    def view_of_entity(self, eid, not_vid):
        best = None
        for v in self.views[1:]:
            if v["id"] != not_vid and eid in (v.get("members") or []):
                if best is None or len(v.get("members") or []) < len(best.get("members") or []):
                    best = v
        return best["id"] if best else (self.views[0]["id"] if self.views and self.views[0]["id"] != not_vid else None)


# ----------------------------------------------------------------- vue d'ensemble
def _cards(M, members, vid):
    """Regroupe les membres en cartes : la zone la plus haute qui n'est pas un cadre, sinon l'entite."""
    cards, order = {}, []
    ent2card = {}
    for eid in members:
        e = M.ents[eid]
        ch = M.chain(e.get("zone"))
        frames = [z for z in ch if M.frame.get(z)]
        card_zone = next((z for z in ch if not M.frame.get(z)), None)
        key = card_zone or ("e:" + eid)
        if key not in cards:
            if card_zone:
                z = M.zones[card_zone]
                cards[key] = {"id": key, "zone": card_zone, "label": z.get("label", card_zone),
                              "color": z.get("color"), "logo": z.get("logo"), "ents": [],
                              "link": M.link_ok(z.get("link"), vid), "frames": frames, "sub": z.get("sub")}
            else:
                cards[key] = {"id": key, "zone": None, "label": e.get("label", eid), "color": e.get("color"),
                              "logo": e.get("logo"), "ents": [], "link": M.link_ok(e.get("link"), vid),
                              "frames": frames, "sub": e.get("sub")}
            order.append(key)
        cards[key]["ents"].append(e)
        ent2card[eid] = key
    for c in cards.values():
        if not c["link"] and c["zone"] and len(c["ents"]) == 1:
            c["link"] = M.link_ok(c["ents"][0].get("link"), vid)
        if not c["logo"] and len(c["ents"]) == 1:
            c["logo"] = c["ents"][0].get("logo")
        if not c["color"] and len(c["ents"]) == 1:
            c["color"] = c["ents"][0].get("color")
        c["fk"] = {M.frame[z]: z for z in c["frames"]}
    return [cards[k] for k in order], ent2card


def _card_flows(M, ent2card):
    out, seen = [], {}
    for f in M.flows:
        a, b = ent2card.get(f.get("from")), ent2card.get(f.get("to"))
        if not a or not b or a == b:
            continue
        k = (a, b)
        if k in seen:
            if f.get("main") and not seen[k].get("main"):
                seen[k].update(main=True)
            if not seen[k]["label"] and f.get("label"):
                seen[k]["label"] = f["label"]
            continue
        g = {"a": a, "b": b, "label": f.get("label", ""), "main": bool(f.get("main")), "kind": f.get("kind")}
        seen[k] = g
        out.append(g)
    return out


def _topo(ids, flows):
    ids = list(ids)
    pos = {i: k for k, i in enumerate(ids)}
    indeg = {i: 0 for i in ids}
    succ = {i: [] for i in ids}
    for f in flows:
        if f["a"] in indeg and f["b"] in indeg:
            succ[f["a"]].append(f["b"])
            indeg[f["b"]] += 1
    out, rem = [], set(ids)
    while rem:
        ready = sorted([i for i in rem if indeg[i] == 0], key=pos.get)
        if not ready:
            ready = [min(rem, key=lambda i: (indeg[i], pos[i]))]
        i = ready[0]
        out.append(i)
        rem.discard(i)
        for s in succ[i]:
            indeg[s] -= 1
    return out


def _actor(c):
    return all((e.get("color") == "ext") or RX_ACTOR.search(e.get("label", "")) for e in c["ents"]) and \
        (c["zone"] is None or RX_ACTOR.search(c["label"]))


def render_overview(M, view, title_caption=None):
    vid = view["id"]
    members = [m for m in (view.get("members") or []) if m in M.ents]
    cards, ent2card = _cards(M, members, vid)
    cf = _card_flows(M, ent2card)
    by = {c["id"]: c for c in cards}
    has_cloud = any("cloud" in c["fk"] for c in cards)
    has_frames = any(c["fk"] for c in cards)

    def deg(cid, side):
        return sum(1 for f in cf if f[side] == cid)

    center, left, right, bottom = [], [], [], []
    for c in cards:
        inside = ("cloud" in c["fk"]) if has_cloud else bool(c["fk"])
        side_block = (c["zone"] is None and len(c["ents"]) == 1 and
                      (c.get("color") in ("partner", "partner2", "ops") or RX_OPS.search(c["label"])
                       or re.search(r"partenaire|partner", c["label"], re.I)))
        if side_block:
            right.append(c)
        elif inside:
            center.append(c)
        elif _actor(c):
            bottom.append(c)
        elif has_frames:
            outs = sum(1 for f in cf if f["a"] == c["id"] and ("cloud" in by[f["b"]]["fk"] or by[f["b"]]["fk"]))
            ins = sum(1 for f in cf if f["b"] == c["id"] and ("cloud" in by[f["a"]]["fk"] or by[f["a"]]["fk"]))
            ops = (c.get("color") == "ops") or RX_OPS.search(c["label"])
            (left if (outs > ins and not ops) else right).append(c)
        else:
            center.append(c)
    if not has_frames:                     # pas de cadre : sources a gauche, puits a droite
        srcs = [c for c in center if deg(c["id"], "b") == 0 and deg(c["id"], "a") > 0]
        sinks = [c for c in center if deg(c["id"], "a") == 0 and deg(c["id"], "b") > 0]
        if len(center) - len(srcs) - len(sinks) >= 1:
            left += srcs
            right += sinks
            center = [c for c in center if c not in srcs and c not in sinks]

    body, frames_svg = [], []
    mid = "a"
    body_flows = []

    # ---- colonne centrale
    cloud_z = next((c["fk"]["cloud"] for c in center if "cloud" in c["fk"]), None)
    clus_z = next((c["fk"]["cluster"] for c in center if "cluster" in c["fk"]), None)
    ns_z = next((c["fk"]["ns"] for c in center if "ns" in c["fk"]), None)
    top = [c for c in center if "cluster" not in c["fk"] and "ns" not in c["fk"]]
    inclus = [c for c in center if "cluster" in c["fk"] and "ns" not in c["fk"]]
    inns = [c for c in center if "ns" in c["fk"]]
    order = _topo([c["id"] for c in center], cf)
    rank = {cid: k for k, cid in enumerate(order)}
    top.sort(key=lambda c: rank[c["id"]])
    inclus.sort(key=lambda c: rank[c["id"]])
    inns.sort(key=lambda c: rank[c["id"]])

    geo = {}
    y = 148 if cloud_z else 112

    def small(c):
        return len(c["ents"]) == 1 and not c["ents"][0].get("sub") and len(c["label"]) <= 20

    def stack(group, x, w, y, gap):
        i = 0
        while i < len(group):
            c = group[i]
            if i + 1 < len(group) and small(c) and small(group[i + 1]):
                hw = (w - 18) / 2
                geo[c["id"]] = (x, y, hw, 60)
                geo[group[i + 1]["id"]] = (x + hw + 18, y, hw, 60)
                y += 60 + gap
                i += 2
                continue
            h = 64
            geo[c["id"]] = (x, y, w, h)
            y += h + gap
            i += 1
        return y - gap

    if top:
        for c in top:
            h = 92 if (c.get("sub") or c.get("logo") or len(c["ents"]) > 1) else 64
            geo[c["id"]] = (388, y, 384, h)
            y += h + 10
        y -= 10
    last = y
    clus_rect = ns_rect = None
    if clus_z and (inclus or inns):
        cy0 = (last + 10) if top else (y if not cloud_z else 158)
        yy = cy0 + 34
        if inclus:
            yy = stack(inclus, 388, 384, yy, 26) + 26
        if ns_z and inns:
            ns_y = yy if inclus else cy0 + 44
            yb = stack(inns, 406, 348, ns_y + 46, 26)
            ns_rect = (380, ns_y, 400, yb + 44 - ns_y)
            cb = ns_rect[1] + ns_rect[3] + 14
        else:
            cb = yy - 26 + 22
        clus_rect = (362, cy0, 446, cb - cy0)
        last = cb
    elif inns:
        ns_y = (last + 26) if top else y
        yb = stack(inns, 406, 348, ns_y + 46, 26)
        ns_rect = (380, ns_y, 400, yb + 44 - ns_y)
        last = ns_rect[1] + ns_rect[3]
    elif not top and center:
        last = stack(center, 388, 384, y, 26)
    cloud_rect = (352, 112, 464, last + 8 - 112) if cloud_z else None

    if cloud_rect:
        z = M.zones[cloud_z]
        x0, y0, w0, h0 = cloud_rect
        frames_svg.append(f'<rect x="{n(x0)}" y="{n(y0)}" width="{n(w0)}" height="{n(h0)}" rx="18" fill="none" '
                          'stroke="var(--sai)" stroke-width="1.4" stroke-dasharray="6 5"/>')
        lx = x0 + 12
        if z.get("logo") in M.logos:
            frames_svg.append(f'<image data-logo="{esc(z["logo"])}" x="{n(x0 + 12)}" y="{n(y0 - 30)}" width="20" '
                              'height="22" preserveAspectRatio="xMidYMid meet"/>')
            lx = x0 + 40
        frames_svg.append(f'<text class="lbl" x="{n(lx)}" y="{n(y0 - 13)}" style="fill:var(--sai)">'
                          f'{esc(z.get("label", ""))}</text>')
    if clus_rect:
        z = M.zones[clus_z]
        x0, y0, w0, h0 = clus_rect
        frames_svg.append(f'<rect x="{n(x0)}" y="{n(y0)}" width="{n(w0)}" height="{n(h0)}" rx="16" fill="none" '
                          'stroke="#326CE5" stroke-width="1.6" stroke-dasharray="4 4"/>')
        lab = z.get("label", "Kubernetes")
        pw = max(150, tw(lab, "lbl") + 70)
        link = M.link_ok(z.get("link"), vid)
        tab = (f'<rect x="{n(x0 + 20)}" y="{n(y0 - 6)}" width="{n(pw)}" height="26" rx="6" fill="var(--bg)"/>'
               f'<rect x="{n(x0 + 24)}" y="{n(y0 - 4)}" width="26" height="22" rx="4" fill="#ffffff"/>'
               f'<image data-logo="{esc(z.get("logo") or "kubernetes")}" x="{n(x0 + 27)}" y="{n(y0 - 3)}" width="20" '
               'height="20" preserveAspectRatio="xMidYMid meet"/>'
               f'<text x="{n(x0 + 56)}" y="{n(y0 + 11)}" style="fill:#326CE5;font-weight:700;font-size:12px;'
               f'font-family:var(--mono)">{esc(lab)}</text>')
        if link:
            tab += zoom(x0 + 20 + pw - 12, y0 + 6)
            tab = (f'<g class="blk" data-go="{esc(link)}" role="button" tabindex="0" '
                   f'aria-label="{esc(lab)}">{tab}</g>')
        frames_svg.append(tab)
    if ns_rect:
        z = M.zones[ns_z]
        x0, y0, w0, h0 = ns_rect
        frames_svg.append(f'<rect x="{n(x0)}" y="{n(y0)}" width="{n(w0)}" height="{n(h0)}" rx="14" fill="none" '
                          'stroke="var(--grn)" stroke-width="1.3" stroke-dasharray="6 5"/>'
                          f'<text class="lbl" x="{n(x0 + 20)}" y="{n(y0 + 28)}" style="fill:var(--grn)">'
                          f'{esc(z.get("label", ""))}</text>')

    # ---- colonnes laterales, alignees sur le bloc touche
    def anchor(c):
        ys = []
        for f in cf:
            o = f["b"] if f["a"] == c["id"] else (f["a"] if f["b"] == c["id"] else None)
            if o in geo:
                gx, gy, gw, gh = geo[o]
                ys.append(gy + gh / 2)
        return min(ys) if ys else None

    def side_h(c):
        k = len(c["ents"])
        if c["zone"] is None:
            return 100 if c.get("sub") else 64
        rich = any(e.get("sub") or e.get("logo") for e in c["ents"])
        if k > 4:
            return 92
        return 50 + k * ((78 if rich else 30) + 10) + 8

    def place_side(group, x, w, gap, prefer_ops=False):
        items = []
        for c in group:
            a = anchor(c)
            ops = (c.get("color") == "ops") or RX_OPS.search(c["label"])
            items.append((0 if (prefer_ops and ops) else 1, a if a is not None else 9999, c))
        items.sort(key=lambda t: (t[0], t[1]))
        yy = 148
        for _o, a, c in items:
            h = side_h(c)
            want = (a - 30) if a is not None and a < 9999 else yy
            cy = max(yy, want)
            geo[c["id"]] = (x, cy, w, h)
            yy = cy + h + gap

    place_side(left, 40, 272, 24)
    place_side(right, 850, 290, 30, prefer_ops=True)

    bottom_y = max([gy + gh for (gx, gy, gw, gh) in geo.values()] + [cloud_rect[1] + cloud_rect[3] if cloud_rect else 0]) + 104
    if bottom:
        tot = len(bottom) * 184 + (len(bottom) - 1) * 16
        bx = 584 - tot / 2
        for c in bottom:
            geo[c["id"]] = (bx, bottom_y, 184, 52)
            bx += 200

    # ---- cartes
    def card_svg(c, compact):
        x, y, w, h = geo[c["id"]]
        col = tok(c.get("color"))
        st = f' style="stroke:{col}"' if col else ""
        tcol = f' style="fill:{col}"' if (col and c.get("color") in TITLE_COLORED) else ""
        rx = 14 if c in left or c in right else (12 if c in bottom else 10)
        s = [f'<rect class="bg" x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="{rx}"{st}/>']
        if c in bottom:
            s.append(f'<circle cx="{n(x + 28)}" cy="{n(y + 26)}" r="14" fill="#5f6b7a"/>')
            if "user" in M.logos:
                s.append(f'<image data-logo="user" x="{n(x + 17)}" y="{n(y + 15)}" width="22" height="22" '
                         'preserveAspectRatio="xMidYMid meet"/>')
            s.append(f'<text class="tm" x="{n(x + 56)}" y="{n(y + 31)}">{esc(wrap(c["label"], w - 70)[0])}</text>')
        elif compact:
            names = " · ".join(e.get("label", "") for e in c["ents"]) if c["zone"] else (c.get("sub") or "")
            lx = x + 12
            if c.get("logo") in M.logos:
                s.append(plate(x + 12, y + h / 2 - 16, 32, 32, c["logo"], M.logos))
                lx = x + 56
                anchor_ = "start"
                tx = lx + 12
            else:
                anchor_ = "middle"
                tx = x + w / 2
            avail = (x + w - 28) - (lx + 12) if anchor_ == "start" else w - 40
            if c["zone"] and len(c["ents"]) == 1 and c["ents"][0].get("label") == c["label"]:
                names = c["ents"][0].get("sub") or ""
            if names:
                s.append(f'<text class="tm" x="{n(tx)}" y="{n(y + h / 2 - 6)}" text-anchor="{anchor_}"{tcol}>'
                         f'{esc(wrap(c["label"], avail)[0])}</text>')
                s.append(f'<text class="s" x="{n(tx)}" y="{n(y + h / 2 + 13)}" text-anchor="{anchor_}">'
                         f'{esc(wrap(names, avail, "s", 1)[0])}</text>')
            else:
                s.append(f'<text class="tm" x="{n(tx)}" y="{n(y + h / 2 + 5)}" text-anchor="{anchor_}"{tcol}>'
                         f'{esc(wrap(c["label"], avail)[0])}</text>')
        else:                                         # carte laterale : titre + boites internes
            s.append(f'<text class="t" x="{n(x + 22)}" y="{n(y + 32)}"{tcol}>{esc(wrap(c["label"], w - 60, "t", 1)[0])}</text>')
            if c["zone"] is None:
                if c.get("sub"):
                    s.append(f'<text class="s" x="{n(x + 22)}" y="{n(y + 62)}">{esc(wrap(c["sub"], w - 44, "s", 1)[0])}</text>')
            elif len(c["ents"]) > 4:
                names = " · ".join(e.get("label", "") for e in c["ents"])
                for i, ln in enumerate(wrap(names, w - 44, "s", 2)):
                    s.append(f'<text class="s" x="{n(x + 22)}" y="{n(y + 58 + i * 18)}">{esc(ln)}</text>')
            else:
                rich = any(e.get("sub") or e.get("logo") for e in c["ents"])
                rh = 78 if rich else 30
                yy = y + 46
                for e in c["ents"]:
                    bx, bw = x + 16, w - 32
                    s.append(f'<rect class="box" x="{n(bx)}" y="{n(yy)}" width="{n(bw)}" height="{rh}" rx="{10 if rich else 8}"/>')
                    if rich:
                        tx = bx + 16
                        if e.get("logo") in M.logos:
                            s.append(plate(bx + 9, yy + 18, 64, 42, e["logo"], M.logos))
                            tx = bx + 90
                        s.append(f'<text class="tm" x="{n(tx)}" y="{n(yy + 36)}">{esc(wrap(e.get("label", ""), bx + bw - tx - 8)[0])}</text>')
                        if e.get("sub"):
                            s.append(f'<text class="s" x="{n(tx)}" y="{n(yy + 56)}">{esc(wrap(e["sub"], bx + bw - tx - 8, "s", 1)[0])}</text>')
                    else:
                        tx, an = bx + bw / 2, "middle"
                        if e.get("logo") in M.logos:
                            s.append(plate(bx + 7, yy + 5, 40, 20, e["logo"], M.logos))
                            tx = bx + 26 + bw / 2
                        s.append(f'<text class="tm" x="{n(tx)}" y="{n(yy + 20)}" text-anchor="{an}">{esc(wrap(e.get("label", ""), bw - 60)[0])}</text>')
                    yy += rh + 10
        if c["link"]:
            s.append(zoom(x + w - 16, y + 14))
            return (f'<g class="blk" data-go="{esc(c["link"])}" role="button" tabindex="0" '
                    f'aria-label="{esc(c["label"])}">{"".join(s)}</g>')
        return f'<g class="card">{"".join(s)}</g>'

    for c in cards:
        if c["id"] in geo:
            body.append(card_svg(c, compact=(c in center)))

    # ---- flux entre cartes
    def side_of(cid):
        c = by[cid]
        return "c" if c in center else ("l" if c in left else ("r" if c in right else "b"))

    gutter_i = {}
    for f in cf:
        if f["a"] not in geo or f["b"] not in geo:
            continue
        A, B = geo[f["a"]], geo[f["b"]]
        sa, sb = side_of(f["a"]), side_of(f["b"])
        cls = flow_cls(f)
        st = "stroke:var(--grn)" if (f.get("kind") in ("pull", "read") and cls == "arr") else ""
        lc = "var(--grn)" if st else None
        ax, ay, aw, ah = A
        bx, by_, bw, bh = B
        if sa == "c" and sb == "c":
            if abs(ay - by_) < 1 and abs(ah - bh) < 1:          # meme rangee (paire)
                x1, x2 = (ax + aw, bx) if ax < bx else (ax, bx + bw)
                body_flows.append(path("arr", [(x1, ay + ah / 2), (x2, by_ + bh / 2)], mid))
                continue
            above = ay < by_
            overlap = (max(ax, bx), min(ax + aw, bx + bw))
            lo_, hi_ = (ay + ah, by_) if above else (by_ + bh, ay)
            between = any(g[1] < hi_ - 1 and g[1] + g[3] > lo_ + 1 and g[0] < overlap[1] and g[0] + g[2] > overlap[0]
                          for k_, g in geo.items() if k_ not in (f["a"], f["b"]) and by[k_] in center)
            if overlap[1] - overlap[0] > 20 and not between:
                cx = (overlap[0] + overlap[1]) / 2 if (aw < 300 or bw < 300) else 580
                y1, y2 = (ay + ah, by_ - 2) if above else (ay, by_ + bh + 2)
                body_flows.append(path(cls, [(cx, y1), (cx, y2)], mid))
                body_flows.append(lbl(cx + 18, (y1 + y2) / 2 + 4, f["label"], "start", lc))
            else:
                k = gutter_i.setdefault("c", 0)
                gutter_i["c"] = k + 1
                gx = max(ax + aw, bx + bw) + 12 + 5 * k
                body_flows.append(path(cls, [(ax + aw, ay + ah / 2), (gx, ay + ah / 2), (gx, by_ + bh / 2),
                                             (bx + bw + 2, by_ + bh / 2)], mid))
            continue
        if sb == "c" and sa == "l" or sa == "c" and sb == "l":
            L, C = (A, B) if sa == "l" else (B, A)
            yv = max(L[1] + 20, min(L[1] + L[3] - 20, C[1] + C[3] / 2))
            x1, x2 = L[0] + L[2], C[0] - 2
            pts = [(x1, yv), (x2, yv)] if sa == "l" else [(x2 + 2, yv), (x1 + 2, yv)]
            if not (C[1] + 8 <= yv <= C[1] + C[3] - 8):
                cy_ = C[1] + C[3] / 2
                mx = (x1 + x2) / 2
                pts = [(x1, yv), (mx, yv), (mx, cy_), (x2, cy_)] if sa == "l" else [(x2 + 2, cy_), (mx, cy_), (mx, yv), (x1 + 2, yv)]
            body_flows.append(path(cls, pts, mid, st))
            body_flows.append(lbl((x1 + x2) / 2, yv - 8, f["label"], "middle", lc))
            continue
        if sb == "r" or sa == "r":
            R, C = (B, A) if sb == "r" else (A, B)
            cy_ = C[1] + C[3] / 2
            ry = max(R[1] + R[3] * 0.55, min(R[1] + R[3] - 16, cy_))
            frame_r = max([r[0] + r[2] for r in (cloud_rect, clus_rect, ns_rect) if r] + [C[0] + C[2]])
            gx = (frame_r + R[0]) / 2 if frame_r < R[0] - 8 else C[0] + C[2] + 20
            if sb == "r":
                pts = [(C[0] + C[2], cy_), (gx, cy_), (gx, ry), (R[0] - 2, ry)] if abs(cy_ - ry) > 2 else [(C[0] + C[2], cy_), (R[0] - 2, ry)]
                lx_, ly_ = (C[0] + C[2] + gx) / 2, cy_ - 10
            else:
                tgt = frame_r + 2 if frame_r > C[0] + C[2] and (cloud_rect or clus_rect) and abs(cy_ - ry) <= 2 else C[0] + C[2] + 2
                pts = [(R[0], ry), (gx, ry), (gx, cy_), (C[0] + C[2] + 2, cy_)] if abs(cy_ - ry) > 2 else [(R[0], ry), (tgt, ry)]
                lx_, ly_ = (R[0] + gx) / 2, ry - 8
            body_flows.append(path(cls, pts, mid, st))
            body_flows.append(lbl(R[0] - 6, (ry if sa == "r" else cy_) - 8, f["label"], "end", lc))
            continue
        if sa == "b" or sb == "b":
            Bt, C = (A, B) if sa == "b" else (B, A)
            cx = Bt[0] + Bt[2] / 2
            if not (C[0] + 8 <= cx <= C[0] + C[2] - 8):
                cx = min(max(cx, C[0] + 20), C[0] + C[2] - 20)
            pts = [(cx, Bt[1] - 2), (cx, C[1] + C[3] + 2)]
            body_flows.append(path(cls, pts if sa == "b" else list(reversed(pts)), mid, st))
            continue

    # legende
    if title_caption:
        body.append(f'<text class="s" x="580" y="{n(bottom_y + (90 if bottom else -40))}" text-anchor="middle" '
                    f'style="fill:var(--muted)">{esc(title_caption)}</text>')
    allr = list(geo.values()) + [r for r in (cloud_rect, clus_rect, ns_rect) if r]
    H = max(y + h for (x, y, w, h) in allr) + (80 if title_caption else 40)
    X0 = min([0] + [x - 20 for (x, y, w, h) in allr])
    X1 = max([1180] + [x + w + 20 for (x, y, w, h) in allr])
    Y0 = min(y for (x, y, w, h) in allr) - (44 if cloud_rect else 30)
    return (f'<svg viewBox="{n(X0)} {n(Y0)} {n(X1 - X0)} {n(H - Y0)}" role="img" aria-label="{esc(view.get("label", vid))}, cliquable">'
            f'{marker(mid)}{"".join(frames_svg)}{"".join(body)}{"".join(body_flows)}</svg>')


# ----------------------------------------------------------------- sous-vues
def _view_zone(M, view):
    if view.get("zone") in M.zones:
        return view["zone"]
    for z in M.zones.values():
        if z.get("link") == view["id"]:
            return z["id"]
    return None


def render_subview(M, view, ov_id):
    vid = view["id"]
    members = [m for m in (view.get("members") or []) if m in M.ents]
    vz = _view_zone(M, view)
    mset = set(members)
    # zones filles avec leur propre vue : repliees en une carte cliquable
    rep = {}
    nodes = {}
    if vz:
        for cz in M.children.get(vz, []):
            z = M.zones[cz]
            link = M.link_ok(z.get("link"), vid)
            sub = [e for e in M.subtree_ents(cz) if e["id"] in mset]
            if link and sub:
                key = "z:" + cz
                nodes[key] = {"label": z.get("label", cz), "sub": " · ".join(e.get("label", "") for e in sub),
                              "color": z.get("color"), "logo": z.get("logo"), "link": link, "card": True}
                for e in sub:
                    rep[e["id"]] = key
    for eid in members:
        if eid in rep:
            continue
        e = M.ents[eid]
        nodes[eid] = {"label": e.get("label", eid), "sub": e.get("sub"), "color": e.get("color"),
                      "logo": e.get("logo"), "link": M.link_ok(e.get("link"), vid), "desc": e.get("desc"),
                      "db": e.get("color") == "db" or bool(RX_DB.search(e.get("label", "")))}
        rep[eid] = eid
    edges, seen = [], set()
    ext_in, ext_out = None, []
    for f in M.flows:
        a, b = f.get("from"), f.get("to")
        ra, rb = rep.get(a), rep.get(b)
        if ra and rb and ra != rb:
            if (ra, rb) not in seen:
                seen.add((ra, rb))
                edges.append({"a": ra, "b": rb, "label": f.get("label", ""), "main": f.get("main"), "kind": f.get("kind")})
        elif rb and not ra and a in M.ents and ext_in is None:
            ext_in = (M.ents[a].get("label", a), rb)
        elif ra and not rb and b in M.ents and len(ext_out) < 2:
            tgt_view = M.view_of_entity(b, vid)
            ch = M.chain(M.ents[b].get("zone"))
            cz = next((z for z in reversed(ch) if not M.frame.get(z)), None)
            label = M.zones[cz]["label"] if cz else M.ents[b].get("label", b)
            key = "x:" + (cz or b)
            if key not in nodes:
                nodes[key] = {"label": label, "sub": None, "color": M.zones[cz].get("color") if cz else M.ents[b].get("color"),
                              "logo": None, "link": tgt_view if tgt_view != vid else None, "card": True, "ext": True}
                ext_out.append(key)
            if (ra, key) not in seen:
                seen.add((ra, key))
                edges.append({"a": ra, "b": key, "label": f.get("label", ""), "main": f.get("main"), "kind": f.get("kind")})
    if not ext_in and vz:
        parent = M.zones[vz].get("parent")
        if parent and not M.frame.get(parent):
            ext_in = (M.zones[parent].get("label", parent), None)
    if not ext_in:
        def links_to(v):
            for m in (v.get("members") or []):
                e = M.ents.get(m)
                if not e:
                    continue
                if e.get("link") == vid or any(M.zones[z].get("link") == vid for z in M.chain(e.get("zone"))):
                    return True
            return False
        par = next((v for v in M.views if v["id"] != vid and links_to(v)), None)
        if par:
            ext_in = ("la vue d'ensemble" if par["id"] == ov_id else par.get("label", par["id"]), None)

    # tailles
    for k, nd in nodes.items():
        base = max(tw(nd["label"]) + 44, tw(nd.get("sub") or "", "s") + 32 if not nd.get("card") else 0)
        w = max(98 if not (nd.get("logo") in M.logos) else 130, min(210 if not nd.get("card") else 170, base))
        nd["w"], nd["h"] = w, (70 if nd.get("db") else 60)

    # chaines (plus long chemin, une par groupe connecte), sorties sous leur voisin, le reste en ligne
    ids = list(nodes)
    order = _topo(ids, edges)
    pos = {i: k for k, i in enumerate(order)}

    def longest(pool):
        sub = [e for e in edges if e["a"] in pool and e["b"] in pool]
        if not sub:
            return []
        dist, prev = {i: 0 for i in pool}, {i: None for i in pool}
        for i in sorted(pool, key=pos.get):
            for e in sub:
                if e["a"] == i and pos[e["b"]] > pos[i] and dist[i] + 1 > dist[e["b"]]:
                    dist[e["b"]], prev[e["b"]] = dist[i] + 1, i
        end = max(pool, key=lambda i: (dist[i], -pos[i]))
        ch = []
        while end is not None:
            ch.append(end)
            end = prev[end]
        return list(reversed(ch)) if len(ch) > 1 else []

    pool = set(ids)
    chains = []
    while True:
        ch = longest(pool)
        if not ch:
            break
        chains.append(ch)
        pool -= set(ch)
    # rattache les voisins restants a la chaine la plus proche (ligne du dessous)
    nbr = {i: set() for i in ids}
    for e in edges:
        nbr[e["a"]].add(e["b"])
        nbr[e["b"]].add(e["a"])
    geo = {}
    X0, XMAX, ROWY = 60, 1150, 110
    y = ROWY
    chain_next = {}
    elab = {(e["a"], e["b"]): e.get("label") or "" for e in edges}

    def gap_after(a, b):
        return max(34, tw(elab.get((a, b), ""), "lbl") + 18)
    first_node = None
    for ch in chains:
        bands, band, x = [], [], X0
        for i, k in enumerate(ch):
            if band and x + nodes[k]["w"] > XMAX:
                bands.append(band)
                band, x = [], X0
            band.append(k)
            x += nodes[k]["w"] + (gap_after(k, ch[i + 1]) if i + 1 < len(ch) else 34)
        bands.append(band)
        for i in range(len(ch) - 1):
            chain_next[ch[i]] = ch[i + 1]
        for band in bands:
            x = X0
            for i, k in enumerate(band):
                geo[k] = (x, y, nodes[k]["w"], nodes[k]["h"])
                x += nodes[k]["w"] + (gap_after(k, band[i + 1]) if i + 1 < len(band) else 34)
            first_node = first_node or band[0]
            row = []
            for r in sorted(pool, key=pos.get):
                anc = next((c for c in band if c in nbr[r]), None)
                if anc is None:
                    continue
                gx, gy, gw, gh = geo[anc]
                row.append((gx + gw / 2 - nodes[r]["w"] / 2, r))
            for _w, r in row:
                pool.discard(r)
            row.sort()
            cur = X0 - 999
            for want, r in row:
                xx = max(want, cur + 24, X0)
                geo[r] = (xx, y + 112, nodes[r]["w"], nodes[r]["h"])
                cur = xx + nodes[r]["w"]
            y += 60 + (112 if row else 0) + 70
    if pool:
        x = X0
        for r in sorted(pool, key=pos.get):
            if x + nodes[r]["w"] > XMAX and x > X0:
                x = X0
                y += 90
            geo[r] = (x, y, nodes[r]["w"], nodes[r]["h"])
            first_node = first_node or r
            x += nodes[r]["w"] + 34
        y += 90
    chain = chains[0] if chains else []
    if geo:                                            # contenu etroit : centre dans la largeur de reference
        right_ = max(x + w for (x, _y, w, _h) in geo.values())
        dx = (1190 - 60 - right_) / 2
        if dx > 20:
            geo = {k: (x + dx, y_, w, h) for k, (x, y_, w, h) in geo.items()}

    mid = "m-" + re.sub(r"[^A-Za-z0-9_-]", "", vid)[:40]
    body, arrows = [], []
    cap = view.get("caption") or (M.zones[vz].get("desc") if vz and M.zones[vz].get("desc") else None) \
        or view.get("label", vid)
    body.append(lbl(40, 36, cap, "start"))
    first = first_node
    if ext_in and first in geo:
        gx, gy, gw, gh = geo[first]
        cx = gx + gw / 2
        arrows.append(f'<path class="arr" d="M{n(cx)} {n(gy - 40)} L{n(cx)} {n(gy - 2)}" fill="none" '
                      f'stroke-dasharray="5 4" marker-end="url(#{mid})"/>')
        arrows.append(lbl(cx + 33, gy - 20, "depuis " + ext_in[0], "start"))

    for k, nd in nodes.items():
        if k not in geo:
            continue
        x, y_, w, h = geo[k]
        col = tok(nd.get("color"))
        st = f' style="stroke:{col}"' if col else ""
        if nd.get("db"):
            cx = x + w / 2
            c = col or "var(--rds)"
            s = (f'<ellipse cx="{n(cx)}" cy="{n(y_ + 29)}" rx="15" ry="5" fill="{c}"/>'
                 f'<rect x="{n(cx - 15)}" y="{n(y_ + 5)}" width="30" height="24" fill="{c}"/>'
                 f'<line x1="{n(cx - 15)}" y1="{n(y_ + 5)}" x2="{n(cx - 15)}" y2="{n(y_ + 29)}" stroke="{c}"/>'
                 f'<line x1="{n(cx + 15)}" y1="{n(y_ + 5)}" x2="{n(cx + 15)}" y2="{n(y_ + 29)}" stroke="{c}"/>'
                 f'<ellipse cx="{n(cx)}" cy="{n(y_ + 17)}" rx="15" ry="5" fill="#7badde" stroke="{c}"/>'
                 f'<ellipse cx="{n(cx)}" cy="{n(y_ + 5)}" rx="15" ry="5" fill="#9cc2e8" stroke="{c}"/>'
                 f'<text class="tm" x="{n(cx)}" y="{n(y_ + 49)}" text-anchor="middle" style="fill:{c}">{esc(nd["label"])}</text>')
            if nd.get("sub"):
                s += f'<text class="s" x="{n(cx)}" y="{n(y_ + 65)}" text-anchor="middle" style="fill:var(--muted)">{esc(nd["sub"])}</text>'
            body.append(s)
            continue
        card = bool(nd.get("card") or nd.get("link"))
        rect = (f'<rect class="{"bg" if card else "box"}" x="{n(x)}" y="{n(y_)}" width="{n(w)}" height="{n(h)}" rx="10"{st}/>')
        inner = []
        tx = x + w / 2
        dy = 0
        if nd.get("logo") in M.logos:
            inner.append(plate(x + 8, y_ + 6, 40, 16, nd["logo"], M.logos, 2))
            dy = 8
        tcol = f' style="fill:{col}"' if (col and (card or nd.get("color") in TITLE_COLORED)) else ""
        lines = wrap(nd["label"], w - (34 if card else 20), "tm", 2)
        if nd.get("sub") and not nd.get("card") and len(lines) == 1:
            inner.append(f'<text class="tm" x="{n(tx)}" y="{n(y_ + 27 + dy)}" text-anchor="middle"{tcol}>{esc(lines[0])}</text>')
            inner.append(f'<text class="s" x="{n(tx)}" y="{n(y_ + 45 + dy * .9)}" text-anchor="middle">{esc(wrap(nd["sub"], w - 16, "s", 1)[0])}</text>')
        elif len(lines) == 2:
            inner.append(f'<text class="tm" x="{n(tx)}" y="{n(y_ + 25 + dy)}" text-anchor="middle"{tcol}>{esc(lines[0])}</text>')
            inner.append(f'<text class="tm" x="{n(tx)}" y="{n(y_ + 43 + dy * .7)}" text-anchor="middle"{tcol}>{esc(lines[1])}</text>')
        else:
            inner.append(f'<text class="tm" x="{n(tx)}" y="{n(y_ + 35 + dy)}" text-anchor="middle"{tcol}>{esc(lines[0])}</text>')
        if nd.get("card") and nd.get("sub"):
            inner.append(f'<title>{esc(nd["label"])} : {esc(nd["sub"])}</title>')
        if card and nd.get("link"):
            inner.append(zoom(x + w - 14, y_ + 12))
            body.append(f'<g class="blk" data-go="{esc(nd["link"])}" role="button" tabindex="0" '
                        f'aria-label="{esc(nd["label"])}">{rect}{"".join(inner)}</g>')
        elif nd.get("desc"):
            lines_d = [l.strip(" -") for l in re.split(r"[\n;]", str(nd["desc"])) if l.strip()]
            th = 44 + 18 * len(lines_d)
            tip = (f'<g class="tip" aria-hidden="true"><rect class="tipbg" x="{n(x - 20)}" y="{n(y_ + h + 10)}" width="300" '
                   f'height="{n(th)}" rx="10"/><text class="tiphd" x="{n(x - 2)}" y="{n(y_ + h + 32)}">{esc(nd["label"])}</text>'
                   + "".join(f'<text class="tipln" x="{n(x - 2)}" y="{n(y_ + h + 54 + 18 * i)}">- {esc(l)}</text>' for i, l in enumerate(lines_d))
                   + "</g>")
            body.append(f'<g class="det" tabindex="0">{rect}{"".join(inner)}<title>{esc(nd["label"])} : {esc(", ".join(lines_d))}</title>{tip}</g>')
        else:
            body.append(rect + "".join(inner))

    for e in edges:
        a, b = e["a"], e["b"]
        if a not in geo or b not in geo:
            continue
        ax, ay, aw, ah = geo[a]
        bx, by_, bw, bh = geo[b]
        cls = flow_cls(e) if e.get("kind") == "auth" or e.get("main") else "arr"
        if cls == "flow":
            cls = "arr"                      # dans une sous-vue, fleches sobres (comme la reference)
        if chain_next.get(a) == b and abs(ay + ah / 2 - (by_ + bh / 2)) < 2:
            yv = ay + ah / 2
            arrows.append(path(cls, [(ax + aw, yv), (bx - (4 if nodes[b].get("card") else 0), yv)], mid))
            arrows.append(lbl((ax + aw + bx) / 2, yv - 10, e["label"]))
            continue
        acx, bcx = ax + aw / 2, bx + bw / 2
        if by_ >= ay + ah - 1:                         # vers le bas
            if abs(acx - bcx) < 6:
                pts = [(acx, ay + ah), (acx, by_ - 2)]
            else:
                my = (ay + ah + by_) / 2
                pts = [(acx, ay + ah), (acx, my), (bcx, my), (bcx, by_ - 2)]
            arrows.append(path(cls, pts, mid))
            arrows.append(lbl(bcx + 32, (ay + ah + by_) / 2 + 2, e["label"], "start"))
        elif ay >= by_ + bh - 1:                       # vers le haut
            if abs(acx - bcx) < 6:
                pts = [(acx, ay), (acx, by_ + bh + 2)]
            else:
                my = (by_ + bh + ay) / 2
                pts = [(acx, ay), (acx, my), (bcx, my), (bcx, by_ + bh + 2)]
            arrows.append(path(cls, pts, mid))
            arrows.append(lbl(acx + 32, (by_ + bh + ay) / 2 + 2, e["label"], "start"))
        else:                                          # meme hauteur, non consecutifs
            yv = max(ay, by_) - 14
            x1, x2 = (ax + aw / 2, bx + bw / 2)
            pts = [(x1, ay), (x1, yv), (x2, yv), (x2, by_ - 2)]
            arrows.append(path(cls, pts, mid))
            arrows.append(lbl((x1 + x2) / 2, yv - 6, e["label"]))
    if view.get("note"):
        arrows.append(lbl(580, y + 4, view["note"]))
        y += 30
    W = max(1190, max([x + w for (x, _y, w, _h) in geo.values()] + [0]) + 30)
    H = max([yy + hh for (_x, yy, _w, hh) in geo.values()] + [120]) + (60 if view.get("note") else 40)
    return (f'<svg viewBox="0 0 {n(W)} {n(H)}" role="img" aria-label="{esc(view.get("label", vid))}">'
            f'{marker(mid)}{"".join(body)}{"".join(arrows)}</svg>')


# ----------------------------------------------------------------- page
_EXTRA_CSS = """
  .card rect.bg{fill:var(--surface);stroke:var(--line);stroke-width:1.5;filter:drop-shadow(0 2px 4px rgba(15,23,42,.12))}
  .vtools{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px}
  .vtools .back{margin-bottom:0}
  .vtools .grow{flex:1}
  .imp{display:inline-flex;align-items:center;gap:.4rem;font:inherit;font-size:12.5px;font-weight:500;color:var(--muted);
    background:var(--s2);border:1px solid var(--line);border-radius:999px;padding:5px 12px;cursor:pointer}
  .imp:hover{color:var(--sai);border-color:var(--sai)}
  .imp input{display:none}
  .imp[hidden]{display:none!important}
  .impinfo{font-size:12px;color:var(--muted)}
  .imp select{font:inherit;font-size:12px;background:var(--surface);color:var(--ink);border:1px solid var(--line);border-radius:6px}
  .crumb .mid{font:inherit;font-size:14px;font-weight:500;color:var(--sai);background:none;border:none;cursor:pointer;padding:6px 10px;border-radius:8px}
"""

_JS = r"""
(function(){
  var names=__NAMES__, OV=__OV__, KEY=__KEY__;
  var trail=document.getElementById("trail");
  var cur=OV,hist=[];
  function crumb(){
    if(cur===OV){trail.innerHTML="";return;}
    var h="",path=hist.filter(function(x){return x!==OV;});
    path.forEach(function(id,i){h+='<span class="sep">›</span> <button class="mid" data-jump="'+i+'">'+(names[id]||id)+'</button>';});
    h+='<span class="sep">›</span> <span class="cur">'+(names[cur]||cur)+'</span>';
    trail.innerHTML=h;
    trail.querySelectorAll("[data-jump]").forEach(function(b){b.addEventListener("click",function(){
      var i=+b.getAttribute("data-jump"),p=hist.filter(function(x){return x!==OV;}),tgt=p[i];
      hist=[OV].concat(p.slice(0,i));render(tgt);});});
  }
  function render(id){
    document.querySelectorAll(".view").forEach(function(v){v.hidden=(v.id!=="v-"+id);});
    cur=id;crumb();
    var prev=hist.length?hist[hist.length-1]:OV;
    document.querySelectorAll("[data-back]").forEach(function(b){b.innerHTML="&lsaquo; "+(names[prev]||names[OV]);});
    try{document.querySelector(".stage").scrollIntoView({block:"nearest"});}catch(e){}
  }
  function go(id){ if(id!==cur){hist.push(cur);} render(id); }
  function back(){ render(hist.length?hist.pop():OV); }
  function bind(root){
    root.querySelectorAll("[data-go]").forEach(function(b){
      if(b._b)return;b._b=1;
      b.addEventListener("click",function(){go(b.getAttribute("data-go"));});
      b.addEventListener("keydown",function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();go(b.getAttribute("data-go"));}});
    });
  }
  function logos(root){try{var L=window.LOGOS||{};root.querySelectorAll('image[data-logo]').forEach(function(im){var k=im.getAttribute('data-logo');if(L[k]){im.setAttributeNS('http://www.w3.org/1999/xlink','href',L[k]);im.setAttribute('href',L[k]);}});}catch(e){}}
  window.__archi={go:go,bind:bind,logos:logos,names:names,KEY:KEY};
  bind(document);
  document.querySelectorAll("[data-back]").forEach(function(b){b.addEventListener("click",function(){back();});});
  document.getElementById("home").addEventListener("click",function(){hist=[];render(OV);});
  logos(document);
  go(OV);
})();
"""

_THEME_JS = r"""(function(){var KEY=__TKEY__,r=document.documentElement;function apply(t){r.setAttribute('data-theme',t);r.removeAttribute('data-skin');var b=document.getElementById('xtheme');if(b)b.textContent=(t==='light'?'☀ Thème : Clair':'☾ Thème : Sombre');}var t='dark';try{t=localStorage.getItem(KEY)||'dark';}catch(e){}apply(t);var b=document.getElementById('xtheme');if(b)b.addEventListener('click',function(){t=(r.getAttribute('data-theme')==='light')?'dark':'light';try{localStorage.setItem(KEY,t);}catch(e){}apply(t);});var m=document.getElementById('xmenu'),d=document.getElementById('xdrop');if(m&&d){m.addEventListener('click',function(e){e.stopPropagation();var o=d.classList.toggle('open');m.setAttribute('aria-expanded',o);});document.addEventListener('click',function(e){if(d.contains(e.target))return;d.classList.remove('open');m.setAttribute('aria-expanded','false');});document.addEventListener('keydown',function(e){if(e.key==='Escape'){d.classList.remove('open');m.setAttribute('aria-expanded','false');}});}})();"""


def _slug(t):
    return re.sub(r"[^a-z0-9]+", "-", str(t).lower()).strip("-") or "archi"


def _library_logos():
    """Bibliotheque partagee du framework (assets/logos) : logos par defaut (cluster, cloud, utilisateur,
    identite...) et reconnaissance des libelles a l'import draw.io dans le navigateur."""
    try:
        import import_drawio as IMP  # sibling (archi/)
        return IMP.logo_sources()
    except Exception:
        return {}


def build_page(model, drawio_b64=None):
    model = dict(model)
    model["logos"] = {**_library_logos(), **(model.get("logos") or {})}
    M = Model(model)
    meta = model.get("meta") or {}
    title = meta.get("project") or "Architecture"
    views = M.views
    if not views:
        raise ValueError("Le modele ne declare aucune vue (`views`).")
    ov = views[0]["id"]
    names = {v["id"]: v.get("label", v["id"]) for v in views}
    names[ov] = "Vue d'ensemble"
    seq, imports, sections = {}, {}, []
    for v in views:
        vid = v["id"]
        tools = ['<div class="vtools">']
        if vid != ov:
            tools.append(f'<button class="back" data-back>&lsaquo; {esc(names[ov])}</button>')
        tools.append('<span class="grow"></span></div>')
        if v.get("kind") == "sequence":
            seq[vid] = {k: v.get(k) for k in ("caption", "participants", "messages", "notes")}
            svg = f'<svg viewBox="0 0 1180 420" role="img" aria-label="{esc(v.get("label", vid))}" data-seq="{esc(vid)}"></svg>'
        elif vid == ov:
            svg = render_overview(M, v, meta.get("caption"))
        else:
            svg = render_subview(M, v, ov)
        if v.get("drawio"):
            imports[vid] = {"name": v.get("drawio_name") or "modèle", "xml": v["drawio"], "page": v.get("drawio_page"),
                            "mode": v.get("drawio_mode") or "schema"}
        hidden = "" if vid == ov else " hidden"
        sections.append(f'<!-- ============ {esc(names[vid]).upper()} ============ -->\n'
                        f'    <div class="view" id="v-{esc(vid)}"{hidden}>\n      {"".join(tools)}\n      '
                        f'<div class="vsvg">{svg}</div>\n    </div>')
    navlinks = "".join(
        f'<a href="{esc(l.get("url", "#"))}"{" class=\"active\" aria-current=\"page\"" if l.get("active") else " target=\"_blank\" rel=\"noopener\""} role="menuitem">'
        f'{esc(l.get("label", ""))}{"" if l.get("active") else " <span class=\"ar\" aria-hidden=\"true\">↗</span>"}</a>'
        for l in (meta.get("nav") or []))
    copy = ('<button type="button" id="xdrawio" class="xtheme">⌘ Copier le .drawio</button>' if drawio_b64 else "")
    key = _slug(meta.get("theme_key") or title)
    js = (_JS.replace("__NAMES__", json.dumps(names, ensure_ascii=False)).replace("__OV__", json.dumps(ov))
          .replace("__KEY__", json.dumps(key)))
    import_js = (HERE / "golden_import.js").read_text(encoding="utf-8")
    copy_js = ""
    if drawio_b64:
        copy_js = ("<script>(function(){var b=document.getElementById('xdrawio');if(!b)return;b.addEventListener('click',function(){"
                   "try{var x=decodeURIComponent(escape(atob(window.__DRAWIO_B64)));navigator.clipboard.writeText(x).then(function(){"
                   "b.textContent='✓ Copié';setTimeout(function(){b.textContent='⌘ Copier le .drawio';},1500);},function(){b.textContent='Copie refusée';});"
                   "}catch(e){b.textContent='Copie indisponible';}});})();</script>"
                   f"<script>window.__DRAWIO_B64={json.dumps(drawio_b64)};</script>")
    head = (
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        f'<title>{esc(title)}</title><script>try{{var _t=localStorage.getItem({json.dumps(key + "-theme")})||\'dark\';'
        "document.documentElement.setAttribute('data-theme',_t);}catch(e){document.documentElement.setAttribute('data-theme','dark');}</script>\n"
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500&family=Manrope:wght@400;500;600;700&display=swap">\n'
        f'<style>\n{CSS}{_EXTRA_CSS}</style>\n'
    )
    body = (
        f'<div class="wrap"><nav class="xnav" aria-label="Pages"><div class="xmenu"><button type="button" id="xmenu" class="xnav-btn" '
        'aria-label="Navigation" aria-haspopup="true" aria-expanded="false"><span class="xbg"><i></i><i></i><i></i></span> Menu</button>'
        f'<div class="xdrop" id="xdrop" role="menu">{navlinks}{"<div class=\"xsep\" role=\"separator\"></div>" if navlinks else ""}'
        f'<button type="button" id="xtheme" class="xtheme" aria-label="Basculer le thème">Thème</button>{copy}</div></div></nav>\n'
        '  <nav class="crumb"><button id="home">Vue d\'ensemble</button><span id="trail"></span></nav>\n\n'
        f'  <div class="stage">\n    {"".join(sections)}\n  </div>\n</div>\n'
        f'<script>window.LOGOS={json.dumps(M.logos, ensure_ascii=False)};window.SEQ={json.dumps(seq, ensure_ascii=False)};'
        f'window.IMPORTS={json.dumps(imports, ensure_ascii=False)};</script>\n'
        f'<script>{js}</script>\n<script>{import_js}</script>\n'
        f'<script>{_THEME_JS.replace("__TKEY__", json.dumps(key + "-theme"))}</script>\n{copy_js}'
    )
    return "<!doctype html><html lang=\"fr\"><head>" + head + "</head><body>" + body + "</body></html>"
