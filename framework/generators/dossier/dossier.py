#!/usr/bin/env python3
"""dossier - dossier projet en slides 16:9 depuis UNE source (profiles/<mission>/dossier.json).

Chaque slide est le reflet d'un livrable existant (skill `slide-style`) : titre court, légende qui
explique comment lire la slide, unités en jours, logo du client, lien vers le fichier source.

Usage :
  dossier.py <mission>                      liste des slides + contrôles (lecture seule)
  dossier.py <mission> --pptx out.pptx      deck PowerPoint natif (tableaux éditables, formes)
  dossier.py <mission> --only id1,id2       ne rend que ces slides (avec --pptx)

Écrit UNIQUEMENT le fichier demandé, en local. Le dépôt dans un espace partagé suit le déroulé
Office (framework/generators/_deroule-office.md), après accord.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


prof = _load("pmf_profile", ROOT / "framework" / "lib" / "profile.py")

# Layout constants (cq = 1 % of the slide width)
X0, XW = 6.0, 88.0
FOOT_Y = 52.4


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
            h = 1.15
            D.picture(s, lg, 96 - h * iw / ih, 3.2, h=h)
    gray = "6D6862" if dark else "gris"
    D.text(s, 4, FOOT_Y, 30, 1.2, f"{project} · {sl.get('section', '')}", size=.85, color=gray, caps=True, spacing=3.2)
    D.text(s, 86, FOOT_Y, 10, 1.2, f"{n:02d}", size=.85, color=gray, align="r", spacing=3.2)
    if sl.get("src"):
        first = sl["src"].split(" · ")[0].strip()
        link = first if Path(first).suffix in (".xlsx", ".pptx", ".drawio", ".html", ".md", ".json", ".yml") else None
        D.text(s, 22, FOOT_Y, 56, 1.2, [[(f"Source · {sl['src']} ↗", {"link": link})]], size=.85, color="encre", align="c", spacing=1.2)


def header(D, s, sl):
    D.text(s, X0, 4.4, 80, 1.2, sl.get("eyebrow", ""), size=.95, color="gris", caps=True, spacing=4.5)
    D.text(s, X0, 5.9, 80, 3.0, sl.get("title", ""), size=2.4, color="encre")
    cap = sl.get("cap", "")
    lines = D_est(cap, 82, .98)
    D.text(s, X0, 9.4, 82, lines * 1.55, cap, size=.98, color="cap", line=1.25)
    return 9.4 + lines * 1.52 + 1.6


def D_est(text, w, size):
    from slides import est_lines  # noqa: E402
    return est_lines(text, w, size)


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


# ── cell model -> table runs ──────────────────────────────────────────────────
def cell_of(v, colspec, size, total=False, current=False):
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


def render_table(D, s, tab, y, size=.95, small=False, x=None, w=None):
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
    if head and cur is not None:
        cols = [dict(c) for c in cols]
    gf, tops, heights, lefts, widths = D.table(s, x, y, w, cols, rows, size=size, head=head, row_pad=.55 if small else .8)
    if head:
        # header dot keys (states table) and current column in black
        for j, c in enumerate(cols):
            cell = gf.table.cell(0, j)
            if c.get("key"):
                p = cell.text_frame.paragraphs[0]
                r = p.add_run(); r.text = " ●"; r.font.color.rgb = S.rgb(S.PILL[c["key"]][0]); r.font.size = S.Pt(S.pt_of(size))
                p.runs[0]._r.addprevious(p.runs[-1]._r)
            if cur is not None and j == cur:
                cell.fill.solid(); cell.fill.fore_color.rgb = S.rgb("noir")
                for r in cell.text_frame.paragraphs[0].runs:
                    r.font.color.rgb = S.rgb("blanc")
    off = 1 if head else 0
    for i, j, (k, v) in overlays:
        top, h = tops[i + off], heights[i + off]
        cx, cw = lefts[j] + .8, widths[j] - 1.6
        if k == "bar":
            bw = cw * .58
            D.rect(s, cx, top + h / 2 - .42, bw, .84, "voile")
            D.rect(s, cx, top + h / 2 - .42, max(bw * v / 100, .15), .84, "encre")
        elif k == "stack":
            xx = cx
            for key, frac in v:
                if frac > 0:
                    D.rect(s, xx, top + h / 2 - .3, cw * frac, .6, S.PILL[key][0]); xx += cw * frac
    return tops[-1] + heights[-1]


# ── slide kinds ───────────────────────────────────────────────────────────────
def k_table(D, s, sl, y):
    y = render_table(D, s, sl["table"], y, small=sl.get("small"), size=sl.get("size", .95))
    if sl.get("note"):
        D.text(s, X0, y + 1, 80, 1.4, sl["note"], size=.88, color="gris"); y += 2.4
    return y


def tiles(D, s, items, x, y, w, h, vsize=4.4, vertical=False):
    n = len(items)
    for i, t in enumerate(items):
        fill = t.get("c", "sable")
        fg = "blanc" if fill in ("noir", "bordeaux") else "encre"
        tx, ty = (x, y + i * h) if vertical else (x + i * w, y)
        D.rect(s, tx, ty, w, h, fill)
        D.text(s, tx + 1.8, ty + 1.6, w - 3.6, 1.2, t["k"], size=.75, color=fg, caps=True, spacing=3.4, font=S.F_REG)
        D.text(s, tx + 1.8, ty + h - vsize * 1.05 - (2.4 if t.get("s") else 1.2), w - 3.6, vsize * 1.2, t["v"], size=vsize, color=fg, font=S.F_THIN)
        if t.get("s"):
            D.text(s, tx + 1.8, ty + h - 2.4, w - 3.6, 1.2, t["s"], size=.9, color=fg)


def k_tiles_table(D, s, sl, y):
    tiles(D, s, sl["tiles"], X0, y, XW / 4, 10.5)
    return render_table(D, s, sl["table"], y + 12.5, small=True)


def k_progress(D, s, sl, y):
    y0 = y + 2
    D.text(s, X0, y0, 30, 12, [[(sl["kpi"], {"size": 11, "font": S.F_THIN}), (sl.get("unit", ""), {"size": 2.6})]], size=11, line=.9)
    D.text(s, X0, y0 + 12.5, 30, 4, sl.get("lead", ""), size=1.25, color="texte", line=1.3)
    bx, bw = 42, 50
    yy = y0 + .5
    for b in sl["bars"]:
        D.text(s, bx, yy + .3, 8, 1.4, b["l"], size=.92, caps=True, spacing=2.4)
        tx = bx + 9.5
        D.rect(s, tx, yy, bw - 15, 1.9, "voile")
        D.rect(s, tx, yy, (bw - 15) * b["p"] / 100, 1.9, b["c"])
        if not b.get("time"):
            mx = tx + (bw - 15) * sl["expected"] / 100
            D.line(s, mx, yy - .45, mx, yy + 2.35, color="bordeaux", w=1)
        D.text(s, tx + bw - 14, yy + .1, 6, 1.6, b.get("v") or f"{b['p']} %", size=1.4, align="r")
        yy += 3.6 if not b.get("time") else 5.2
        if b.get("time"):
            D.text(s, tx, yy - 2.4, 40, 1.2, f"Trait bordeaux : avancement attendu à date ({sl['expected']} %)", size=.82, color="gris")
    return max(yy, y0 + 17)


def chart(D, s, c, x, y, w, h, big=True):
    """Burn-down: axes in days, elapsed band, ideal / real / trend, today and vertical markers."""
    (x0, x1), (y0, y1) = c["x"], c["y"]
    px = lambda d: x + 3.5 + (w - 4.5) * (d - x0) / (x1 - x0)  # noqa: E731
    py = lambda v: y + 1.6 + (h - 4.6) * (1 - (v - y0) / (y1 - y0))  # noqa: E731
    ex = px(c["elapsed"])
    D.rect(s, px(x0), y + 1.0, ex - px(x0), h - 4.0, "voile2")
    fs = .72 if big else .78
    D.text(s, px(x0), y + 1.3, ex - px(x0), 1.2, c.get("elapsed_label", ""), size=fs, color="gris", caps=True, spacing=2.2, align="c")
    if c.get("remain_label"):
        D.text(s, ex, y + 1.3, px(x1) - ex, 1.2, c["remain_label"], size=fs, color="gris", caps=True, spacing=2.2, align="c")
    D.line(s, px(x0), py(y0), px(x1), py(y0), color="filet")
    D.line(s, px(x0), py(y1), px(x0), py(y0), color="filet")
    for v in c["yticks"]:
        D.text(s, x, py(v) - .6, 3, 1.2, str(v), size=.72, color="gris", align="r")
    for d, lab in c["xticks"]:
        D.text(s, px(d) - 2, py(y0) + .4, 4, 1.1, lab, size=.72, color="gris", align="c")
    for d, lab in c.get("xdates", []):
        D.text(s, px(d) - 2, py(y0) + 1.5, 4, 1.1, lab, size=.66, color="gris", align="c")
    D.poly(s, [(px(a), py(b)) for a, b in c["ideal"]], color="taupe", w=1, dash=True)
    D.poly(s, [(px(a), py(b)) for a, b in c["real"]], color="noir", w=2.2)
    D.poly(s, [(px(a), py(b)) for a, b in c["trend"]], color="noir", w=1.2, dash=True)
    for v in c.get("vlines", []):
        X = px(v["x"])
        D.line(s, X, y + 1.0, X, py(y0), color=v["c"], w=1.1)
        D.text(s, X - 12.3, y + 3.4 + 1.6 * c["vlines"].index(v), 12, 1.2, v["label"], size=.72, color=v["c"] if v["c"] != "sauge" else "ardoise", caps=True, spacing=1.6, align="r")
    t = c["today"]
    D.line(s, ex, y + 1.0, ex, py(y0), color="bordeaux", w=1)
    D.oval(s, ex, py(t["y"]), .45, "bordeaux")
    D.text(s, ex + .8, py(t["y"]) - 1.6, 22, 1.3, t["label"], size=.95 if big else 1.0, color="bordeaux")
    if c.get("end_label"):
        D.text(s, px(x1) - 22, py(c["trend"][-1][1]) - 2, 22, 1.3, c["end_label"], size=.9, color="ardoise", align="r")


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


def k_gantt(D, s, sl, y):
    g = sl["gantt"]
    gx, gw = X0 + 13, XW - 14
    px = lambda d: gx + gw * d / g["days"]  # noqa: E731
    for d, lab in g["months"]:
        D.text(s, px(d), y, 12, 1.2, lab, size=.75, color="gris", caps=True, spacing=2.4)
        if d:
            D.line(s, px(d), y, px(d), y + 2.4 + len(g["lanes"]) * 3.7, color="filet")
    for d, lab in g["weeks"]:
        D.text(s, px(d), y + 1.4, 4, 1, lab, size=.66, color="gris")
    ly = y + 3.2
    for ln in g["lanes"]:
        D.text(s, X0, ly + .55, 12, 1.2, ln["n"], size=.85, caps=True, spacing=1.8)
        D.rect(s, px(ln["a"]), ly + .5, px(ln["b"]) - px(ln["a"]), 1.6, "sable")
        if ln["done"] > ln["a"]:
            D.rect(s, px(ln["a"]), ly + .5, px(ln["done"]) - px(ln["a"]), 1.6, ln["c"])
        D.line(s, X0, ly + 3.2, X0 + XW, ly + 3.2, color="voile")
        ly += 3.7
    t = px(g["today"]["d"])
    D.line(s, t, y + 2.4, t, ly + .4, color="bordeaux", w=1)
    D.text(s, t + .4, ly + .4, 20, 1.2, g["today"]["label"], size=.72, color="bordeaux", caps=True, spacing=1.8)
    for m in g["milestones"]:
        X = px(m["d"])
        D.diamond(s, X, ly + 1.0, .55, m["c"])
        D.text(s, X - 10.8, ly + 1.8, 10, 1.2, m["label"], size=.72, color=m["c"], caps=True, spacing=1.8, align="r")
    return ly + 3.4


def k_milestones(D, s, sl, y):
    ly = y + 9
    D.line(s, X0 + 1, ly, X0 + XW - 1, ly, color="encre", w=.75)
    D.rect(s, X0 + 1, ly - .55, (XW - 2) * sl["elapsed"], 1.1, "encre")
    for it in sl["items"]:
        X = X0 + 1 + (XW - 2) * it["p"]
        if it["shape"] == "dot":
            D.oval(s, X, ly, .7, it["c"])
        else:
            D.diamond(s, X, ly, .8, it["c"])
        al = "r" if it["p"] > .9 else "c"
        xx = X - 15 if al == "c" else X - 30 + .8
        D.text(s, xx, ly - 4.2, 30, 1.3, it["top"], size=.85, color="gris", caps=True, spacing=2.6, align=al)
        D.text(s, xx, ly + 2.2, 30, 1.8, it["date"], size=1.35, align=al)
    return ly + 6


def k_meteo(D, s, sl, y):
    n = len(sl["domains"])
    gap, h = .5, 11
    w = (XW - gap * (n - 1)) / n
    for i, d in enumerate(sl["domains"]):
        x = X0 + i * (w + gap)
        fill, fg = S.PILL[d["st"]]
        D.rect(s, x, y, w, h, fill)
        D.text(s, x + 1.4, y + 1.5, w - 2.8, 1.2, d["k"], size=.75, color=fg, caps=True, spacing=3.2, font=S.F_REG)
        D.text(s, x + 1.4, y + 3.8, w - 2.8, 4.5, d["v"], size=1.05, color=fg, line=1.3)
        bw = w - 2.8
        D.rect(s, x + 1.4, y + h - 1.9, bw, .55, "FFFFFF" if fg == "FFFFFF" or fg == "blanc" else "D3CABD")
        D.rect(s, x + 1.4, y + h - 1.9, bw * d["closed"], .55, "blanc" if fg in ("blanc", "FFFFFF") else "encre")
    legend(D, s, sl.get("legend", []), y + h + 2)
    return y + h + 4


def k_matrix(D, s, sl, y):
    mx, my, cw, ch, gap = X0 + 3, y + 1.6, 9.2, 5.3, .35
    for r in range(4):
        for c in range(4):
            lv = sl["grid"][r][c]
            cx, cy = mx + c * (cw + gap), my + r * (ch + gap)
            D.rect(s, cx, cy, cw, ch, S.LEVEL[lv])
            ids = sl["chips"].get(f"{r},{c}", [])
            for k, cid in enumerate(ids):
                D.oval(s, cx + cw / 2, cy + ch / 2, 1.3, "blanc")
                D.text(s, cx + cw / 2 - 1.3, cy + ch / 2 - .6, 2.6, 1.2, cid, size=.75, align="c", font=S.F_REG)
    gh = 4 * ch + 3 * gap
    D.text(s, mx, my + gh + .5, 4 * cw + 3 * gap, 1.2, "Impact", size=.78, color="gris", caps=True, spacing=2.4, align="c")
    D.text(s, mx, my - 1.6, 20, 1.2, "Probabilité ↑", size=.72, color="gris", caps=True, spacing=1.8)
    lx, lw = X0 + 44, XW - 44
    yy = y
    for it in sl["top"]:
        D.text(s, lx, yy + .2, 4, 1.2, it["id"], size=.88, color="gris", spacing=1.6)
        D.text(s, lx + 4.4, yy, lw - 14, 1.6, it["t"], size=1.22)
        D.text(s, lx + 4.4, yy + 1.9, lw - 14, 1.4, it["lev"], size=.88, color="gris")
        fill = S.LEVEL[it["lvl"]]
        fg = "blanc" if it["lvl"] == "l4" else "encre"
        D.rect(s, lx + lw - 8.5, yy + .1, 8.5, 1.7, fill)
        D.text(s, lx + lw - 8.5, yy + .45, 8.5, 1.1, it["lt"], size=.72, color=fg, caps=True, spacing=1.8, align="c", font=S.F_REG)
        D.line(s, lx, yy + 4.6, lx + lw, yy + 4.6, color="filet")
        yy += 5.6
    return max(my + gh + 2, yy)


def k_diagram(D, s, sl, y):
    g = sl["diagram"]
    avail_h = (FOOT_Y - 1.2 - y) - (2.2 if sl.get("legend") else 0)
    k = min(XW / g["w"], avail_h / g["h"])
    ox = X0 + (XW - g["w"] * k) / 2
    P = lambda a, b: (ox + a * k, y + b * k)  # noqa: E731
    for ln in g["links"]:
        dash = ln.get("dash", False)
        color = ln.get("c") or ("gris" if dash else "encre")
        D.poly(s, [P(a, b) for a, b in ln["p"]], color=color, w=1, dash=dash, start=ln.get("start", False), end=ln.get("end", False))
    for lx, ly, t in g.get("labels", []):
        X, Y = P(lx, ly)
        D.text(s, X, Y - .9, 24, 1.2, t, size=.78, color="ardoise")
    for b in g["boxes"]:
        X, Y = P(b["x"], b["y"])
        w, h = b["w"] * k, b["h"] * k
        fill = b.get("fill")
        D.rect(s, X, Y, w, h, fill, line=(b.get("color") if b.get("color") != "encre" else "encre") if b.get("outline") else None, lw=1.1)
        fg = b.get("color", "encre")
        sub = b.get("s")
        D.text(s, X, Y + h / 2 - (1.35 if sub else .75), w, 1.4, b["n"], size=1.15, color=fg, align="c")
        if sub:
            D.text(s, X, Y + h / 2 + .25, w, 1.2, sub, size=.8, color=fg, align="c")
        if b.get("badge") is not None:
            D.oval(s, X + w - .9, Y + .9, .65, "or" if fill == "noir" else "noir")
            D.text(s, X + w - 1.55, Y + .4, 1.3, 1, str(b["badge"]), size=.72, color="blanc", align="c", font=S.F_REG)
    if sl.get("legend"):
        legend(D, s, sl["legend"], FOOT_Y - 3.0)
    return FOOT_Y - 1


def k_gate(D, s, sl, y):
    D.text(s, X0, y, 22, 9, [[(sl["kpi"], {"size": 8.4, "font": S.F_THIN}), (sl["of"], {"size": 3.4, "color": "gris"})]], size=8.4, line=.9)
    D.text(s, X0, y + 10, 22, 3, sl["lead"], size=1.2, color="texte")
    return render_table(D, s, sl["table"], y, small=True, x=X0 + 26, w=XW - 26)


def k_weekly(D, s, sl, y):
    cols = sl["cols"]
    ws = [.36, .29, .35]
    x = X0
    bottom = y
    for c, wf in zip(cols, ws):
        w = XW * wf - 2.4
        hl = S.est_lines(c["h"].upper(), w, .78 * 2.0)
        D.text(s, x, y, w, 1.2 * hl, c["h"], size=.78, caps=True, spacing=3.0, font=S.F_REG)
        hy = y + 1.3 * hl + .7
        D.line(s, x, hy, x + w, hy, color="encre", w=.9)
        paras = []
        for it in c["items"]:
            runs = [(it["b"] + (" " if it.get("t") else ""), {"bold": True, "size": 1.2})]
            if it.get("t"):
                runs.append((it["t"], {"size": 1.2}))
            paras.append(runs)
            for sub in it.get("sub", []):
                paras.append([("–  ", {"color": "gris", "size": 1.12}), (sub, {"size": 1.12, "font": S.F_LIGHT, "color": "3A3633"})])
        n = sum(S.est_lines("".join(t for t, _ in p), w - 1, 1.16) for p in paras)
        D.text(s, x, hy + .8, w, n * 1.8 + 2, paras, size=1.16, line=1.25, para_space=3)
        bottom = max(bottom, hy + .8 + n * 1.8)
        x += XW * wf
    return bottom


def k_mail(D, s, sl, y):
    D.text(s, X0, y, 20, 1, "Objet", size=.72, color="gris", caps=True, spacing=3)
    D.text(s, X0, y + 1.2, XW, 1.4, sl["obj"], size=1.08, font=S.F_REG)
    D.line(s, X0, y + 2.9, X0 + XW, y + 2.9, color="encre", w=.9)
    yy = y + 3.6
    D.text(s, X0, yy, XW, 3, sl["intro"], size=1.05, para_space=2)
    yy += 3.6
    w = XW / 2 - 1.4
    for i, sj in enumerate(sl["subjects"]):
        cx = X0 + (i % 2) * (XW / 2 + 1.4)
        cy = yy + (i // 2) * 6.2
        D.text(s, cx, cy, w, 6, [[(sj["h"], {"bold": True, "size": 1.1})], sj["s"], sj["n"]], size=1.02, line=1.25, para_space=1)
    yy += ((len(sl["subjects"]) + 1) // 2) * 6.2 + .4
    paras = []
    for p in sl["closing"]:
        paras.extend(p.split("\n"))
    D.text(s, X0, yy, XW, 5, paras, size=1.02, para_space=2)
    return yy + 5


KINDS = {"table": k_table, "tiles_table": k_tiles_table, "progress": k_progress, "burndown": k_burndown, "sprint": k_sprint,
         "gantt": k_gantt, "milestones": k_milestones, "meteo": k_meteo, "matrix": k_matrix, "diagram": k_diagram,
         "gate": k_gate, "weekly": k_weekly, "mail": k_mail}


def render(deck, logos_dir, out, only=None):
    D = S.Deck(logos_dir, deck.get("logos"))
    warnings = []
    for n, sl in enumerate(deck["slides"], 1):
        if only and sl.get("id") not in only and str(n) not in only:
            continue
        k = sl["kind"]
        if k == "cover":
            s = D.new(dark=True)
            lg = D.logo("dark")
            if lg and lg.exists():
                from PIL import Image
                iw, ih = Image.open(lg).size
                h = 10
                D.picture(s, lg, 50 - h * iw / ih / 2, 13, h=h)
            D.text(s, 10, 27.5, 80, 4, sl["title"], size=3.6, color="blanc", caps=True, spacing=16, align="c")
            D.line(s, 47, 33.2, 53, 33.2, color="or", w=.75)
            D.text(s, 10, 35, 80, 2, sl["sub"], size=1.5, color="D8D2CA", spacing=2.6, align="c")
            chrome(D, s, sl, deck, n, True)
        elif k == "section":
            s = D.new(dark=True)
            title_lines = sl["title"].split("\n")
            ty = 28.1 - len(title_lines) * 3.1
            D.text(s, 8, ty - 4.2, 70, 1.4, sl.get("kicker", deck.get("kicker", "")), size=1, color="9A948C", caps=True, spacing=5.8)
            D.text(s, 8, ty, 70, len(title_lines) * 6, title_lines, size=5, color="blanc", caps=True, spacing=11, line=1.05)
            ry = ty + len(title_lines) * 6.3 + 1.4
            D.line(s, 8, ry, 14, ry, color="or", w=.75)
            D.text(s, 8, ry + 1.8, 70, 2, sl.get("sub", ""), size=1.5, color="D8D2CA", spacing=2.6)
            D.text(s, 60, 18, 32, 18, sl.get("num", ""), size=16, color="1F1F1F", font=S.F_THIN, align="r")
            chrome(D, s, sl, deck, n, True)
        else:
            s = D.new()
            y = header(D, s, sl)
            bottom = KINDS[k](D, s, sl, y)
            if k == "table" and sl.get("legend"):
                legend(D, s, sl["legend"], bottom + 1.2)
                bottom += 2.6
            if bottom > FOOT_Y - .6:
                warnings.append(f"{sl.get('id')}: contenu estimé jusqu'à {bottom:.1f} cq (pied de page à {FOOT_Y})")
            chrome(D, s, sl, deck, n, False)
    D.save(out)
    return warnings


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__); return 2
    mission = argv[0]
    mdir = Path(prof.mission_dir(mission))
    src = mdir / "dossier.json"
    if "--input" in argv:
        src = Path(argv[argv.index("--input") + 1])
    deck = json.loads(src.read_text(encoding="utf-8"))
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
    if "--pptx" not in argv:
        print(f"Dossier projet · {deck.get('project')} · {len(deck['slides'])} slides (source : {src})")
        for n, sl in enumerate(deck["slides"], 1):
            print(f"  {n:02d}  {sl['kind']:<12} {sl.get('title', '').replace(chr(10), ' ')}  ->  {sl.get('src', '')}")
        print("\nExport : --pptx out.pptx")
        return 0
    out = Path(argv[argv.index("--pptx") + 1])
    warnings = render(deck, mdir, out, only)
    print(f"ok : {out} ({len(deck['slides']) if not only else len(only)} slides)")
    for w in warnings:
        print("  attention :", w)
    return 0


sys.path.insert(0, str(ROOT / "framework" / "lib"))
import slides as S  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
