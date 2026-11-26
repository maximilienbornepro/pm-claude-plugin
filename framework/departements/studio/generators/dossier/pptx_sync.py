"""pptx_sync - relit un dossier.pptx retouché à la main et reporte les modifications dans dossier.json.

Ce qui remonte (formes nommées `dx:*` posées par pptx_render) :
- titres, sur-titres, légendes, sources, notes ; sous-titres et numéros des sections ;
- tableaux : texte des cellules, statuts (couleur de la cellule), niveaux (couleur du point), lettres RACI,
  ETP, pastilles de chantier (couleur), pourcentages (texte, ou longueur de la barre si on l'a étirée),
  lignes ajoutées ou supprimées ; la barre de répartition des états est recalculée depuis les nombres ;
- tuiles, KPI, barres d'avancement, burn-down (données du graphique), Gantt (barres déplacées ou étirées,
  trait « aujourd'hui », jalons), frise des jalons, météo des domaines, matrice des risques (pastilles
  déplacées d'une case à l'autre), weekly (puces à niveaux), compte rendu, textes des schémas ;
- ordre des slides, slides supprimées. Une slide ajoutée à la main est signalée, pas reprise.
Le sommaire est recalculé, jamais relu.
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "framework" / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slides as S  # noqa: E402
import pptx_render as R  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.oxml.ns import qn  # noqa: E402

EMU = S.EMU_CQ


def _rev(table):
    return {v.upper(): k for k, v in table.items()}


REV_PILL = {S.C.get(v[0], v[0]).upper(): k for k, v in S.PILL.items()}
REV_LEVEL = {S.C.get(v, v).upper(): k for k, v in S.LEVEL.items()}
REV_STATUS = {S.C.get(v, v).upper(): k for k, v in S.STATUS.items()}


def cqv(emu):
    return emu / EMU


def run_text(paragraph, bold_markup=True, strip=("★", "↗")):
    out = []
    for r in paragraph.runs:
        t = r.text
        for ch in strip:
            t = t.replace(ch, "")
        if not t:
            continue
        bold = (r.font.name or "") == S.F_REG
        out.append(f"**{t.strip()}**" + (" " if t.endswith(" ") else "") if (bold and bold_markup and t.strip()) else t)
    return "".join(out).strip()


def frame_text(shape, sep="\n", **kw):
    if not shape.has_text_frame:
        return ""
    return sep.join(run_text(p, **kw) for p in shape.text_frame.paragraphs).strip()


def fill_hex(obj):
    try:
        if obj.fill.type == 1:  # solid
            return str(obj.fill.fore_color.rgb).upper()
    except Exception:
        pass
    return None


def run_color(paragraph, i=0):
    try:
        return str(paragraph.runs[i].font.color.rgb).upper()
    except Exception:
        return None


def pct(s):
    m = re.search(r"-?\d+(?:[.,]\d+)?", s or "")
    return None if not m else float(m.group(0).replace(",", "."))


def num_str(v):
    return str(int(v)) if float(v).is_integer() else str(v)


def changed(new, old):
    return new is not None and old is not None and abs(new - old) > .5


# ── tables ────────────────────────────────────────────────────────────────────
def read_cell(cell, old, total=False):
    """Return the updated JSON cell, keeping its type and options."""
    para = cell.text_frame.paragraphs[0]
    styled = isinstance(old, dict) and any(k in old for k in ("pill", "raci", "dot", "heat", "st", "bar"))
    txt = run_text(para, bold_markup=not (total or styled)).replace("●", "").strip()
    if not isinstance(old, dict):
        return txt if not isinstance(old, (int, float)) else txt
    new = dict(old)
    if "pill" in old:
        new["t"] = txt
        new["pill"] = REV_PILL.get(fill_hex(cell) or "", old["pill"])
    elif "dot" in old:
        new["t"] = txt
        new["dot"] = REV_LEVEL.get(run_color(para) or "", old["dot"])
    elif "raci" in old:
        new["raci"] = (txt or old["raci"])[:1].upper()
    elif "heat" in old:
        new["t"] = txt
        v = pct(txt)
        new["heat"] = 0 if v is None else (int(v) if float(v).is_integer() else v)
    elif "st" in old:
        new["st"] = REV_STATUS.get(run_color(para) or "", old["st"])
    elif "bar" in old:
        v = pct(txt)
        if v is not None:
            new["bar"] = int(round(v))
    elif "stack" in old:
        pass
    else:
        new["t"] = txt
    return new


def sync_table(gf, tab, shapes):
    tbl = gf.table
    head = not tab.get("nohead")
    nrows = len(tbl.rows) - (1 if head else 0)
    extra = (1 if tab.get("total") else 0) + (1 if tab.get("total2") else 0)
    body = nrows - extra
    rows = tab["rows"]
    out = []
    for i in range(body):
        tr = i + (1 if head else 0)
        old = rows[i] if i < len(rows) else [""] * len(tab["cols"])
        new = [read_cell(tbl.cell(tr, j), old[j] if j < len(old) else "") for j in range(len(tab["cols"]))]
        # bar stretched by hand: the shape wins when the text did not change
        for j, v in enumerate(new):
            if isinstance(v, dict) and "bar" in v and isinstance(old[j], dict) and v["bar"] == old[j].get("bar"):
                b, t = shapes.get(f"dx:bar:{i}"), shapes.get(f"dx:track:{i}")
                if b is not None and t is not None and t.width:
                    expected = max(t.width * old[j]["bar"] / 100, S.cq(.15))
                    if abs(b.width - expected) > S.cq(.08):  # stretched by hand
                        v["bar"] = max(0, min(100, int(round(100 * b.width / t.width))))
        out.append(new)
    tab["rows"] = out
    k = body + (1 if head else 0)
    for key in ("total", "total2"):
        if tab.get(key):
            tab[key] = [read_cell(tbl.cell(k, j), v, total=True) if not isinstance(v, dict) else read_cell(tbl.cell(k, j), v, total=True)
                        for j, v in enumerate(tab[key])]
            k += 1
    # states table: recompute the distribution bar from the counts
    keys = [c.get("key") for c in tab["cols"]]
    if any(keys):
        for r in tab["rows"] + ([tab["total"]] if tab.get("total") else []):
            sc = next((j for j, v in enumerate(r) if isinstance(v, dict) and "stack" in v), None)
            if sc is None:
                continue
            vals = [(keys[j], pct(r[j] if isinstance(r[j], str) else r[j].get("t", "")) or 0) for j in range(len(r)) if keys[j]]
            tot = sum(v for _, v in vals) or 1
            r[sc] = {"stack": [[k_, v / tot] for k_, v in vals]}


# ── per kind ──────────────────────────────────────────────────────────────────
def bar_ratio(shapes, i):
    b, t = shapes.get(f"dx:bar:{i}"), shapes.get(f"dx:track:{i}")
    if b is None or t is None or not t.width:
        return None
    return b.width / t.width


def sync_chart(gf, c, shapes, report):
    old_labels = {k_: c.get(k_) for k_ in ("elapsed_label", "remain_label", "end_label")}
    ch = gf.chart
    series = {}
    for ser in ch._chartSpace.iter(qn("c:ser")):
        tx = ser.find(qn("c:tx"))
        vs = [v.text for v in tx.iter(qn("c:v"))] if tx is not None else []
        name = (vs[0] if vs else "").strip()
        xs = [float(v.text) for v in ser.find(qn("c:xVal")).iter(qn("c:v"))]
        ys = [float(v.text) for v in ser.find(qn("c:yVal")).iter(qn("c:v"))]
        series[name] = [[(int(a) if a.is_integer() else a), (int(b) if b.is_integer() else b)] for a, b in zip(xs, ys)]
    key = {"Réel": "real", "Idéal": "ideal", "Tendance": "trend"}
    for name, pts in series.items():
        if name in key and pts and pts != c[key[name]]:
            c[key[name]] = pts
            report.append(f"burn-down : série « {name} » mise à jour ({len(pts)} points)")
    if c["real"]:
        lx, ly = c["real"][-1]
        if (lx, ly) != (c["elapsed"], c["today"]["y"]):
            old_x, old_y = c["elapsed"], c["today"]["y"]
            c["elapsed"], c["today"]["x"], c["today"]["y"] = lx, lx, ly
            lab = c["today"]["label"]
            lab = re.sub(r"J\+?\d+", lambda m: f"J+{num_str(lx)}" if "+" in m.group(0) or c["x"][0] == 0 else f"J{num_str(lx)}", lab, count=1)
            lab = re.sub(rf"\b{num_str(old_y)}\b", num_str(ly), lab)
            c["today"]["label"] = lab
            if c.get("elapsed_label"):
                c["elapsed_label"] = re.sub(rf"\b{num_str(old_x)}\b", num_str(lx), c["elapsed_label"], count=1)
    # vertical markers moved by hand
    fi = R.CHART_INNER
    gx, gw = cqv(gf.left), cqv(gf.width)
    (x0, x1) = c["x"]
    for i, v in enumerate(c.get("vlines", [])):
        ln = shapes.get(f"dx:vline:{i}")
        if ln is not None:
            d = x0 + (cqv(ln.left) - gx - gw * fi["x"]) / (gw * fi["w"]) * (x1 - x0)
            if abs(d - v["x"]) > .6:
                v["x"] = round(d)
        lab = shapes.get(f"dx:vlabel:{i}")
        if lab is not None:
            v["label"] = frame_text(lab, bold_markup=False) or v["label"]
    for name, k_ in (("dx:today_label", None), ("dx:elapsed_label", "elapsed_label"), ("dx:remain_label", "remain_label"), ("dx:end_label", "end_label")):
        sh = shapes.get(name)
        if sh is not None and k_:
            v = frame_text(sh, bold_markup=False)
            if v and v != old_labels.get(k_):  # edited by hand wins over the recomputed label
                c[k_] = v


def sync_slide(sl, shapes, sid, report):
    def txt(name, default=None, **kw):
        sh = shapes.get(name)
        return frame_text(sh, **kw) if sh is not None else default

    k = sl["kind"]
    t = shapes.get(f"dx:slide:{sid}")
    if t is not None:
        title = frame_text(t, bold_markup=False)
        if title and title.replace("\n", " ") != sl.get("title", "").replace("\n", " "):
            report.append(f"{sid} : titre « {sl.get('title', '')} » → « {title} »")
        if title:
            sl["title"] = title
    for name, key in (("dx:eyebrow", "eyebrow"), ("dx:cap", "cap"), ("dx:sub", "sub"), ("dx:kicker", "kicker"), ("dx:note", "note")):
        v = txt(name, bold_markup=False)
        if v is not None and key in sl:
            sl[key] = v
    v = txt("dx:secnum", bold_markup=False)
    if v is not None and k == "section":
        sl["num"] = v
    v = txt("dx:src", bold_markup=False)
    if v is not None and "src" in sl:
        sl["src"] = re.sub(r"^Source\s*·\s*", "", v).strip()

    if k in ("table", "tiles_table", "gate") and shapes.get("dx:table") is not None:
        sync_table(shapes["dx:table"], sl["table"], shapes)
    if k in ("tiles_table", "sprint"):
        for i, ti in enumerate(sl["tiles"]):
            for f in ("k", "v", "s"):
                val = txt(f"dx:tile:{i}:{f}", bold_markup=False)
                if val is not None and f in ti:
                    ti[f] = val
    if k in ("progress", "gate"):
        kp = shapes.get("dx:kpi")
        if kp is not None and kp.text_frame.paragraphs[0].runs:
            runs = kp.text_frame.paragraphs[0].runs
            sl["kpi"] = runs[0].text.strip()
            if k == "gate" and len(runs) > 1:
                sl["of"] = runs[1].text.strip()
            if k == "progress" and len(runs) > 1:
                sl["unit"] = runs[1].text.strip()
        v = txt("dx:lead", bold_markup=False)
        if v is not None:
            sl["lead"] = v
    if k == "progress":
        for i, b in enumerate(sl["bars"]):
            lab = txt(f"dx:plabel:{i}", bold_markup=False)
            if lab:
                b["l"] = lab
            if b.get("time"):
                continue
            tv = pct(txt(f"dx:pval:{i}", bold_markup=False))
            ratio = bar_ratio(shapes, i)
            if tv is not None and changed(tv, b["p"]):
                b["p"] = int(round(tv))
            elif ratio is not None and changed(ratio * 100, b["p"]):
                b["p"] = int(round(ratio * 100))
                report.append(f"{sid} : barre « {b['l']} » étirée → {b['p']} %")
    if k in ("burndown", "sprint") and shapes.get("dx:chart") is not None:
        sync_chart(shapes["dx:chart"], sl["chart"], shapes, report)
    if k == "gantt":
        g = sl["gantt"]
        gx, gw, _ = R.gantt_geom(0, g["days"])
        inv = lambda xcq: round((xcq - gx) / gw * g["days"], 1)  # noqa: E731
        for i, ln in enumerate(g["lanes"]):
            nm = txt(f"dx:lane_name:{i}", bold_markup=False)
            if nm:
                ln["n"] = nm
            bar, done = shapes.get(f"dx:lane:{i}"), shapes.get(f"dx:done:{i}")
            if bar is not None:
                a, b = inv(cqv(bar.left)), inv(cqv(bar.left + bar.width))
                if abs(a - ln["a"]) > .5 or abs(b - ln["b"]) > .5:
                    report.append(f"{sid} : couloir « {ln['n']} » J{ln['a']}-J{ln['b']} → J{round(a)}-J{round(b)}")
                    ln["a"], ln["b"] = round(a), round(b)
            if done is not None:
                d = inv(cqv(done.left + done.width))
                if abs(d - ln["done"]) > .5:
                    ln["done"] = max(ln["a"], round(d, 1))
        td = shapes.get("dx:today")
        if td is not None:
            d = inv(cqv(td.left))
            if abs(d - g["today"]["d"]) > .5:
                g["today"]["d"] = round(d)
        v = txt("dx:today_label", bold_markup=False)
        if v:
            g["today"]["label"] = v
        for i, m in enumerate(g["milestones"]):
            sh = shapes.get(f"dx:ms:{i}")
            if sh is not None:
                d = inv(cqv(sh.left + sh.width / 2))
                if abs(d - m["d"]) > .5:
                    m["d"] = round(d)
            v = txt(f"dx:mslabel:{i}", bold_markup=False)
            if v:
                m["label"] = v
    if k == "milestones":
        line, el = shapes.get("dx:msline"), shapes.get("dx:mselapsed")
        if line is not None:
            lx, lw = cqv(line.left), cqv(line.width) or 1
            if el is not None:
                sl["elapsed"] = round(cqv(el.width) / lw, 3)
            for i, it in enumerate(sl["items"]):
                sh = shapes.get(f"dx:ms:{i}")
                if sh is not None:
                    p = round((cqv(sh.left + sh.width / 2) - lx) / lw, 3)
                    if abs(p - it["p"]) > .005:
                        it["p"] = p
                for f, key in (("mstop", "top"), ("msdate", "date")):
                    v = txt(f"dx:{f}:{i}", bold_markup=False)
                    if v:
                        it[key] = v
    if k == "meteo":
        for i, d in enumerate(sl["domains"]):
            for f in ("k", "v"):
                v = txt(f"dx:dom:{i}:{f}", bold_markup=False)
                if v:
                    d[f] = v
            box = shapes.get(f"dx:dom:{i}")
            if box is not None:
                d["st"] = REV_PILL.get(fill_hex(box) or "", d["st"])
            r = bar_ratio(shapes, i)
            if r is not None and abs(r - d["closed"]) > .02:
                d["closed"] = round(r, 2)
    if k == "matrix":
        cells = {}
        for r in range(4):
            for c in range(4):
                sh = shapes.get(f"dx:cell:{r}:{c}")
                if sh is not None:
                    cells[(r, c)] = sh
                    lv = REV_LEVEL.get(fill_hex(sh) or "")
                    if lv:
                        sl["grid"][r][c] = lv
        chips = {}
        for name, sh in shapes.items():
            if name.startswith("dx:chip:"):
                cid = frame_text(sh, bold_markup=False) or name[8:]
                cx, cy = sh.left + sh.width / 2, sh.top + sh.height / 2
                for (r, c), cell in cells.items():
                    if cell.left <= cx <= cell.left + cell.width and cell.top <= cy <= cell.top + cell.height:
                        chips.setdefault(f"{r},{c}", []).append(cid)
        if chips:
            if chips != sl["chips"]:
                report.append(f"{sid} : position des risques dans la matrice mise à jour")
            sl["chips"] = chips
        for i, it in enumerate(sl["top"]):
            for f in ("id", "t", "lev", "lt"):
                v = txt(f"dx:top:{i}:{f}", bold_markup=False)
                if v:
                    it[f] = v
            pill = shapes.get(f"dx:top:{i}:pill")
            if pill is not None:
                it["lvl"] = REV_LEVEL.get(fill_hex(pill) or "", it["lvl"])
    if k == "weekly":
        for i, col in enumerate(sl["cols"]):
            v = txt(f"dx:whead:{i}", bold_markup=False)
            if v:
                col["h"] = v
            sh = shapes.get(f"dx:wcol:{i}")
            if sh is None:
                continue
            items = []
            for p in sh.text_frame.paragraphs:
                if not p.text.strip():
                    continue
                if p.level == 0:
                    b = "".join(r.text for r in p.runs if (r.font.name or "") == S.F_REG).strip()
                    rest = "".join(r.text for r in p.runs if (r.font.name or "") != S.F_REG).strip()
                    items.append({"b": b or rest, **({"t": rest} if b and rest else {})})
                elif items:
                    items[-1].setdefault("sub", []).append(p.text.strip())
            if items:
                col["items"] = items
    if k == "mail":
        v = txt("dx:obj", bold_markup=False)
        if v:
            sl["obj"] = v
        sh = shapes.get("dx:intro")
        if sh is not None:
            sl["intro"] = [run_text(p) for p in sh.text_frame.paragraphs if p.text.strip()]
        subs = []
        i = 0
        while shapes.get(f"dx:subj:{i}") is not None:
            ps = [p for p in shapes[f"dx:subj:{i}"].text_frame.paragraphs if p.text.strip()]
            if ps:
                subs.append({"h": run_text(ps[0], bold_markup=False), "s": run_text(ps[1]) if len(ps) > 1 else "",
                             "n": run_text(ps[2]) if len(ps) > 2 else ""})
            i += 1
        if subs:
            sl["subjects"] = subs
        sh = shapes.get("dx:closing")
        if sh is not None:
            ps = [run_text(p) for p in sh.text_frame.paragraphs if p.text.strip()]
            if ps:
                sl["closing"] = [ps[0]] + (["\n".join(ps[1:])] if len(ps) > 1 else [])
    if k == "diagram":
        for i, b in enumerate(sl["diagram"]["boxes"]):
            sh = shapes.get(f"dx:box:{i}")
            if sh is not None and sh.has_text_frame:
                ps = [p for p in sh.text_frame.paragraphs if p.text.strip()]
                if ps:
                    b["n"] = run_text(ps[0], bold_markup=False)
                    if len(ps) > 1:
                        b["s"] = run_text(ps[1], bold_markup=False)
        for i, lab in enumerate(sl["diagram"].get("labels", [])):
            v = txt(f"dx:label:{i}", bold_markup=False)
            if v:
                lab[2] = v


def sync(deck, pptx_path):
    """Return (new deck, report lines). The input deck is not modified."""
    deck = copy.deepcopy(deck)
    prs = Presentation(str(pptx_path))
    ids = R.slide_ids(deck)
    by_id = dict(zip(ids, deck["slides"]))
    seen, order, report = set(), [], []
    for idx, s in enumerate(prs.slides, 1):
        shapes = {sh.name: sh for sh in s.shapes}
        sid = next((n[9:] for n in shapes if n.startswith("dx:slide:")), None)
        if sid == "sommaire":
            continue
        if sid is None or sid not in by_id:
            report.append(f"slide {idx} ajoutée à la main : non reprise dans dossier.json (à ajouter dans la source si besoin)")
            continue
        sync_slide(by_id[sid], shapes, sid, report)
        seen.add(sid); order.append(sid)
    removed = [sid for sid in ids if sid not in seen]
    for sid in removed:
        report.append(f"slide « {by_id[sid].get('title', sid)} » supprimée dans le PowerPoint : retirée de dossier.json")
    if order != [sid for sid in ids if sid in seen]:
        report.append("ordre des slides modifié dans le PowerPoint : repris")
    deck["slides"] = [by_id[sid] for sid in order]
    return deck, report
