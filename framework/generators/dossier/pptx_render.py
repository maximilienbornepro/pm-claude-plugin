"""pptx_render - dossier.json -> PowerPoint natif, éditable à la main et relisible par pptx_sync.

Règles d'édition (pour que les retouches à la main remontent dans dossier.json puis le HTML) :
- titre de chaque slide = espace réservé de titre (plan, sommaire, accessibilité) ; légende = espace
  réservé de texte ; sur-titre, sources, valeurs = zones de texte nommées `dx:<rôle>` ;
- tableaux = tableaux PowerPoint natifs (`dx:table`) ;
- barres d'avancement = deux formes, `dx:track:<i>` (rail) et `dx:bar:<i>` (remplissage) : étirer la barre
  change le pourcentage ;
- burn-down = graphique natif (Données du graphique modifiables) ;
- Gantt, jalons, matrice des risques = formes nommées que l'on déplace ou étire ;
- weekly = vraies puces à niveaux.
La slide est retrouvée par le nom de son titre : `dx:slide:<id>`.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
import slides as S  # noqa: E402
from pptx.chart.data import XyChartData  # noqa: E402
from pptx.enum.chart import XL_CHART_TYPE  # noqa: E402
from pptx.enum.dml import MSO_LINE_DASH_STYLE  # noqa: E402
from pptx.opc.constants import RELATIONSHIP_TYPE as RT  # noqa: E402
from pptx.oxml.ns import qn  # noqa: E402
from pptx.util import Pt  # noqa: E402
from lxml import etree  # noqa: E402

X0, XW = 6.0, 88.0
FOOT_Y = 52.4
EXT = (".xlsx", ".pptx", ".drawio", ".html", ".md", ".json", ".yml")
# Shared geometry (pptx_sync inverts it)
GANTT = dict(gx_off=13.0, gw_off=14.0, lane_h=3.7)
CHART_INNER = dict(x=.06, y=.08, w=.92, h=.78)  # plot area inside the chart frame (fractions)


def slide_ids(deck):
    """Stable id per slide: its `id`, else cover / section-<k>."""
    out, k = [], 0
    for sl in deck["slides"]:
        if sl.get("id"):
            out.append(sl["id"])
        elif sl["kind"] == "cover":
            out.append("cover")
        else:
            k += 1
            out.append(f"section-{k}")
    return out


def agenda(deck):
    """[(section title, num, [(slide id, title)])] ; content before the first section goes under « Synthèse »."""
    ids = slide_ids(deck)
    out, cur = [], ["Synthèse", "", []]
    for sid, sl in zip(ids, deck["slides"]):
        if sl["kind"] == "cover":
            continue
        if sl["kind"] == "section":
            if cur[2]:
                out.append(tuple(cur))
            cur = [sl["title"].replace("\n", " "), sl.get("num", ""), []]
        else:
            cur[2].append((sid, sl.get("title", "")))
    if cur[2]:
        out.append(tuple(cur))
    return out


# ── chrome ────────────────────────────────────────────────────────────────────
def chrome(D, s, sl, deck, n, dark):
    project = sl.get("project") or deck.get("project", "")
    if dark:
        if sl["kind"] != "cover":
            D.picture(s, D.logo("dark"), 8, 3.4, h=4.2)
    else:
        lg = D.logo("light")
        if lg and lg.exists():
            from PIL import Image
            iw, ih = Image.open(lg).size
            D.picture(s, lg, 96 - 1.15 * iw / ih, 3.2, h=1.15)
    gray = "6D6862" if dark else "gris"
    D.text(s, 4, FOOT_Y, 30, 1.2, f"{project} · {sl.get('section', '')}", size=.85, color=gray, caps=True, spacing=3.2, name="dx:foot")
    D.text(s, 86, FOOT_Y, 10, 1.2, f"{n:02d}", size=.85, color=gray, align="r", spacing=3.2, name="dx:num")
    if sl.get("src"):
        first = sl["src"].split(" · ")[0].strip()
        link = first if Path(first).suffix in EXT else None
        D.text(s, 22, FOOT_Y, 56, 1.2, [[(f"Source · {sl['src']} ↗", {"link": link})]], size=.85, color="encre", align="c",
               spacing=1.2, name="dx:src")


def header(D, s, sl, sid):
    D.text(s, X0, 4.4, 80, 1.2, sl.get("eyebrow", ""), size=.95, color="gris", caps=True, spacing=4.5, name="dx:eyebrow")
    D.placeholder(s, 0, X0, 5.9, 80, 3.0, sl.get("title", ""), size=2.4, color="encre", name=f"dx:slide:{sid}")
    cap = sl.get("cap", "")
    lines = S.est_lines(cap, 82, .98)
    D.placeholder(s, 1, X0, 9.4, 82, lines * 1.55, cap, size=.98, color="cap", line=1.25, name="dx:cap")
    return 9.4 + lines * 1.52 + 1.6


def legend(D, s, items, y):
    x = X0
    for kind, label in items:
        k, _, v = kind.partition(":")
        if k == "st":
            D.oval(s, x + .4, y + .55, .38, S.STATUS[v]); x += 1.2
        elif k == "pill":
            D.rect(s, x, y + .2, .75, .75, S.PILL[v][0]); x += 1.2
        elif k == "raci":
            D.rect(s, x, y + .2, .75, .75, S.RACI[v][0]); x += 1.2
        elif k in ("line", "dash"):
            D.line(s, x, y + .6, x + 1.8, y + .6, color=v, w=1.5, dash=(k == "dash")); x += 2.3
        elif k == "star":
            D.text(s, x, y, 1, 1.2, "★", size=.9, color="or"); x += 1.1
        elif k == "badge":
            D.oval(s, x + .45, y + .55, .45, "noir"); x += 1.3
        D.text(s, x, y + .05, 40, 1.2, label, size=.72, color="gris", caps=True, spacing=1.8)
        x += len(label) * .62 + 2.2


# ── tables ────────────────────────────────────────────────────────────────────
def cell_of(v, colspec, size, total=False):
    align = colspec.get("align", "l")
    fill, runs, overlay = None, [], None
    if not isinstance(v, dict):
        v = {"t": str(v)}
    t = v.get("t", "")
    color = v.get("c") or ("gris" if v.get("muted") else ("3A3633" if v.get("light") else "encre"))
    if "pill" in v:
        fill, fg = S.PILL[v["pill"]]
        runs = [(t, {"caps": True, "spacing": 1.6, "size": size * .76, "color": fg, "font": S.F_REG})]
    elif "dot" in v:
        runs = [("● ", {"color": S.LEVEL[v["dot"]], "size": size * 1.1}), (t, {"color": color})]
    elif "raci" in v:
        fill, fg = S.RACI[v["raci"]]
        runs, align = [(v["raci"], {"color": fg, "font": S.F_REG})], "c"
    elif "heat" in v:
        h = v["heat"]
        fill = S.HEAT.get(h, S.C["taupe"] if h < 2 else S.C["ardoise"])
        runs, align = [(t, {"color": "gris" if h == 0 else "encre"})], "c"
    elif "st" in v:
        runs, align = [("●", {"color": S.STATUS[v["st"]], "size": size * 1.5})], "c"
    elif "bar" in v:
        runs, align, overlay = [(f"{v['bar']} %", {})], "r", ("bar", v["bar"])
    elif "stack" in v:
        overlay = ("stack", v["stack"])
    else:
        runs = [(p, {"color": color, "bold": b or total}) for p, b in S.runs_of(t)] if t else []
        if v.get("star"):
            runs.append(("  ★", {"color": "or"}))
    cell = {"runs": runs, "align": v.get("align", align), "fill": fill}
    if total:
        cell["tline"] = ("encre", 1.0); cell["bline"] = None
    return cell, overlay


def render_table(D, s, tab, y, size=.95, small=False, x=None, w=None, row_lines=None):
    x = X0 if x is None else x
    w = XW if w is None else w
    cols = tab["cols"]
    size = min(size, .88) if small else size
    rows, overlays = [], []
    cur = tab.get("current_col")
    for i, r in enumerate(tab["rows"]):
        row = []
        for j, v in enumerate(r):
            c, ov = cell_of(v, cols[j], size)
            row.append(c)
            if ov:
                overlays.append((i, j, ov))
        rows.append(row)
    for key in ("total", "total2"):
        if tab.get(key):
            rows.append([cell_of(v, cols[j], size, total=(key == "total"))[0] for j, v in enumerate(tab[key])])
            if key == "total2":
                for c in rows[-1]:
                    for k, (t, o) in enumerate(c["runs"]):
                        c["runs"][k] = (t, dict(o, color="gris", bold=False))
                    c["bline"] = None
    head = not tab.get("nohead")
    gf, tops, heights, lefts, widths = D.table(s, x, y, w, cols, rows, size=size, head=head,
                                               row_pad=.55 if small else .8, name="dx:table")
    if head:
        for j, c in enumerate(cols):
            cell = gf.table.cell(0, j)
            if c.get("key"):
                p = cell.text_frame.paragraphs[0]
                r = p.add_run(); r.text = "● "; r.font.color.rgb = S.rgb(S.PILL[c["key"]][0]); r.font.size = Pt(S.pt_of(size))
                p.runs[0]._r.addprevious(p.runs[-1]._r)
            if cur is not None and j == cur:
                from pptx.enum.text import MSO_ANCHOR
                cell.fill.solid(); cell.fill.fore_color.rgb = S.rgb("noir")
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                cell.margin_top = cell.margin_bottom = S.cq(.45)
                gf.table.rows[0].height = S.cq(2.6)
                for r in cell.text_frame.paragraphs[0].runs:
                    r.font.color.rgb = S.rgb("blanc")
    off = 1 if head else 0
    for i, j, (k, v) in overlays:
        top, h = tops[i + off], heights[i + off]
        cx, cw = lefts[j] + .8, widths[j] - 1.6
        if k == "bar":
            bw = cw * .58
            D.rect(s, cx, top + h / 2 - .42, bw, .84, "voile", name=f"dx:track:{i}")
            D.rect(s, cx, top + h / 2 - .42, max(bw * v / 100, .15), .84, "encre", name=f"dx:bar:{i}")
        elif k == "stack":
            xx = cx
            for key, frac in v:
                if frac > 0:
                    D.rect(s, xx, top + h / 2 - .3, cw * frac, .6, S.PILL[key][0], name=f"dx:stack:{i}:{key}"); xx += cw * frac
    return tops[-1] + heights[-1]


# ── slide kinds ───────────────────────────────────────────────────────────────
def k_table(D, s, sl, y):
    y = render_table(D, s, sl["table"], y, small=sl.get("small"), size=sl.get("size", .95))
    if sl.get("note"):
        D.text(s, X0, y + 1, 80, 1.4, sl["note"], size=.88, color="gris", name="dx:note"); y += 2.4
    return y


def tiles(D, s, items, x, y, w, h, vsize=4.4, vertical=False):
    for i, t in enumerate(items):
        fill = t.get("c", "sable")
        fg = "blanc" if fill in ("noir", "bordeaux") else "encre"
        tx, ty = (x, y + i * h) if vertical else (x + i * w, y)
        D.rect(s, tx, ty, w, h, fill, name=f"dx:tile:{i}")
        D.text(s, tx + 1.8, ty + 1.6, w - 3.6, 1.2, t["k"], size=.75, color=fg, caps=True, spacing=3.4, font=S.F_REG, name=f"dx:tile:{i}:k")
        D.text(s, tx + 1.8, ty + h - vsize * 1.05 - (2.4 if t.get("s") else 1.2), w - 3.6, vsize * 1.2, t["v"], size=vsize, color=fg,
               font=S.F_THIN, name=f"dx:tile:{i}:v")
        if t.get("s"):
            D.text(s, tx + 1.8, ty + h - 2.4, w - 3.6, 1.2, t["s"], size=.9, color=fg, name=f"dx:tile:{i}:s")


def k_tiles_table(D, s, sl, y):
    tiles(D, s, sl["tiles"], X0, y, XW / 4, 10.5)
    return render_table(D, s, sl["table"], y + 12.5, small=True)


def k_progress(D, s, sl, y):
    y0 = y + 2
    D.text(s, X0, y0, 30, 12, [[(sl["kpi"], {"size": 11, "font": S.F_THIN}), (sl.get("unit", ""), {"size": 2.6})]], size=11, line=.9, name="dx:kpi")
    D.text(s, X0, y0 + 12.5, 30, 4, sl.get("lead", ""), size=1.25, color="texte", line=1.3, name="dx:lead")
    bx, bw = 42, 50
    yy = y0 + .5
    for i, b in enumerate(sl["bars"]):
        D.text(s, bx, yy + .3, 8, 1.4, b["l"], size=.92, caps=True, spacing=2.4, name=f"dx:plabel:{i}")
        tx = bx + 9.5
        D.rect(s, tx, yy, bw - 15, 1.9, "voile", name=f"dx:track:{i}")
        D.rect(s, tx, yy, max((bw - 15) * b["p"] / 100, .15), 1.9, b["c"], name=f"dx:bar:{i}")
        if not b.get("time"):
            mx = tx + (bw - 15) * sl["expected"] / 100
            D.line(s, mx, yy - .45, mx, yy + 2.35, color="bordeaux", w=1, name=f"dx:expected:{i}")
        D.text(s, tx + bw - 14, yy + .1, 6, 1.6, b.get("v") or f"{b['p']} %", size=1.4, align="r", name=f"dx:pval:{i}")
        yy += 3.6 if not b.get("time") else 5.2
        if b.get("time"):
            D.text(s, tx, yy - 2.4, 40, 1.2, f"Trait bordeaux : avancement attendu à date ({sl['expected']} %)", size=.82, color="gris")
    return max(yy, y0 + 17)


def _no_fill(el, tag):
    sp = el.find(qn(tag))
    if sp is None:
        sp = etree.SubElement(el, qn(tag))
    for ch in list(sp):
        sp.remove(ch)
    etree.SubElement(sp, qn("a:noFill"))
    ln = etree.SubElement(sp, qn("a:ln")); etree.SubElement(ln, qn("a:noFill"))


def chart(D, s, c, x, y, w, h, big=True):
    """Burn-down as a NATIVE XY chart (data editable in PowerPoint) + named overlays for today / markers."""
    (x0, x1), (y0, y1) = c["x"], c["y"]
    fi = CHART_INNER
    gx, gy, gw, gh = x, y + 1.0, w, h - 1.0
    px = lambda d: gx + gw * (fi["x"] + fi["w"] * (d - x0) / (x1 - x0))  # noqa: E731
    py = lambda v: gy + gh * (fi["y"] + fi["h"] * (1 - (v - y0) / (y1 - y0)))  # noqa: E731
    ex = px(c["elapsed"])
    D.rect(s, px(x0), py(y1), ex - px(x0), py(y0) - py(y1), "voile2", name="dx:elapsed")
    fs = .72 if big else .78
    D.text(s, px(x0), y + .2, ex - px(x0), 1.2, c.get("elapsed_label", ""), size=fs, color="gris", caps=True, spacing=2.2, align="c", name="dx:elapsed_label")
    if c.get("remain_label"):
        D.text(s, ex, y + .2, px(x1) - ex, 1.2, c["remain_label"], size=fs, color="gris", caps=True, spacing=2.2, align="c", name="dx:remain_label")
    cd = XyChartData()
    for name, key in (("Réel", "real"), ("Idéal", "ideal"), ("Tendance", "trend")):
        ser = cd.add_series(name)
        for a, b in c[key]:
            ser.add_data_point(a, b)
    gf = s.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_LINES_NO_MARKERS, S.cq(gx), S.cq(gy), S.cq(gw), S.cq(gh), cd)
    gf.name = "dx:chart"
    ch = gf.chart
    ch.has_legend = False
    ch.font.name = S.F_LIGHT; ch.font.size = Pt(S.pt_of(.72)); ch.font.color.rgb = S.rgb("gris")
    style = {"Réel": ("noir", 2.2, False), "Idéal": ("taupe", 1.0, True), "Tendance": ("noir", 1.2, True)}
    for ser in ch.plots[0].series:
        colr, wd, dash = style[ser.name]
        ser.smooth = False
        ln = ser.format.line
        ln.color.rgb = S.rgb(colr); ln.width = Pt(wd)
        if dash:
            ln.dash_style = MSO_LINE_DASH_STYLE.DASH
    xa, ya = ch.category_axis, ch.value_axis
    xa.minimum_scale, xa.maximum_scale = x0, x1
    xa.major_unit = c["xticks"][1][0] - c["xticks"][0][0] if len(c["xticks"]) > 1 else 1
    ya.minimum_scale, ya.maximum_scale, ya.major_unit = y0, y1, (y1 - y0) / max(1, len(c["yticks"]) - 1)
    for ax in (xa, ya):
        ax.has_major_gridlines = False
        ax.format.line.color.rgb = S.rgb("filet")
        ax.tick_labels.font.size = Pt(S.pt_of(.72)); ax.tick_labels.font.color.rgb = S.rgb("gris")
    xa.tick_labels.number_format = '"J"0'; xa.tick_labels.number_format_is_linked = False
    cs = ch._chartSpace
    pa = cs.find(qn("c:chart")).find(qn("c:plotArea"))
    lay = pa.find(qn("c:layout"))
    if lay is None:
        lay = etree.SubElement(pa, qn("c:layout")); pa.remove(lay); pa.insert(0, lay)
    for chd in list(lay):
        lay.remove(chd)
    ml = etree.SubElement(lay, qn("c:manualLayout"))
    for tag, val in (("c:layoutTarget", "inner"), ("c:xMode", "edge"), ("c:yMode", "edge"),
                     ("c:x", fi["x"]), ("c:y", fi["y"]), ("c:w", fi["w"]), ("c:h", fi["h"])):
        etree.SubElement(ml, qn(tag)).set("val", str(val))
    _no_fill(pa, "c:spPr")
    sp = cs.find(qn("c:spPr"))
    if sp is None:
        sp = etree.Element(qn("c:spPr")); cs.find(qn("c:chart")).addnext(sp)
    for chd in list(sp):
        sp.remove(chd)
    etree.SubElement(sp, qn("a:noFill")); ln = etree.SubElement(sp, qn("a:ln")); etree.SubElement(ln, qn("a:noFill"))
    for d, lab in c.get("xdates", []):
        D.text(s, px(d) - 2, py(y0) + 2.0, 4, 1.1, lab, size=.66, color="gris", align="c")
    for i, v in enumerate(c.get("vlines", [])):
        X = px(v["x"])
        D.line(s, X, py(y1), X, py(y0), color=v["c"], w=1.1, name=f"dx:vline:{i}")
        D.text(s, X - 12.3, py(y1) + 2.2 + 1.6 * i, 12, 1.2, v["label"], size=.72, color=v["c"] if v["c"] != "sauge" else "ardoise",
               caps=True, spacing=1.6, align="r", name=f"dx:vlabel:{i}")
    t = c["today"]
    D.line(s, ex, py(y1), ex, py(y0), color="bordeaux", w=1, name="dx:today")
    D.oval(s, ex, py(t["y"]), .45, "bordeaux", name="dx:today_dot")
    D.text(s, ex + .8, py(t["y"]) - 1.6, 22, 1.3, t["label"], size=.95 if big else 1.0, color="bordeaux", name="dx:today_label")
    if c.get("end_label"):
        D.text(s, px(x1) - 22, py(c["trend"][-1][1]) - 2, 22, 1.3, c["end_label"], size=.9, color="ardoise", align="r", name="dx:end_label")


def k_burndown(D, s, sl, y):
    h = 50.3 - y
    chart(D, s, sl["chart"], X0, y, XW, h - 2)
    legend(D, s, sl.get("legend", []), y + h - 1.4)
    return y + h


def k_sprint(D, s, sl, y):
    th = (FOOT_Y - 2 - y) / 3
    tiles(D, s, sl["tiles"], X0, y, 28, th, vsize=3.2, vertical=True)
    chart(D, s, sl["chart"], X0 + 30, y, XW - 30, FOOT_Y - 2 - y, big=False)
    return FOOT_Y - 2


def gantt_geom(y, days):
    gx, gw = X0 + GANTT["gx_off"], XW - GANTT["gw_off"]
    return gx, gw, (lambda d: gx + gw * d / days)


def k_gantt(D, s, sl, y):
    g = sl["gantt"]
    gx, gw, px = gantt_geom(y, g["days"])
    for d, lab in g["months"]:
        D.text(s, px(d), y, 12, 1.2, lab, size=.75, color="gris", caps=True, spacing=2.4)
        if d:
            D.line(s, px(d), y, px(d), y + 2.4 + len(g["lanes"]) * GANTT["lane_h"], color="filet")
    for d, lab in g["weeks"]:
        D.text(s, px(d), y + 1.4, 4, 1, lab, size=.66, color="gris")
    ly = y + 3.2
    for i, ln in enumerate(g["lanes"]):
        D.text(s, X0, ly + .55, 12, 1.2, ln["n"], size=.85, caps=True, spacing=1.8, name=f"dx:lane_name:{i}")
        D.rect(s, px(ln["a"]), ly + .5, px(ln["b"]) - px(ln["a"]), 1.6, "sable", name=f"dx:lane:{i}")
        D.rect(s, px(ln["a"]), ly + .5, max(px(ln["done"]) - px(ln["a"]), .1), 1.6, ln["c"], name=f"dx:done:{i}")
        D.line(s, X0, ly + 3.2, X0 + XW, ly + 3.2, color="voile")
        ly += GANTT["lane_h"]
    t = px(g["today"]["d"])
    D.line(s, t, y + 2.4, t, ly + .4, color="bordeaux", w=1, name="dx:today")
    D.text(s, t + .4, ly + .4, 20, 1.2, g["today"]["label"], size=.72, color="bordeaux", caps=True, spacing=1.8, name="dx:today_label")
    for i, m in enumerate(g["milestones"]):
        X = px(m["d"])
        D.diamond(s, X, ly + 1.0, .55, m["c"], name=f"dx:ms:{i}")
        D.text(s, X - 10.8, ly + 1.8, 10, 1.2, m["label"], size=.72, color=m["c"], caps=True, spacing=1.8, align="r", name=f"dx:mslabel:{i}")
    return ly + 3.4


def k_milestones(D, s, sl, y):
    ly = y + 9
    D.line(s, X0 + 1, ly, X0 + XW - 1, ly, color="encre", w=.75, name="dx:msline")
    D.rect(s, X0 + 1, ly - .55, (XW - 2) * sl["elapsed"], 1.1, "encre", name="dx:mselapsed")
    for i, it in enumerate(sl["items"]):
        X = X0 + 1 + (XW - 2) * it["p"]
        if it["shape"] == "dot":
            D.oval(s, X, ly, .7, it["c"], name=f"dx:ms:{i}")
        else:
            D.diamond(s, X, ly, .8, it["c"], name=f"dx:ms:{i}")
        al = "r" if it["p"] > .9 else "c"
        xx = X - 15 if al == "c" else X - 30 + .8
        D.text(s, xx, ly - 4.2, 30, 1.3, it["top"], size=.85, color="gris", caps=True, spacing=2.6, align=al, name=f"dx:mstop:{i}")
        D.text(s, xx, ly + 2.2, 30, 1.8, it["date"], size=1.35, align=al, name=f"dx:msdate:{i}")
    return ly + 6


def k_meteo(D, s, sl, y):
    n = len(sl["domains"])
    gap, h = .5, 11
    w = (XW - gap * (n - 1)) / n
    for i, d in enumerate(sl["domains"]):
        x = X0 + i * (w + gap)
        fill, fg = S.PILL[d["st"]]
        D.rect(s, x, y, w, h, fill, name=f"dx:dom:{i}")
        D.text(s, x + 1.4, y + 1.5, w - 2.8, 1.2, d["k"], size=.75, color=fg, caps=True, spacing=3.2, font=S.F_REG, name=f"dx:dom:{i}:k")
        D.text(s, x + 1.4, y + 3.8, w - 2.8, 4.5, d["v"], size=1.05, color=fg, line=1.3, name=f"dx:dom:{i}:v")
        bw = w - 2.8
        light = fg in ("blanc", "FFFFFF")
        D.rect(s, x + 1.4, y + h - 1.9, bw, .55, "FFFFFF" if light else "D3CABD", name=f"dx:track:{i}")
        D.rect(s, x + 1.4, y + h - 1.9, max(bw * d["closed"], .1), .55, "blanc" if light else "encre", name=f"dx:bar:{i}")
    legend(D, s, sl.get("legend", []), y + h + 2)
    return y + h + 4


MATRIX = dict(dx=3.0, dy=1.6, cw=9.2, ch=5.3, gap=.35)


def k_matrix(D, s, sl, y):
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    M = MATRIX
    mx, my, cw, ch, gap = X0 + M["dx"], y + M["dy"], M["cw"], M["ch"], M["gap"]
    for r in range(4):
        for c in range(4):
            cx, cy = mx + c * (cw + gap), my + r * (ch + gap)
            D.rect(s, cx, cy, cw, ch, S.LEVEL[sl["grid"][r][c]], name=f"dx:cell:{r}:{c}")
    for r in range(4):
        for c in range(4):
            ids = sl["chips"].get(f"{r},{c}", [])
            cx, cy = mx + c * (cw + gap), my + r * (ch + gap)
            for k, cid in enumerate(ids):
                ox = (k - (len(ids) - 1) / 2) * 2.9
                chip = D.oval(s, cx + cw / 2 + ox, cy + ch / 2, 1.3, "blanc", name=f"dx:chip:{cid}")
                tf = chip.text_frame
                for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
                    setattr(tf, m, 0)
                tf.vertical_anchor = MSO_ANCHOR.MIDDLE
                p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
                rr = p.add_run(); rr.text = cid; rr.font.size = Pt(S.pt_of(.72)); rr.font.name = S.F_REG; rr.font.color.rgb = S.rgb("encre")
    gh = 4 * ch + 3 * gap
    D.text(s, mx, my + gh + .5, 4 * cw + 3 * gap, 1.2, "Impact", size=.78, color="gris", caps=True, spacing=2.4, align="c")
    D.text(s, mx, my - 1.6, 20, 1.2, "Probabilité ↑", size=.72, color="gris", caps=True, spacing=1.8)
    lx, lw = X0 + 44, XW - 44
    yy = y
    for i, it in enumerate(sl["top"]):
        D.text(s, lx, yy + .2, 4, 1.2, it["id"], size=.88, color="gris", spacing=1.6, name=f"dx:top:{i}:id")
        D.text(s, lx + 4.4, yy, lw - 14, 1.6, it["t"], size=1.22, name=f"dx:top:{i}:t")
        D.text(s, lx + 4.4, yy + 1.9, lw - 14, 1.4, it["lev"], size=.88, color="gris", name=f"dx:top:{i}:lev")
        fg = "blanc" if it["lvl"] == "l4" else "encre"
        D.rect(s, lx + lw - 8.5, yy + .1, 8.5, 1.7, S.LEVEL[it["lvl"]], name=f"dx:top:{i}:pill")
        D.text(s, lx + lw - 8.5, yy + .45, 8.5, 1.1, it["lt"], size=.72, color=fg, caps=True, spacing=1.8, align="c", font=S.F_REG, name=f"dx:top:{i}:lt")
        D.line(s, lx, yy + 4.6, lx + lw, yy + 4.6, color="filet")
        yy += 5.6
    return max(my + gh + 2, yy)


def k_diagram(D, s, sl, y):
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    g = sl["diagram"]
    avail_h = (FOOT_Y - 1.2 - y) - (2.2 if sl.get("legend") else 0)
    k = min(XW / g["w"], avail_h / g["h"])
    ox = X0 + (XW - g["w"] * k) / 2
    P = lambda a, b: (ox + a * k, y + b * k)  # noqa: E731
    for i, ln in enumerate(g["links"]):
        dash = ln.get("dash", False)
        color = ln.get("c") or ("gris" if dash else "encre")
        sh = D.poly(s, [P(a, b) for a, b in ln["p"]], color=color, w=1, dash=dash, start=ln.get("start", False), end=ln.get("end", False))
        sh.name = f"dx:link:{i}"
    for i, (lx, ly, t) in enumerate(g.get("labels", [])):
        X, Y = P(lx, ly)
        D.text(s, X, Y - .9, 24, 1.2, t, size=.78, color="ardoise", name=f"dx:label:{i}")
    for i, b in enumerate(g["boxes"]):
        X, Y = P(b["x"], b["y"])
        w, h = b["w"] * k, b["h"] * k
        fill = b.get("fill")
        line = (b.get("color") if b.get("color") not in (None, "encre") else "encre") if b.get("outline") else None
        box = D.rect(s, X, Y, w, h, fill, line=line, lw=1.1, name=f"dx:box:{i}")
        fg = b.get("color", "encre")
        tf = box.text_frame
        for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, m, 0)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE; tf.word_wrap = True
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = b["n"]; r.font.size = Pt(S.pt_of(1.15)); r.font.name = S.F_LIGHT; r.font.color.rgb = S.rgb(fg)
        if b.get("s"):
            p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.CENTER
            r2 = p2.add_run(); r2.text = b["s"]; r2.font.size = Pt(S.pt_of(.8)); r2.font.name = S.F_LIGHT; r2.font.color.rgb = S.rgb(fg)
        if b.get("badge") is not None:
            D.oval(s, X + w - .9, Y + .9, .65, "or" if fill == "noir" else "noir", name=f"dx:badge:{i}")
            D.text(s, X + w - 1.55, Y + .4, 1.3, 1, str(b["badge"]), size=.72, color="blanc", align="c", font=S.F_REG, name=f"dx:badge:{i}:n")
    if sl.get("legend"):
        legend(D, s, sl["legend"], FOOT_Y - 3.0)
    return FOOT_Y - 1


def k_gate(D, s, sl, y):
    D.text(s, X0, y, 22, 9, [[(sl["kpi"], {"size": 8.4, "font": S.F_THIN}), (sl["of"], {"size": 3.4, "color": "gris"})]], size=8.4, line=.9, name="dx:kpi")
    D.text(s, X0, y + 10, 22, 3, sl["lead"], size=1.2, color="texte", name="dx:lead")
    return render_table(D, s, sl["table"], y, small=True, x=X0 + 26, w=XW - 26)


def weekly_paras(items):
    """Theme line = level 0 (bold label + text) ; sub-points = level 1 with a real « – » bullet."""
    paras = []
    for it in items:
        runs = [(it["b"] + (" " if it.get("t") else ""), {"bold": True, "size": 1.2})]
        if it.get("t"):
            runs.append((it["t"], {"size": 1.2}))
        paras.append({"runs": runs, "level": 0})
        for sub in it.get("sub", []):
            paras.append({"runs": [(sub, {"size": 1.12, "font": S.F_LIGHT, "color": "3A3633"})], "level": 1, "bullet": "–", "indent": 1.4})
    return paras


def k_weekly(D, s, sl, y):
    ws = [.36, .29, .35]
    x, bottom = X0, y
    for i, (c, wf) in enumerate(zip(sl["cols"], ws)):
        w = XW * wf - 2.4
        hl = S.est_lines(c["h"].upper(), w, .78 * 2.0)
        D.text(s, x, y, w, 1.2 * hl, c["h"], size=.78, caps=True, spacing=3.0, font=S.F_REG, name=f"dx:whead:{i}")
        hy = y + 1.3 * hl + .7
        D.line(s, x, hy, x + w, hy, color="encre", w=.9)
        paras = weekly_paras(c["items"])
        n = sum(S.est_lines("".join(t for t, _ in p["runs"]), w - 1, 1.16) for p in paras)
        D.text(s, x, hy + .8, w, n * 1.8 + 2, paras, size=1.16, line=1.25, para_space=3, name=f"dx:wcol:{i}")
        bottom = max(bottom, hy + .8 + n * 1.8)
        x += XW * wf
    return bottom


def k_mail(D, s, sl, y):
    D.text(s, X0, y, 20, 1, "Objet", size=.72, color="gris", caps=True, spacing=3)
    D.text(s, X0, y + 1.2, XW, 1.4, sl["obj"], size=1.08, font=S.F_REG, name="dx:obj")
    D.line(s, X0, y + 2.9, X0 + XW, y + 2.9, color="encre", w=.9)
    yy = y + 3.6
    D.text(s, X0, yy, XW, 3, sl["intro"], size=1.05, para_space=2, name="dx:intro")
    yy += 3.6
    w = XW / 2 - 1.4
    for i, sj in enumerate(sl["subjects"]):
        cx = X0 + (i % 2) * (XW / 2 + 1.4)
        cy = yy + (i // 2) * 6.2
        D.text(s, cx, cy, w, 6, [[(sj["h"], {"bold": True, "size": 1.1})], sj["s"], sj["n"]], size=1.02, line=1.25, para_space=1, name=f"dx:subj:{i}")
    yy += ((len(sl["subjects"]) + 1) // 2) * 6.2 + .4
    paras = []
    for p in sl["closing"]:
        paras.extend(p.split("\n"))
    D.text(s, X0, yy, XW, 5, paras, size=1.02, para_space=2, name="dx:closing")
    return yy + 5


def k_archi(D, s, sl, y, mdir):
    sys.path.insert(0, str(ROOT / "framework" / "generators" / "archi"))
    import dossier_skin as K  # noqa: E402
    import svg2pptx  # noqa: E402
    model = json.loads((mdir / sl["model"]).read_text(encoding="utf-8"))
    pal = {k: v.lstrip("#") for k, v in K.SKIN.items()}
    svg2pptx.render(D, s, K.overview_svg(model), X0, y, XW, FOOT_Y - 2.6 - y, pal, tempfile.mkdtemp())
    if sl.get("link"):
        D.text(s, X0, FOOT_Y - 2.4, 60, 1.2, [[(sl.get("link_label", "Vue interactive et sous-vues ↗"), {"link": sl["link"]})]],
               size=.8, color="encre", caps=True, spacing=2.2, name="dx:archi_link")
    return FOOT_Y - 1


KINDS = {"table": k_table, "tiles_table": k_tiles_table, "progress": k_progress, "burndown": k_burndown, "sprint": k_sprint,
         "gantt": k_gantt, "milestones": k_milestones, "meteo": k_meteo, "matrix": k_matrix, "diagram": k_diagram,
         "gate": k_gate, "weekly": k_weekly, "mail": k_mail}


def _jump(run, src_slide, dst_slide):
    """Internal hyperlink: clicking the run jumps to another slide."""
    rid = src_slide.part.relate_to(dst_slide.part, RT.SLIDE)
    rPr = run._r.get_or_add_rPr()
    h = etree.SubElement(rPr, qn("a:hlinkClick"))
    h.set(qn("r:id"), rid); h.set("action", "ppaction://hlinksldjump")
    S.plain_link(run)


def agenda_slide(D, deck, by_id, project):
    """« Sommaire » right after the cover: sections (level 0) and their slides (level 1), each a link."""
    s = D.new(layout=1)
    D.text(s, X0, 4.4, 80, 1.2, "Dossier projet · Sommaire", size=.95, color="gris", caps=True, spacing=4.5, name="dx:eyebrow")
    D.placeholder(s, 0, X0, 5.9, 80, 3.0, "Sommaire", size=2.4, color="encre", name="dx:slide:sommaire")
    groups = agenda(deck)
    half = (sum(len(g[2]) + 1 for g in groups) + 1) // 2
    cols, cur, n = [[], []], 0, 0
    for g in groups:
        if n >= half and cur == 0:
            cur = 1
        cols[cur].append(g); n += len(g[2]) + 1

    def paras(gs):
        out = []
        for title, num, items in gs:
            out.append({"runs": [((f"{num}  " if num else "") + title, {"size": 1.25, "font": S.F_REG})], "level": 0})
            for sid, t in items:
                out.append({"runs": [(t, {"size": 1.0, "color": "3A3633"})], "level": 1, "bullet": "–", "indent": 1.4, "left": .3})
        return out
    ph = D.placeholder(s, 1, X0, 11.5, 42, 38, paras(cols[0]), size=1.0, line=1.2, para_space=2, name="dx:agenda:0")
    tb = D.text(s, X0 + 46, 11.5, 42, 38, paras(cols[1]), size=1.0, line=1.2, para_space=2, name="dx:agenda:1")
    for frame, gs in ((ph.text_frame, cols[0]), (tb.text_frame, cols[1])):
        targets = []
        for title, num, items in gs:
            targets.append(None)
            targets.extend(sid for sid, _ in items)
        for para, sid in zip(frame.paragraphs, targets):
            if sid and sid in by_id and para.runs:
                _jump(para.runs[0], s, by_id[sid])
    chrome(D, s, {"section": "Sommaire", "kind": "agenda"}, deck, 2, False)
    return s


def render(deck, mdir, out, only=None):
    mdir = Path(mdir)
    D = S.Deck(mdir, deck.get("logos"))
    ids = slide_ids(deck)
    by_id, warnings = {}, []
    for n, (sid, sl) in enumerate(zip(ids, deck["slides"]), 1):
        if only and sid not in only and str(n) not in only:
            continue
        k = sl["kind"]
        num = n + (1 if n > 1 and not only else 0)  # agenda is slide 2
        if k == "cover":
            s = D.new(dark=True, layout=0)
            lg = D.logo("dark")
            if lg and lg.exists():
                from PIL import Image
                iw, ih = Image.open(lg).size
                D.picture(s, lg, 50 - 10 * iw / ih / 2, 13, h=10)
            D.placeholder(s, 0, 10, 27.5, 80, 4, sl["title"], size=3.6, color="blanc", caps=True, spacing=16, align="c", name=f"dx:slide:{sid}")
            D.line(s, 47, 33.2, 53, 33.2, color="or", w=.75)
            D.placeholder(s, 1, 10, 35, 80, 2, sl["sub"], size=1.5, color="D8D2CA", spacing=2.6, align="c", name="dx:sub")
            chrome(D, s, sl, deck, num, True)
        elif k == "section":
            s = D.new(dark=True, layout=2)
            lines = sl["title"].split("\n")
            ty = 28.1 - len(lines) * 3.1
            D.text(s, 8, ty - 4.2, 70, 1.4, sl.get("kicker", deck.get("kicker", "")), size=1, color="9A948C", caps=True, spacing=5.8, name="dx:kicker")
            D.placeholder(s, 0, 8, ty, 70, len(lines) * 6, lines, size=5, color="blanc", caps=True, spacing=11, line=1.05, name=f"dx:slide:{sid}")
            ry = ty + len(lines) * 6.3 + 1.4
            D.line(s, 8, ry, 14, ry, color="or", w=.75)
            D.placeholder(s, 1, 8, ry + 1.8, 70, 2, sl.get("sub", ""), size=1.5, color="D8D2CA", spacing=2.6, name="dx:sub")
            D.text(s, 60, 18, 32, 18, sl.get("num", ""), size=16, color="1F1F1F", font=S.F_THIN, align="r", name="dx:secnum")
            chrome(D, s, sl, deck, num, True)
        else:
            s = D.new(layout=1)
            y = header(D, s, sl, sid)
            bottom = k_archi(D, s, sl, y, mdir) if k == "archi" else KINDS[k](D, s, sl, y)
            if k == "table" and sl.get("legend"):
                legend(D, s, sl["legend"], bottom + 1.2)
                bottom += 2.6
            if bottom > FOOT_Y - .6:
                warnings.append(f"{sid}: contenu estimé jusqu'à {bottom:.1f} cq (pied de page à {FOOT_Y})")
            chrome(D, s, sl, deck, num, False)
        D.drop_empty_placeholders(s)
        by_id[sid] = s
    if not only:
        ag = agenda_slide(D, deck, by_id, deck.get("project", ""))
        lst = D.prs.slides._sldIdLst
        el = lst[-1]; lst.remove(el); lst.insert(1, el)
        D.drop_empty_placeholders(ag)
    D.save(out)
    return warnings
