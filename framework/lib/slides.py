"""slides - charte des slides du dossier projet et primitives PPTX natives (python-pptx).

Une seule charte pour le HTML du dossier projet et pour l'export PowerPoint (skill `slide-style`) :
fond ivoire, slides de section noires, typo sans empattement très légère, aplats de couleur.

Unité de travail : le « cq » = 1 % de la largeur de la slide (comme les `cqw` de la maquette HTML).
La slide fait 100 cq de large et 56,25 cq de haut (16:9). 1 cq de corps = 9,6 pt.

Dépendance : python-pptx (pip install python-pptx). Lecture seule vis-à-vis des systèmes :
ce module n'écrit que le fichier .pptx demandé.
"""
from __future__ import annotations

import re
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.dml import MSO_LINE_DASH_STYLE
    from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.oxml.ns import qn
    from pptx.util import Emu, Pt
    from lxml import etree
except ImportError as e:  # pragma: no cover
    raise SystemExit("python-pptx est requis pour l'export PPTX : pip install python-pptx") from e

# ── Charte (mêmes valeurs que docs/maquette/index.html) ─────────────────────────
C = {
    "noir": "0B0B0B", "ivoire": "F7F4EF", "blanc": "FFFFFF", "encre": "1A1A1A", "gris": "8A8580",
    "filet": "D9D3CA", "voile": "ECE6DD", "sable": "E9DFD1", "taupe": "B7A99A", "sauge": "A9B5A0",
    "ardoise": "5E6670", "bordeaux": "7A1F23", "or": "B8975A", "texte": "4A4643", "cap": "5A5550",
    "voile2": "F1ECE5", "e1": "F0EBE3",
}
# Levels, statuses, RACI and workstream status: one colour per meaning, everywhere.
LEVEL = {"l1": "EEE8DF", "l2": C["sable"], "l3": C["taupe"], "l4": C["bordeaux"]}
PILL = {"ok": (C["sauge"], C["encre"]), "cours": (C["sable"], C["encre"]), "risque": (C["taupe"], C["encre"]),
        "bloque": (C["bordeaux"], C["blanc"]), "afaire": (C["voile"], C["encre"]), "fait": (C["noir"], C["blanc"])}
STATUS = {"v": "7E9A6E", "j": "D9B44A", "o": "C9803A", "r": C["bordeaux"]}
RACI = {"R": (C["noir"], C["blanc"]), "A": (C["bordeaux"], C["blanc"]), "C": (C["sable"], C["encre"]), "I": (C["voile"], C["gris"])}
HEAT = {0: None, .5: C["e1"], 1: C["sable"]}

# Light sans-serif, never serif. Windows falls back to Segoe UI Light if Helvetica Neue is missing.
F_LIGHT, F_THIN, F_REG = "Helvetica Neue Light", "Helvetica Neue Thin", "Helvetica Neue"

W_CQ, H_CQ = 100.0, 56.25
EMU_CQ = 121920  # 12 192 000 EMU / 100


def cq(v: float) -> int:
    return int(round(v * EMU_CQ))


def pt_of(size_cq: float) -> float:
    return size_cq * 9.6


def rgb(hexa: str) -> RGBColor:
    return RGBColor.from_string(C.get(hexa, hexa))


def col(name):
    """Colour token or raw hex -> hex string."""
    if name is None:
        return None
    return C.get(name, name)


def _strip_style(shape):
    st = shape._element.find(qn("p:style"))
    if st is not None:
        shape._element.remove(st)


def _arrow(line_el, start=False, end=False):
    ln = line_el
    for tag, on in (("a:headEnd", start), ("a:tailEnd", end)):
        if on:
            e = etree.SubElement(ln, qn(tag))
            e.set("type", "triangle"); e.set("w", "med"); e.set("len", "med")


def _bullet(para, char="–", indent_cq=1.4, left_cq=0.0):
    """Real bullet with hanging indent on a paragraph (editable as a list in PowerPoint)."""
    pPr = para._p.get_or_add_pPr()
    pPr.set("marL", str(cq(left_cq + indent_cq))); pPr.set("indent", str(-cq(indent_cq)))
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
        for e in pPr.findall(qn(tag)):
            pPr.remove(e)
    clr = etree.SubElement(pPr, qn("a:buClr")); etree.SubElement(clr, qn("a:srgbClr")).set("val", C["gris"])
    etree.SubElement(pPr, qn("a:buChar")).set("char", char)


HLINK_EXT = "{A12FA001-AC4F-418D-AE19-62706E023703}"
HLINK_NS = "http://schemas.microsoft.com/office/drawing/2018/hyperlinkcolor"


def plain_link(run):
    """Hyperlink drawn in the run's own colour, not underlined (instead of the theme's blue)."""
    rPr = run._r.get_or_add_rPr()
    rPr.set("u", "none")
    h = rPr.find(qn("a:hlinkClick"))
    if h is None:
        return
    lst = h.find(qn("a:extLst"))
    if lst is None:
        lst = etree.SubElement(h, qn("a:extLst"))
    ext = etree.SubElement(lst, qn("a:ext")); ext.set("uri", HLINK_EXT)
    etree.SubElement(ext, "{%s}hlinkClr" % HLINK_NS, nsmap={"ahyp": HLINK_NS}).set("val", "tx")


def no_bullet(para):
    pPr = para._p.get_or_add_pPr()
    pPr.set("marL", "0"); pPr.set("indent", "0")
    etree.SubElement(pPr, qn("a:buNone"))


def runs_of(text: str):
    """'a **b** c' -> [(a, False), (b, True), (c, False)]."""
    out = []
    for i, part in enumerate(re.split(r"\*\*", text)):
        if part:
            out.append((part, i % 2 == 1))
    return out


def est_lines(text: str, width_cq: float, size_cq: float) -> int:
    """Rough line count for wrapped text (light sans, ~0.5 em per character)."""
    if not text:
        return 1
    cpl = max(1, int(width_cq / (size_cq * 0.5)))
    n = 0
    for para in str(text).split("\n"):
        n += max(1, -(-len(para) // cpl))
    return n


class Deck:
    def __init__(self, logos_dir: Path | None = None, logos: dict | None = None):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Emu(12192000), Emu(6858000)
        self.blank = self.prs.slide_layouts[6]
        self.logos_dir, self.logos = logos_dir, logos or {}
        self.set_theme_fonts()

    # ── slides ──
    def new(self, dark=False, layout=6):
        """layout: 0 Title Slide (cover), 1 Title and Content (content: title = H1, body = caption),
        2 Section Header (section), 6 Blank. Placeholders keep PowerPoint's structure (outline, summary)."""
        s = self.prs.slides.add_slide(self.prs.slide_layouts[layout])
        bg = s.background.fill
        bg.solid(); bg.fore_color.rgb = rgb("noir" if dark else "ivoire")
        return s

    def placeholder(self, s, idx, x, y, w, h, content, name=None, **kw):
        """Fill and place a layout placeholder (title idx 0, body/subtitle idx 1) with the charter style."""
        ph = s.placeholders[idx]
        ph.left, ph.top, ph.width, ph.height = cq(x), cq(y), cq(w), cq(h)
        if name:
            ph.name = name
        tf = ph.text_frame
        for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, m, 0)
        self.text(s, x, y, w, h, content, tf=tf, **kw)
        for para in tf.paragraphs:
            pPr = para._p.pPr
            if pPr is None or pPr.find(qn("a:buChar")) is None:
                no_bullet(para)
        return ph

    def drop_empty_placeholders(self, s):
        for ph in list(s.placeholders):
            if not ph.has_text_frame or not ph.text_frame.text.strip():
                ph._element.getparent().remove(ph._element)

    def set_theme_fonts(self, major=F_LIGHT, minor=F_LIGHT):
        """Theme fonts = charter fonts, so text added by hand in PowerPoint matches the deck."""
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        theme = self.prs.slide_master.part.part_related_by(RT.THEME)
        xml = theme.blob.decode("utf-8")
        xml = re.sub(r'(<a:majorFont>\s*<a:latin typeface=")[^"]*', r"\g<1>" + major, xml, count=1)
        xml = re.sub(r'(<a:minorFont>\s*<a:latin typeface=")[^"]*', r"\g<1>" + minor, xml, count=1)
        for tag in ("hlink", "folHlink"):  # links in the charter ink, never the default blue
            xml = re.sub(rf"(<a:{tag}>)\s*<a:[a-zA-Z]+Clr [^>]*/>", rf'\g<1><a:srgbClr val="{C["encre"]}"/>', xml, count=1)
        theme._blob = xml.encode("utf-8")

    def save(self, out):
        self.prs.save(str(out))

    # ── primitives (all coordinates in cq) ──
    def text(self, s, x, y, w, h, content, size=1.0, color="encre", font=F_LIGHT, align="l", spacing=0.0,
             caps=False, anchor="t", line=1.15, link=None, bold_font=F_REG, para_space=0.0, name=None, tf=None):
        """content: str (with **bold**), or list of paragraphs, each a str or a list of (text, opts) runs."""
        if tf is None:
            tb = s.shapes.add_textbox(cq(x), cq(y), cq(w), cq(h))
            tf = tb.text_frame
        else:  # fill an existing text frame (placeholder)
            tb = None
            tf.clear()
        if name and tb is not None:
            tb.name = name
        tf.word_wrap = True
        for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, m, 0)
        tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
        paras = content if isinstance(content, list) else [content]
        for i, p in enumerate(paras):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
            para.line_spacing = line
            if para_space and i:
                para.space_before = Pt(para_space)
            if isinstance(p, dict):  # {"runs": [...], "level": n, "bullet": "–"}
                para.level = p.get("level", 0)
                if p.get("bullet"):
                    _bullet(para, p["bullet"], p.get("indent", 1.4), p.get("left", 0.0))
                p = p["runs"]
            runs = p if isinstance(p, list) else [(t, {"bold": b}) for t, b in runs_of(p)]
            for t, o in runs:
                r = para.add_run()
                r.text = t
                if o.get("caps", caps):
                    r._r.get_or_add_rPr().set("cap", "all")  # small caps by style, text keeps its case
                f = r.font
                f.name = bold_font if o.get("bold") else o.get("font", font)
                f.size = Pt(pt_of(o.get("size", size)))
                f.color.rgb = rgb(o.get("color", color))
                sp = o.get("spacing", spacing)
                if sp:
                    r._r.get_or_add_rPr().set("spc", str(int(sp * 100)))
                if o.get("link", link):
                    r.hyperlink.address = o.get("link", link)
                    plain_link(r)
        return tb

    def rect(self, s, x, y, w, h, fill=None, line=None, lw=1.0, dash=False, shape=MSO_SHAPE.RECTANGLE, name=None):
        sh = s.shapes.add_shape(shape, cq(x), cq(y), cq(w), cq(h))
        if name:
            sh.name = name
        _strip_style(sh)
        if fill:
            sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill)
        else:
            sh.fill.background()
        if line:
            sh.line.color.rgb = rgb(line); sh.line.width = Pt(lw)
            if dash:
                sh.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        else:
            sh.line.fill.background()
        sh.shadow.inherit = False
        return sh

    def oval(self, s, cx, cy, r, fill, line=None, name=None):
        return self.rect(s, cx - r, cy - r, 2 * r, 2 * r, fill, line, shape=MSO_SHAPE.OVAL, name=name)

    def diamond(self, s, cx, cy, r, fill, name=None):
        return self.rect(s, cx - r, cy - r, 2 * r, 2 * r, fill, shape=MSO_SHAPE.DIAMOND, name=name)

    def line(self, s, x1, y1, x2, y2, color="encre", w=0.75, dash=False, start=False, end=False, name=None):
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, cq(x1), cq(y1), cq(x2), cq(y2))
        if name:
            c.name = name
        _strip_style(c)
        c.line.color.rgb = rgb(color); c.line.width = Pt(w)
        if dash:
            c.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        if start or end:
            _arrow(c.line._get_or_add_ln(), start, end)
        return c

    def poly(self, s, pts, color="encre", w=1.0, dash=False, start=False, end=False):
        if len(pts) == 2:
            return self.line(s, *pts[0], *pts[1], color=color, w=w, dash=dash, start=start, end=end)
        fb = s.shapes.build_freeform(cq(pts[0][0]), cq(pts[0][1]), scale=1.0)
        fb.add_line_segments([(cq(x), cq(y)) for x, y in pts[1:]], close=False)
        sh = fb.convert_to_shape()
        _strip_style(sh)
        sh.fill.background()
        sh.line.color.rgb = rgb(color); sh.line.width = Pt(w)
        if dash:
            sh.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        if start or end:
            _arrow(sh.line._get_or_add_ln(), start, end)
        return sh

    def picture(self, s, path, x, y, h=None, w=None):
        if not path or not Path(path).exists():
            return None
        return s.shapes.add_picture(str(path), cq(x), cq(y), height=cq(h) if h else None, width=cq(w) if w else None)

    def logo(self, key):
        name = self.logos.get(key)
        return (self.logos_dir / name) if (self.logos_dir and name) else None

    # ── native table ──
    def table(self, s, x, y, w, cols, rows, size=0.95, head=True, row_pad=0.85, min_row=0, name=None):
        """cols: [{h, w (fraction), align}] ; rows: list of list of cell dicts {runs, fill, align}.
        Returns (graphic_frame, [row tops], [row heights], [col lefts], [col widths]) in cq."""
        nrows = len(rows) + (1 if head else 0)
        widths = [w * c.get("w", 1 / len(cols)) for c in cols]
        gf = s.shapes.add_table(nrows, len(cols), cq(x), cq(y), cq(w), cq(1))
        if name:
            gf.name = name
        tbl = gf.table
        tblPr = tbl._tbl.tblPr
        for a in ("firstRow", "bandRow"):
            tblPr.set(a, "0")
        sid = tblPr.find(qn("a:tableStyleId"))
        if sid is not None:
            tblPr.remove(sid)
        for j, wd in enumerate(widths):
            tbl.columns[j].width = cq(wd)
        all_rows = ([[{"runs": [(c.get("h", ""), {"caps": True, "spacing": 2.2, "size": size * .78, "color": "gris", "font": F_REG})],
                       "align": c.get("align", "l"), "fill": c.get("hfill"), "head": True} for c in cols]] if head else []) + rows
        tops, heights, yy = [], [], y
        for i, row in enumerate(all_rows):
            hdr = head and i == 0
            lines = 1
            for j, cell in enumerate(row):
                txt = "".join(t for t, _ in cell.get("runs", []))
                lines = max(lines, est_lines(txt, widths[j] - 1.6, size))
            rh = max(min_row, (size * 1.45 * lines + row_pad * 2) if not hdr else size * 0.78 * 1.4 + 1.6)
            tbl.rows[i].height = cq(rh)
            tops.append(yy); heights.append(rh); yy += rh
            for j, cell in enumerate(row):
                tc = tbl.cell(i, j)
                tc.margin_left = tc.margin_right = cq(0.8)
                tc.margin_top = tc.margin_bottom = cq(0.2)
                tc.vertical_anchor = MSO_ANCHOR.MIDDLE if not hdr else MSO_ANCHOR.BOTTOM
                if cell.get("fill"):
                    tc.fill.solid(); tc.fill.fore_color.rgb = rgb(cell["fill"])
                else:
                    tc.fill.background()
                tf = tc.text_frame
                tf.word_wrap = True
                para = tf.paragraphs[0]
                para.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[cell.get("align", "l")]
                for t, o in cell.get("runs", []):
                    r = para.add_run()
                    r.text = t
                    if o.get("caps"):
                        r._r.get_or_add_rPr().set("cap", "all")
                    f = r.font
                    f.name = F_REG if o.get("bold") else o.get("font", F_LIGHT)
                    f.size = Pt(pt_of(o.get("size", size)))
                    f.color.rgb = rgb(o.get("color", "encre"))
                    if o.get("spacing"):
                        r._r.get_or_add_rPr().set("spc", str(int(o["spacing"] * 100)))
                bottom = ("encre", 1.0) if hdr else (cell.get("bline") or ("filet", 0.6))
                top = cell.get("tline")
                self._borders(tc, top=top, bottom=bottom)
        lefts, xx = [], x
        for wd in widths:
            lefts.append(xx); xx += wd
        return gf, tops, heights, lefts, widths

    @staticmethod
    def _borders(tc, top=None, bottom=None):
        tcPr = tc._tc.get_or_add_tcPr()
        for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
            for e in tcPr.findall(qn(tag)):
                tcPr.remove(e)
        spec = {"a:lnL": None, "a:lnR": None, "a:lnT": top, "a:lnB": bottom}
        for tag in reversed(("a:lnL", "a:lnR", "a:lnT", "a:lnB")):
            ln = etree.Element(qn(tag))
            v = spec[tag]
            if v:
                ln.set("w", str(int(Pt(v[1]))))
                sf = etree.SubElement(ln, qn("a:solidFill"))
                etree.SubElement(sf, qn("a:srgbClr")).set("val", col(v[0]))
            else:
                ln.set("w", "0")
                etree.SubElement(ln, qn("a:noFill"))
            tcPr.insert(0, ln)
