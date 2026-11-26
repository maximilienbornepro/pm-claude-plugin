#!/usr/bin/env python3
"""dossier_skin - second gabarit HTML du schéma d'architecture, à la charte du dossier projet.

Le rendu de référence (golden.py, style gh-pages) reste tel quel. Ce gabarit l'habille à la charte des
slides (skin `slide-style`) : fond ivoire, logo du client, sur-titre, titre court, légende, typo sans
empattement légère, aplats sans ombre. En dessous : la vue macro (vue d'ensemble), toujours cliquable vers
les sous-vues, comme dans le rendu de référence.

    python3 dossier_skin.py <mission> -o sortie.html [--logo chemin.png]

Fournit aussi `overview_svg(model)` : le SVG de la vue macro, logos résolus, réutilisé par le générateur
`dossier` (slide PowerPoint) et par la maquette HTML. Lecture seule côté mission : n'écrit que la sortie.
"""
import base64
import json
import mimetypes
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import golden  # noqa: E402

# Golden CSS variables remapped to the dossier charter (one meaning = one colour, flat, light).
SKIN = {
    "bg": "#F7F4EF", "surface": "#FFFFFF", "s2": "#F1ECE5", "ink": "#1A1A1A", "muted": "#8A8580", "line": "#D9D3CA",
    "sai": "#1A1A1A", "sai-bg": "#ECE6DD", "grn": "#6E8B63", "grn-bg": "#EEF1EA", "ext": "#8A8580", "ext-bg": "#F1ECE5",
    "air": "#5E6670", "air-bg": "#ECEEF0", "ksatc": "#7E9A6E", "ksat-bg": "#EEF1EA", "kc": "#7A1F23", "kc-bg": "#F3E7E7",
    "iceye": "#5E6670", "iceye-bg": "#ECEEF0", "s3": "#B8975A", "rds": "#8C7B69", "amb": "#B8975A", "soc": "#7A1F23",
}
SANS = '"Helvetica Neue", "Avenir Next", "Segoe UI", Arial, sans-serif'

CSS = """
:root:not(#_){%(vars)s --sans:%(sans)s; --mono:%(sans)s; color-scheme:light}
body{background:var(--bg);font-family:var(--sans)}
.wrap{max-width:1240px}
.xnav,.xtheme,#skin{display:none!important}
.dh{position:relative;padding:8px 0 22px}
.dh .logo{position:absolute;top:6px;right:0;height:15px}
.dh .eyebrow{font:300 12px var(--sans);letter-spacing:.5em;text-transform:uppercase;color:var(--muted)}
.dh h1{font:200 34px/1.15 var(--sans);letter-spacing:0;margin:10px 0 0;color:var(--ink)}
.dh .cap{font:200 14px/1.6 var(--sans);color:#5a5550;max-width:900px;margin:10px 0 0}
.crumb{margin:4px 0 14px}.crumb button{color:var(--ink);font-weight:300;letter-spacing:.08em}
.crumb button:hover{background:var(--sai-bg)}
.back{background:var(--sai-bg);color:var(--ink);font-weight:300}
.stage{background:transparent;border:0;border-top:1px solid var(--line);border-radius:0;padding:18px 0 0}
svg text{font-family:var(--sans)}
.t{font-weight:400;font-size:15px}.tm{font-weight:400;font-size:13.5px}.s{font-weight:300}
.lbl,.lsai,.lkc{font-family:var(--sans);font-weight:300;letter-spacing:.06em}
.blk rect.bg,.box{filter:none!important;stroke-width:1!important}
.blk rect.bg{stroke:var(--line)}
.flow{animation:none;stroke-width:2}
.df{display:flex;flex-wrap:wrap;gap:12px 28px;justify-content:space-between;margin-top:26px;padding-top:14px;border-top:1px solid var(--line);
  font:300 11px var(--sans);letter-spacing:.4em;text-transform:uppercase;color:var(--muted)}
.df a{color:var(--ink);text-decoration:none;letter-spacing:.1em;text-transform:none;border-bottom:1px solid #B8975A}
"""

CAPTION = ("Le schéma présente l'architecture de la solution dans sa vue d'ensemble : les blocs regroupent les "
           "services par zone (compte cloud, cluster, partenaires, exploitation) et les flèches suivent les flux, "
           "en trait plein pour le chemin principal. Chaque bloc marqué d'une loupe ouvre une vue détaillée.")


def data_uri(path):
    p = Path(path)
    if not p.exists():
        return None
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def _logos(model):
    L = dict(golden._library_logos() or {})
    L.update(model.get("logos") or {})
    return L


def overview_svg(model):
    """SVG of the macro view (golden), with logos inlined as href."""
    page = golden.build_page(model)
    i = page.index('id="v-overview"')
    a = page.index("<svg", i)
    b = page.index("</svg>", a) + 6
    svg = page[a:b]
    L = _logos(model)

    def put(m):
        k = m.group(1)
        return f'<image href="{L[k]}" data-logo="{k}"' if k in L else m.group(0)
    return re.sub(r'<image data-logo="([^"]+)"', put, svg)


def page(model, logo_uri=None, project="", title="Architecture", eyebrow="Architecture · Vue d'ensemble",
         cap=CAPTION, src_label="", src_href="", foot_right=""):
    html = golden.build_page(model)
    html = re.sub(r"<title>.*?</title>", f"<title>{golden.esc(project)} · {golden.esc(title)}</title>", html, count=1, flags=re.S)
    vars_ = "".join(f"--{k}:{v};" for k, v in SKIN.items())
    html = html.replace("</head>", f"<style>{CSS % {'vars': vars_, 'sans': SANS}}</style></head>", 1)
    logo = f'<img class="logo" src="{logo_uri}" alt="Logo client">' if logo_uri else ""
    head = (f'<header class="dh">{logo}<div class="eyebrow">{golden.esc(eyebrow)}</div>'
            f'<h1>{golden.esc(title)}</h1><p class="cap">{golden.esc(cap)}</p></header>')
    html = html.replace('<div class="wrap">', '<div class="wrap">' + head, 1)
    link = f'<a href="{golden.esc(src_href)}">Source · {golden.esc(src_label)} ↗</a>' if src_label else ""
    foot = f'<footer class="df"><span>{golden.esc(project)} · Architecture</span>{link}<span>{golden.esc(foot_right)}</span></footer>'
    k = html.rindex("</div>", 0, html.index("window.LOGOS"))
    return html[:k] + foot + html[k:]


def main(argv):
    if not argv or argv[0].startswith("-") or "-o" not in argv:
        print(__doc__)
        return 2
    import profile as prof  # noqa: E402
    mission = argv[0]
    mdir = Path(prof.mission_dir(mission))
    model = json.loads((mdir / "architecture" / "model.json").read_text(encoding="utf-8"))
    logo = argv[argv.index("--logo") + 1] if "--logo" in argv else mdir / "logos" / "client-noir-texte.png"
    out = Path(argv[argv.index("-o") + 1])
    project = (model.get("meta") or {}).get("project", mission)
    out.write_text(page(model, data_uri(logo), project=project), encoding="utf-8")
    print(f"ok : {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
