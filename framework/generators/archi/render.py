#!/usr/bin/env python3
"""
render.py - primitives de dessin stack-imagery (bibliothèque, pas un exécutable).

Ce sont les briques forgées pendant la construction du schéma SINBAD. On les importe pour
(re)construire UNE vue SVG proprement, ou pour assembler une page complète (fork d'une autre
infra). Le rendu final reste artisanal : on place les coordonnées à la main, ces helpers
garantissent juste les conventions (flèches rectilignes, cylindre DB, logos à plaque blanche,
double flèche, entrée tiretée par le haut, encarts d'équipe).

    from render import A, box, card, team, db, dashed_in, roundtrip, lg, zoom, label, svg, shell

Conventions encodées (voir KNOWLEDGE.md / model.json) :
  - flèches rectilignes (H/V) via A([(x,y),...]) ;
  - base de données = petit cylindre PostgreSQL (db) ;
  - un composant tiré (BFF récupère, Frontend appelle) = roundtrip() (double flèche) ;
  - entrée d'un flux externe = dashed_in() (tiretée, par le haut) ;
  - couleurs par token CSS (var(--sai|grn|soc|amb|s3|rds|kc)) définis dans le :root de base.

Après assemblage, TOUJOURS passer validate.py avant publication.
"""

TOKENS = {k: f"var(--{k})" for k in
          ("sai", "grn", "soc", "amb", "s3", "rds", "kc", "muted", "ink")}


def esc(t):
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def lg(key, x, y, w, h, p=3):
    """Logo (data-URI injecté via window.LOGOS) sur une plaque blanche."""
    return (f'<rect x="{x-p}" y="{y-p}" width="{w+2*p}" height="{h+2*p}" rx="4" fill="#ffffff"/>'
            f'<image data-logo="{esc(key)}" x="{x}" y="{y}" width="{w}" height="{h}" '
            'preserveAspectRatio="xMidYMid meet"/>')


def zoom(cx, cy):
    """Loupe (coin haut-droit d'un bloc cliquable)."""
    return f'<circle class="zoom" cx="{cx}" cy="{cy}" r="6"/><path class="zoom" d="M{cx+4} {cy+4} l5 5"/>'


def label(x, y, t, anchor="middle", color="var(--muted)"):
    return (f'<text class="lbl" x="{x}" y="{y}" text-anchor="{anchor}" '
            f'style="fill:{color}">{esc(t)}</text>')


def A(pts, color="var(--muted)", mid="ae", dash=False):
    """Flèche rectiligne multi-points (H/V uniquement). pts = [(x,y), ...]."""
    d = "M" + " L".join(f"{x} {y}" for x, y in pts)
    extra = ' stroke-dasharray="5 4"' if dash else ''
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.5"{extra} '
            f'marker-end="url(#{mid})"/>')


def box(x, y, w, h, text, sub=None, stroke=None, logo=None, link=None, label2=None):
    """Boîte standard. stroke = token couleur ; logo à gauche ; link = data-go (cliquable)."""
    st = f' style="stroke:{stroke}"' if stroke else ''
    s = f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"{st}/>'
    off = 0
    if logo:
        s += lg(logo, x + 10, y + h / 2 - 11, 22, 22)
        off = 14
    cx = x + w / 2 + off
    tc = f' style="fill:{stroke}"' if stroke else ''
    if label2:  # libellé sur deux lignes
        s += f'<text class="tm" x="{cx}" y="{y+h/2-2}" text-anchor="middle"{tc}>{esc(text)}</text>'
        s += f'<text class="tm" x="{cx}" y="{y+h/2+16}" text-anchor="middle"{tc}>{esc(label2)}</text>'
    elif sub:
        s += f'<text class="tm" x="{cx}" y="{y+h/2-2}" text-anchor="middle"{tc}>{esc(text)}</text>'
        s += f'<text class="s" x="{x+w/2}" y="{y+h/2+16}" text-anchor="middle">{esc(sub)}</text>'
    else:
        s += f'<text class="tm" x="{cx}" y="{y+h/2+5}" text-anchor="middle"{tc}>{esc(text)}</text>'
    if link:
        s += zoom(x + w - 16, y + 16)
        return (f'<g class="blk" data-go="{esc(link)}" role="button" tabindex="0" '
                f'aria-label="{esc(text)}">{s}</g>')
    return s


def card(x, y, w, logos, title, color, h=46):
    """Carte « outil » (Terraform, Argo, Flux...) : logos à gauche, titre à droite, bord coloré."""
    s = f'<rect class="box" x="{x}" y="{y}" width="{w}" height="{h}" rx="10" style="stroke:{color};stroke-width:1.6"/>'
    lx = x + 12
    for k in logos:
        s += lg(k, lx, y + 12, 22, 22)
        lx += 28
    s += f'<text class="tm" x="{lx+4}" y="{y+29}">{esc(title)}</text>'
    return s


def team(x, y, w, h, label_txt, color):
    """Encart d'équipe (conteneur en tiretés + libellé en gras coloré). Ex : CIP / Devs / Enix."""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="none" '
            f'stroke="{color}" stroke-width="1.5" stroke-dasharray="6 5"/>'
            f'<text class="lbl" x="{x+12}" y="{y+22}" text-anchor="start" '
            f'style="fill:{color};font-weight:700">{esc(label_txt)}</text>')


def zone(x, y, w, h, label_txt=None, fill="var(--s2)", stroke="var(--line)"):
    s = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" '
         f'stroke="{stroke}" stroke-width="1.2" stroke-dasharray="5 5" opacity="0.9"/>')
    if label_txt:
        s += f'<text class="t" x="{x+16}" y="{y+22}" text-anchor="start">{esc(label_txt)}</text>'
    return s


def db(cx, top, label_txt="PostgreSQL", sub=None):
    """Cylindre PostgreSQL (jamais une grosse boîte à listes)."""
    rx, ry, h = 15, 5, 24
    s = (f'<ellipse cx="{cx}" cy="{top+h}" rx="{rx}" ry="{ry}" fill="var(--rds)"/>'
         f'<rect x="{cx-rx}" y="{top}" width="{2*rx}" height="{h}" fill="var(--rds)"/>'
         f'<line x1="{cx-rx}" y1="{top}" x2="{cx-rx}" y2="{top+h}" stroke="var(--rds)"/>'
         f'<line x1="{cx+rx}" y1="{top}" x2="{cx+rx}" y2="{top+h}" stroke="var(--rds)"/>'
         f'<ellipse cx="{cx}" cy="{top+12}" rx="{rx}" ry="{ry}" fill="#7badde" stroke="var(--rds)"/>'
         f'<ellipse cx="{cx}" cy="{top}" rx="{rx}" ry="{ry}" fill="#9cc2e8" stroke="var(--rds)"/>'
         f'<text class="tm" x="{cx}" y="{top+h+20}" text-anchor="middle" style="fill:var(--rds)">{esc(label_txt)}</text>')
    if sub:
        s += f'<text class="s" x="{cx}" y="{top+h+36}" text-anchor="middle" style="fill:var(--muted)">{esc(sub)}</text>'
    return s


def dashed_in(cx, y_from, y_to, text, mid="ae", lx=None, ly=None):
    """Entrée d'un flux externe : flèche tiretée verticale (par le haut) + libellé."""
    s = A([(cx, y_from), (cx, y_to)], mid=mid, dash=True)
    lx = cx + 33 if lx is None else lx
    ly = (y_from + y_to) / 2 if ly is None else ly
    s += label(lx, ly, text, anchor="start")
    return s


def roundtrip(a, b, out_label, back_label, mid="ae", gap=16, color="var(--muted)"):
    """Double flèche entre deux points (un composant qui TIRE la donnée).
    a = source (ex. appelant/BFF), b = cible. out = a->b (demande), back = b->a (donnée).
    Horizontal si a et b sont à la même hauteur ; sinon vertical."""
    (ax, ay), (bx, by) = a, b
    s = []
    if abs(ay - by) <= abs(ax - bx):  # orientation horizontale
        s.append(A([(ax, ay - gap / 2), (bx, by - gap / 2)], color, mid))
        s.append(label((ax + bx) / 2, min(ay, by) - gap / 2 - 6, out_label))
        s.append(A([(bx, by + gap / 2), (ax, ay + gap / 2)], color, mid))
        s.append(label((ax + bx) / 2, max(ay, by) + gap / 2 + 12, back_label))
    else:  # orientation verticale
        s.append(A([(ax - gap / 2, ay), (bx - gap / 2, by)], color, mid))
        s.append(label(min(ax, bx) - gap / 2 - 6, (ay + by) / 2, out_label, anchor="end"))
        s.append(A([(bx + gap / 2, by), (ax + gap / 2, ay)], color, mid))
        s.append(label(max(ax, bx) + gap / 2 + 6, (ay + by) / 2, back_label, anchor="start"))
    return "".join(s)


def marker(mid):
    """Définition de la pointe de flèche (id UNIQUE par vue)."""
    return (f'<defs><marker id="{mid}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" '
            'markerHeight="7" orient="auto-start-reverse"><path d="M2 2 L8 5 L2 8" fill="none" '
            'stroke="context-stroke" stroke-width="1.8" stroke-linecap="round" '
            'stroke-linejoin="round"/></marker></defs>')


def svg(view_box, body, mid="ae", aria=""):
    """Enveloppe <svg> d'une vue, marqueur inclus (id unique à fournir)."""
    vb = " ".join(str(v) for v in view_box)
    return (f'<svg viewBox="{vb}" role="img" aria-label="{esc(aria)}">{marker(mid)}{body}</svg>')


# ---- assemblage d'une page complète (utile pour un fork) ----
_STYLE = """
:root{--bg:#f6f7f9;--surface:#fff;--s2:#eef1f5;--line:#d7dde6;--ink:#1a2330;--muted:#5b6673;
--sai:#2f6ff0;--grn:#1f9d55;--amb:#b0781a;--soc:#FF5757;--kc:#6a57d6;--rds:#2e73b8;--s3:#e2571e;
--sai-bg:#eaf1fe;--grn-bg:#e9f6ee;--kc-bg:#efecfb;--mono:"IBM Plex Mono",ui-monospace,monospace;
--sans:"IBM Plex Sans",system-ui,sans-serif;color-scheme:light;}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f141b;--surface:#19212c;
--s2:#141b24;--line:#2a3542;--ink:#e7edf5;--muted:#9aa7b6;--sai-bg:#132238;--grn-bg:#102a1c;
--kc-bg:#1d1836;color-scheme:dark;}}
:root[data-theme="dark"]{--bg:#0f141b;--surface:#19212c;--s2:#141b24;--line:#2a3542;--ink:#e7edf5;
--muted:#9aa7b6;--sai-bg:#132238;--grn-bg:#102a1c;--kc-bg:#1d1836;color-scheme:dark;}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);margin:0;padding:clamp(16px,4vw,40px)}
.bar{display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap}
#home{font:600 13px var(--mono);color:var(--sai);background:var(--s2);border:1px solid var(--line);border-radius:8px;padding:6px 10px;cursor:pointer}
#trail{color:var(--muted);font:12px var(--mono)}
.view .back{font:600 12px var(--mono);color:var(--sai);background:var(--s2);border:1px solid var(--line);border-radius:8px;padding:5px 9px;cursor:pointer;margin-bottom:8px}
svg{width:100%;height:auto;max-width:100%}
.box{fill:var(--surface);stroke:var(--line);stroke-width:1.3}
.zone{fill:var(--s2);stroke:var(--line);stroke-width:1.2;stroke-dasharray:5 5;opacity:.9}
.flow{stroke:var(--sai);stroke-width:2.2;fill:none;stroke-dasharray:7 7}
.arr{stroke:var(--muted);stroke-width:1.6;fill:none}
.zoom{fill:none;stroke:var(--muted);stroke-width:1.2}
text{font-family:var(--sans)}.t{fill:var(--ink);font-weight:700;font-size:14px}
.tm{fill:var(--ink);font-weight:600;font-size:13px}.s{fill:var(--muted);font-size:11px}
.lbl{fill:var(--muted);font-size:11px;font-family:var(--mono)}
[hidden]{display:none!important}
"""

_NAV = """(function(){var names=__NAMES__,trail=document.getElementById("trail"),cur="__OV__",hist=[];
function render(id){document.querySelectorAll(".view").forEach(function(v){v.hidden=(v.id!=="v-"+id);});
trail.innerHTML=id==="__OV__"?"":'<span>&rsaquo;</span> '+(names[id]||id);cur=id;try{scrollTo(0,0);}catch(e){}}
function go(id){if(id!==cur)hist.push(cur);render(id);}function back(){render(hist.length?hist.pop():"__OV__");}
document.querySelectorAll("[data-go]").forEach(function(b){b.addEventListener("click",function(){go(b.getAttribute("data-go"));});});
document.querySelectorAll("[data-back]").forEach(function(b){b.addEventListener("click",back);});
var h=document.getElementById("home");if(h)h.addEventListener("click",function(){hist=[];render("__OV__");});
try{var L=window.LOGOS||{};document.querySelectorAll('image[data-logo]').forEach(function(im){var k=im.getAttribute('data-logo');
if(L[k]){im.setAttributeNS('http://www.w3.org/1999/xlink','href',L[k]);im.setAttribute('href',L[k]);}});}catch(e){}
render("__OV__");})();"""


def shell(title, overview, views, names, logos):
    """Assemble une page complète. views = [(id, svg_html)], names = {id: libellé}, logos = {clé: dataURI}."""
    import json
    parts = []
    for vid, body in views:
        back = '' if vid == overview else '<button class="back" data-back>&lsaquo; Retour</button>'
        parts.append(f'<div class="view" id="v-{vid}" hidden>{back}{body}</div>')
    nav = _NAV.replace("__NAMES__", json.dumps(names, ensure_ascii=False)).replace("__OV__", overview)
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{esc(title)}</title><style>{_STYLE}</style></head><body>'
            f'<div class="bar"><span id="home">⌂ {esc(title)}</span><span id="trail"></span></div>'
            f'<div class="stage">{"".join(parts)}</div>'
            f'<script>window.LOGOS={json.dumps(logos, ensure_ascii=False)};</script>'
            f'<script>{nav}</script></body></html>')
