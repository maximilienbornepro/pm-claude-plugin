#!/usr/bin/env python3
"""planning - planning technique d'une mission, depuis UNE source de donnees.

Une seule source (planning.json / planning.yml) ; plusieurs rendus, toujours synchronises :
  - deck PPTX autonome (aucune dependance) :
      1. le Gantt (couloirs, barres, jalons, traits verticaux)
      2. la slide « Echeances du planning » : tableau DERIVE du Gantt (jamais saisi a la main)
      3. les slides de situation (Domaine / Sujet / Statut / Situation / Levier / Echeance)
      4. les tableaux libres (responsabilites, RACI resume...)
  - Gantt EXCEL : remplit le template Gantt (Vertex42 adapte) - alternative au PPT
  - markdown (defaut) : relecture + controles de coherence

Usage :
  planning.py <mission> [--input f.json|f.yml]          relecture markdown + controles
  planning.py <mission> --pptx out.pptx                 deck complet
  planning.py <mission> --xlsx out.xlsx [--template t]  Gantt Excel
  planning.py <mission> --json                          donnees normalisees (dont les echeances)

Lecture seule vis-a-vis des systemes : ecrit UNIQUEMENT les fichiers demandes, en local. Le report
dans un deck/classeur partage suit le deroule Office (framework/generators/_deroule-office.md).
"""
import sys, json, re, zipfile, datetime as dt, importlib.util
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def _load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


# --------------------------------------------------------------------------- donnees
def load_data(mission, path=None):
    if path is None:
        prof = _load_mod("pmf_profile", ROOT / "framework" / "lib" / "profile.py")
        for name in ("planning.json", "planning.yml", "planning.yaml"):
            p = prof.mission_file(mission, name)
            if Path(p).exists():
                path = p; break
        if path is None:
            path = HERE / "planning.example.json"
    path = Path(path)
    txt = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(txt), path
    ym = _load_mod("yamlmin", ROOT / "framework" / "lib" / "yamlmin.py")
    return ym.load(txt), path


def D(s):
    return dt.date.fromisoformat(str(s))


def ddmm(d):
    return f"{d.day:02d}/{d.month:02d}"


def items_of(data):
    """Tous les elements dates, dans l'ordre du Gantt : (couloir, item)."""
    for lane in data.get("lanes", []):
        for row in lane.get("rows", []):
            for it in row:
                yield lane["name"], it


def echeances(data):
    """Le tableau des echeances : derive du Gantt, element par element (sync garantie)."""
    out = []
    for lane, it in items_of(data):
        if not it.get("label") or it.get("in_table") is False:
            continue
        if it["type"] == "bar":
            when = f"{ddmm(D(it['start']))} → {ddmm(D(it['end']))}"
        elif it["type"] in ("milestone", "note"):
            when = ddmm(D(it["date"]))
        elif it["type"] == "run":
            when = f"dès le {ddmm(D(it['start']))}"
        else:
            continue
        out.append({"domain": lane, "label": it["label"], "when": when})
    for v in data.get("vlines", []):
        if v.get("label") and v.get("in_table", True):
            out.append({"domain": data.get("vlines_domain", "Jalons"), "label": v["label"], "when": ddmm(D(v["date"]))})
    return out


def checks(data):
    """Controles : dates dans la fenetre, fin >= debut, libelles en double, echeances vides."""
    issues = []
    start = D(data["start"]); end = start + dt.timedelta(weeks=int(data.get("weeks", 14)))
    seen = {}
    for lane, it in items_of(data):
        ds = [D(it[k]) for k in ("start", "end", "date") if k in it]
        for d in ds:
            if not (start <= d <= end):
                issues.append(f"[{lane}] « {it.get('label', it['type'])} » : {d} hors fenetre {start} -> {end}")
        if it["type"] == "bar" and D(it["end"]) < D(it["start"]):
            issues.append(f"[{lane}] « {it.get('label')} » : fin avant debut")
        if it.get("label"):
            k = it["label"].strip().lower()
            if k in seen:
                issues.append(f"libelle en double : « {it['label']} » ({seen[k]} / {lane})")
            seen[k] = lane
    for sl in data.get("status", {}).get("slides", []):
        for sec in sl.get("sections", []):
            for r in sec.get("rows", []):
                if r.get("status") not in STATUS:
                    issues.append(f"statut inconnu « {r.get('status')} » ({r.get('subject')}) - attendu : {', '.join(STATUS)}")
                if r.get("status") != "OK" and not r.get("lever"):
                    issues.append(f"levier manquant pour « {r.get('subject')} » (statut {r.get('status')})")
    return issues


# --------------------------------------------------------------------------- markdown
def to_md(data):
    L = [f"# {data.get('title', 'Planning')}", ""]
    if data.get("subtitle"):
        L += [f"_{data['subtitle']}_", ""]
    L += ["## Echeances (derivees du Gantt)", "", "| Domaine | Element | Date |", "|---|---|---|"]
    for e in echeances(data):
        L.append(f"| {e['domain']} | {e['label']} | {e['when']} |")
    for sl in data.get("status", {}).get("slides", []):
        L += ["", f"## {sl['title']}", "", "| Domaine | Sujet | Statut | Situation | Levier | Echeance |", "|---|---|---|---|---|---|"]
        for sec in sl["sections"]:
            for r in sec["rows"]:
                L.append(f"| {sec['domain']} | {r['subject']} | {r['status']} | {r['situation']} | {r.get('lever','')} | {r.get('due','')} |")
    for t in data.get("tables", []):
        L += ["", f"## {t['title']}", "", "| " + " | ".join(t["header"]) + " |", "|" + "---|" * len(t["header"])]
        for r in t["rows"]:
            L.append("| " + " | ".join(r) + " |")
    iss = checks(data)
    L += ["", "## Controles", ""] + ([f"- {i}" for i in iss] if iss else ["- aucun ecart"])
    return "\n".join(L)


# --------------------------------------------------------------------------- PPTX (OOXML brut)
NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
SW, SH = 9144000, 5143500
STATUS = {  # statut -> (fond, texte)   Prevu et En cours nettement distincts
    "OK": ("C6EFCE", "006100"),
    "En cours": ("2E75B6", "FFFFFF"),
    "Prévu": ("FFFFFF", "7F7F7F"),
    "À risque": ("FFEB9C", "9C5700"),
    "En discussion": ("FFC7CE", "9C0006"),
}
KIND = {"blue": "1442E1", "orange": "F39200", "black": "000000", "red": "E30613", "green": "2E9D4F", "purple": "8E5FD0"}


class Slide:
    def __init__(self, theme):
        self.shapes = []; self.n = 10; self.t = theme

    def _id(self):
        self.n += 1; return self.n

    @staticmethod
    def _fill(c):
        return f'<a:solidFill><a:srgbClr val="{c}"/></a:solidFill>' if c else '<a:noFill/>'

    def _run(self, txt, sz, bold, color, italic=False):
        b = ' b="1"' if bold else ''
        i = ' i="1"' if italic else ''
        return (f'<a:r><a:rPr lang="fr-FR" sz="{sz}"{b}{i} dirty="0"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
                f'<a:latin typeface="{self.t["font"]}"/></a:rPr><a:t>{escape(txt)}</a:t></a:r>')

    def box(self, x, y, cx, cy, text="", geom="rect", fill=None, line=None, sz=800, bold=False, color=None,
            algn="l", anchor="ctr", wrap=False, dash=None, flip=False, italic=False):
        i = self._id(); color = color or self.t["text"]
        ln = (f'<a:ln w="9525">{self._fill(line)}{f"<a:prstDash val=\"{dash}\"/>" if dash else ""}</a:ln>'
              if line else '<a:ln><a:noFill/></a:ln>')
        fl = ' flipV="1"' if flip else ''
        para = (f'<a:p><a:pPr algn="{algn}"/>{self._run(text, sz, bold, color, italic)}</a:p>' if text
                else f'<a:p><a:endParaRPr lang="fr-FR" sz="{sz}"/></a:p>')
        self.shapes.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{i}" name="Shape {i}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm{fl}><a:off x="{int(x)}" y="{int(y)}"/><a:ext cx="{max(int(cx),1)}" cy="{max(int(cy),1)}"/></a:xfrm>'
            f'<a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>{self._fill(fill)}{ln}</p:spPr>'
            f'<p:txBody><a:bodyPr wrap="{"square" if wrap else "none"}" lIns="18000" tIns="0" rIns="18000" bIns="0" anchor="{anchor}">'
            f'<a:noAutofit/></a:bodyPr><a:lstStyle/>{para}</p:txBody></p:sp>')

    def line(self, x, y, cx, cy, color, w=9525, dash=None):
        i = self._id()
        d = f'<a:prstDash val="{dash}"/>' if dash else ''
        self.shapes.append(
            f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{i}" name="Line {i}"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{int(x)}" y="{int(y)}"/><a:ext cx="{int(cx)}" cy="{int(cy)}"/></a:xfrm>'
            f'<a:prstGeom prst="line"><a:avLst/></a:prstGeom><a:ln w="{w}">{self._fill(color)}{d}</a:ln></p:spPr></p:cxnSp>')

    def table(self, x, y, widths, rows, sz=700):
        """rows : liste de (hauteur, [cellule]) ; cellule = dict(text, fill, color, bold, algn, span, merged)."""
        i = self._id()
        grid = "".join(f'<a:gridCol w="{int(w)}"/>' for w in widths)
        trs = []
        for h, cells in rows:
            tcs = []
            for c in cells:
                attrs = (f' rowSpan="{c["span"]}"' if c.get("span") else '') + (' vMerge="1"' if c.get("merged") else '')
                txt = c.get("text", "")
                p = (f'<a:p><a:pPr algn="{c.get("algn", "l")}"/>{self._run(txt, sz, c.get("bold"), c.get("color", self.t["text"]))}</a:p>'
                     if txt else f'<a:p><a:endParaRPr lang="fr-FR" sz="{sz}"/></a:p>')
                bd = ''.join(f'<a:{s} w="6350"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></a:{s}>' for s in ("lnL", "lnR", "lnT", "lnB"))
                tcs.append(f'<a:tc{attrs}><a:txBody><a:bodyPr/><a:lstStyle/>{p}</a:txBody>'
                           f'<a:tcPr marL="45720" marR="45720" marT="{9000 if sz <= 600 else 18000}" marB="{9000 if sz <= 600 else 18000}" anchor="ctr">{bd}{self._fill(c.get("fill"))}</a:tcPr></a:tc>')
            trs.append(f'<a:tr h="{int(h)}">{"".join(tcs)}</a:tr>')
        tot = sum(h for h, _ in rows)
        self.shapes.append(
            f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{i}" name="Table {i}"/><p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/>'
            f'</p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr><p:xfrm><a:off x="{int(x)}" y="{int(y)}"/><a:ext cx="{int(sum(widths))}" cy="{int(tot)}"/></p:xfrm>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table"><a:tbl><a:tblPr firstRow="1" bandRow="1"/>'
            f'<a:tblGrid>{grid}</a:tblGrid>{"".join(trs)}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>')
        return tot

    def header(self, title, subtitle=None):
        if TPL:  # gabarit d'entreprise : le titre va dans l'emplacement titre de la mise en page (style du gabarit)
            self.shapes.append(
                '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 1"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
                '<p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>'
                f'<a:p><a:r><a:rPr lang="fr-FR" dirty="0"/><a:t>{escape(title)}</a:t></a:r></a:p></p:txBody></p:sp>')
            if subtitle:
                self.box(300000, 640000, SW - 600000, 200000, subtitle, sz=1000, bold=True, color=self.t["secondary"], anchor="t")
            return
        self.box(300000, 140000, SW - 600000, 420000, title, sz=1600, bold=True, color=self.t["primary"], wrap=True, anchor="t")
        if subtitle:
            self.box(300000, 700000, SW - 600000, 200000, subtitle, sz=1000, bold=True, color=self.t["secondary"], anchor="t")
        if self.t.get("footer"):
            self.box(300000, SH - 260000, SW - 600000, 180000, self.t["footer"], sz=600, color="7F7F7F")

    def xml(self):
        shapes = [_fit(s) for s in self.shapes] if TPL else self.shapes
        return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld {NS}><p:cSld><p:spTree>'
                '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
                '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
                + "".join(shapes) + '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')


# --------------------------------------------------------------------------- gabarit d'entreprise (--pptx-template)
# Le contenu est dessiné dans le repère du deck neutre (SW x SH), puis recalé dans la zone utile de la mise en
# page du gabarit : sous l'emplacement titre, au-dessus du pied de page. Le titre de chaque slide va dans
# l'emplacement titre du gabarit (police, couleur et logo du gabarit).
TPL = None          # dict : x0, y0, sx, sy (rempli par load_template)
SRC_TOP = 600000    # dans le repère neutre, tout ce qui est sous cette ordonnée est du contenu


def _fit(shape):
    if '<p:ph type="title"/>' in shape:
        return shape
    T = TPL

    def xy(m):
        x, y, cx, cy = (int(v) for v in m.groups())
        return (f'<a:off x="{int(T["x0"] + x * T["sx"])}" y="{int(T["y0"] + max(0, y - SRC_TOP) * T["sy"])}"/>'
                f'<a:ext cx="{max(1, int(cx * T["sx"]))}" cy="{max(1, int(cy * T["sy"]))}"/>')
    shape = re.sub(r'<a:off x="(-?\d+)" y="(-?\d+)"/><a:ext cx="(\d+)" cy="(\d+)"/>', xy, shape)
    shape = re.sub(r'<a:gridCol w="(\d+)"/>', lambda m: f'<a:gridCol w="{int(int(m.group(1)) * T["sx"])}"/>', shape)
    shape = re.sub(r'<a:tr h="(\d+)">', lambda m: f'<a:tr h="{int(int(m.group(1)) * T["sy"])}">', shape)
    return shape


def _ph_box(xml, kind):
    """(x, y, cx, cy) de l'emplacement `kind` (title, body...) d'une mise en page ou d'un masque, ou None."""
    for m in re.finditer(r'<p:sp>.*?</p:sp>', xml, re.S):
        s = m.group(0)
        if re.search(rf'<p:ph[^>]*type="{kind}"', s) or (kind == "body" and re.search(r'<p:ph(?![^>]*type=)[^>]*idx="1"', s)):
            o = re.search(r'<a:off x="(\d+)" y="(\d+)"/><a:ext cx="(\d+)" cy="(\d+)"/>', s)
            if o:
                return tuple(int(v) for v in o.groups())
    return None


def load_template(path, layout_name=None, box=None):
    """Lit le gabarit, choisit la mise en page, calcule la zone utile. Retourne (fichiers, chemin de la mise en page)."""
    global TPL
    z = zipfile.ZipFile(path)
    files = {n: z.read(n) for n in z.namelist()}
    pres = files["ppt/presentation.xml"].decode("utf-8")
    m = re.search(r'<p:sldSz cx="(\d+)" cy="(\d+)"', pres)
    W, H = (int(m.group(1)), int(m.group(2))) if m else (SW, SH)
    layouts = {}
    for n, b in files.items():
        if re.match(r'ppt/slideLayouts/slideLayout\d+\.xml$', n):
            nm = re.search(r'<p:cSld name="([^"]*)"', b.decode("utf-8"))
            layouts[nm.group(1) if nm else n] = n
    if layout_name:
        if layout_name not in layouts:
            sys.exit(f"mise en page « {layout_name} » absente du gabarit. Disponibles : {', '.join(sorted(layouts))}")
        lay = layouts[layout_name]
    else:  # premiere mise en page qui a un emplacement titre
        lay = next((p for p in sorted(layouts.values()) if 'type="title"' in files[p].decode("utf-8")), sorted(layouts.values())[0])
    lx = files[lay].decode("utf-8")
    master = re.search(r'Target="\.\./slideMasters/(slideMaster\d+\.xml)"', files[lay.replace("slideLayouts/", "slideLayouts/_rels/") + ".rels"].decode("utf-8"))
    mx = files.get(f"ppt/slideMasters/{master.group(1)}", b"").decode("utf-8") if master else ""
    title = _ph_box(lx, "title") or _ph_box(mx, "title")
    body = _ph_box(lx, "body") or _ph_box(mx, "body")
    if box:
        x0, y0, w, h = box
    else:
        top = (title[1] + title[3] + 300000) if title else int(H * 0.18)   # sous le titre et son trait decoratif
        bottom = (body[1] + body[3]) if body else int(H * 0.92)
        x0, w = (body[0], body[2]) if body else (int(W * 0.03), int(W * 0.94))
        y0, h = top, max(bottom - top, int(H * 0.5))
    sx = w / (SW - 600000)
    TPL = {"x0": x0 - 300000 * sx, "y0": y0, "sx": sx, "sy": h / (SH - 280000 - SRC_TOP)}
    return files, lay


def write_pptx_template(slides, tpl_path, out, layout_name=None, box=None):
    """Deck dans le gabarit d'entreprise : on garde masques, mises en page, thème et médias, on retire ses slides."""
    files, lay = load_template(tpl_path, layout_name, box)
    pres = files["ppt/presentation.xml"].decode("utf-8")
    prels = files["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    ct = files["[Content_Types].xml"].decode("utf-8")
    # 1. retirer les slides du gabarit (et leurs notes)
    old = set(re.findall(r'<Relationship [^>]*Id="(rId\d+)"[^>]*Type="[^"]*/slide"[^>]*/>', prels))
    old |= set(re.findall(r'<Relationship [^>]*Type="[^"]*/slide"[^>]*Id="(rId\d+)"[^>]*/>', prels))
    prels = re.sub(r'<Relationship [^>]*Type="[^"]*/slide"[^>]*/>', '', prels)
    pres = re.sub(r'<p:sldIdLst>.*?</p:sldIdLst>', '<p:sldIdLst/>', pres, flags=re.S)
    pres = re.sub(r'<p14:sectionLst.*?</p14:sectionLst>', '', pres, flags=re.S)
    pres = re.sub(r'<p:custShowLst>.*?</p:custShowLst>', '', pres, flags=re.S)
    for n in list(files):
        if n.startswith(("ppt/slides/", "ppt/notesSlides/")):
            del files[n]
    ct = re.sub(r'<Override PartName="/ppt/(slides|notesSlides)/[^"]*"[^>]*/>', '', ct)
    # 2. ajouter nos slides sur la mise en page choisie
    ids = [int(v) for v in re.findall(r'<p:sld(?:Master)?Id id="(\d+)"', pres)] or [255]
    base = 256
    srels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{PKG}">'
             f'<Relationship Id="rId1" Type="{REL}/slideLayout" Target="../slideLayouts/{lay.rsplit("/", 1)[1]}"/></Relationships>')
    lst, rel_add, ct_add = [], [], []
    for i, s in enumerate(slides):
        files[f"ppt/slides/slide{i + 1}.xml"] = s.xml().encode("utf-8")
        files[f"ppt/slides/_rels/slide{i + 1}.xml.rels"] = srels.encode("utf-8")
        lst.append(f'<p:sldId id="{base + i}" r:id="rIdPmf{i + 1}"/>')
        rel_add.append(f'<Relationship Id="rIdPmf{i + 1}" Type="{REL}/slide" Target="slides/slide{i + 1}.xml"/>')
        ct_add.append(f'<Override PartName="/ppt/slides/slide{i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')
    pres = pres.replace('<p:sldIdLst/>', '<p:sldIdLst>' + "".join(lst) + '</p:sldIdLst>')
    prels = prels.replace('</Relationships>', "".join(rel_add) + '</Relationships>')
    ct = ct.replace('</Types>', "".join(ct_add) + '</Types>')
    files["ppt/presentation.xml"] = pres.encode("utf-8")
    files["ppt/_rels/presentation.xml.rels"] = prels.encode("utf-8")
    files["[Content_Types].xml"] = ct.encode("utf-8")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
        zo.writestr("[Content_Types].xml", files.pop("[Content_Types].xml"))
        for n, b in files.items():
            zo.writestr(n, b)
    return lay


def nlines(txt, cpl):
    n, cur = 1, 0
    for w in str(txt).split():
        if cur + len(w) + (1 if cur else 0) > cpl:
            n += 1; cur = len(w)
        else:
            cur += len(w) + (1 if cur else 0)
    return n


def theme_of(data):
    t = {"font": "Arial", "primary": "1F3864", "secondary": "2E75B6", "text": "222222", "bar": "8EC1FF",
         "bar_future": "D9E9FF", "header": "2E75B6", "band1": "DCE6F2", "band2": "EEF3F9", "footer": ""}
    t.update(data.get("theme", {}))
    return t


def gantt_slide(data, t):
    s = Slide(t)
    s.header(data.get("gantt_title") or data.get("title", "Planning"), data.get("subtitle"))
    start = D(data["start"]); start -= dt.timedelta(days=start.weekday())
    weeks = int(data.get("weeks", 14)); days = weeks * 7
    X0, X1 = 1650000, SW - 260000
    DAY = (X1 - X0) / days
    X = lambda d: X0 + (D(d) - start).days * DAY if not isinstance(d, dt.date) else X0 + (d - start).days * DAY
    YH, YW, Y0 = 860000, 1010000, 1180000
    rows = sum(len(l["rows"]) for l in data["lanes"])
    YB = SH - 330000
    LANE = min(200000, (YB - Y0) / max(rows, 1))
    # en-tete : mois + semaines
    s.box(300000, YW, 1250000, 150000, data.get("axis_label", "Activité"), sz=800, bold=True)
    m = start
    seen = set()
    for k in range(days):
        d = start + dt.timedelta(days=k)
        if (d.year, d.month) not in seen and (d.day <= 7 or k == 0):
            seen.add((d.year, d.month))
            lab = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."][d.month - 1]
            s.box(X(d), YH, 700000, 150000, f"{lab} {d.year}", sz=800, bold=True, color=t["primary"])
            s.line(X(d), YH, 0, YB - YH, "BFBFBF", 6350)
    for w in range(weeks):
        d = start + dt.timedelta(weeks=w)
        s.box(X(d), YW, 7 * DAY, 150000, f"{d.day:02d}", sz=700, color="595959")
        s.line(X(d), YW + 150000, 0, YB - YW - 150000, "E0E0E0", 6350, "sysDot")
    s.line(300000, Y0 - 10000, X1 - 300000, 0, t["primary"], 12700)
    # couloirs
    y = Y0
    for li, lane in enumerate(data["lanes"]):
        n = len(lane["rows"])
        if li:
            s.line(300000, y, X1 - 300000, 0, "A6A6A6", 6350)
        s.box(300000, y + 10000, 1300000, min(LANE * n - 20000, 300000), lane["name"], sz=800, bold=True, anchor="t", wrap=True)
        for row in lane["rows"]:
            for it in row:
                _item(s, t, it, y, LANE, X, DAY, X1)
            y += LANE
    # traits verticaux (signature, ouverture, aujourd'hui...)
    for v in data.get("vlines", []):
        x = X(v["date"]) + DAY / 2
        col = KIND.get(v.get("kind", "orange"), v.get("kind", "F39200"))
        s.line(x, YW, 0, YB - YW, col, 12700, "dash")
        if v.get("label"):
            s.box(x - 600000, YB + 10000, 1200000, 130000, f'{v["label"]} {ddmm(D(v["date"]))}', sz=650, bold=True, color=col, algn="ctr")
    return s


def _item(s, t, it, y, LANE, X, DAY, X1):
    CH = 47000  # largeur approx d'un caractere en 7 pt (marge comprise)
    lab = it.get("label", ""); side = it.get("side", "r")
    if it["type"] == "bar":
        x1 = X(it["start"]); x2 = X(it["end"]) + DAY
        bh = LANE * 0.55
        s.box(x1, y + (LANE - bh) / 2, x2 - x1, bh, fill=it.get("color", t["bar"]))
        if lab:
            w = len(lab) * CH + 60000
            if side == "l":
                s.box(x1 - w - 20000, y, w, LANE, lab, sz=700, algn="r")
            elif w <= (x2 - x1) and not it.get("label_out"):
                s.box(x1, y, x2 - x1, LANE, lab, sz=700, algn="ctr")
            else:
                s.box(x2 + 20000, y, w, LANE, lab, sz=700)
    elif it["type"] in ("milestone", "note"):
        x = X(it["date"]) + DAY / 2
        if it["type"] == "milestone":
            sz = LANE * 0.65
            geom = "diamond" if it.get("kind") == "diamond" else "triangle"
            s.box(x - sz / 2, y + (LANE - sz) / 2, sz, sz, geom=geom, fill=KIND.get(it.get("kind", "blue"), "1442E1"))
            off = sz / 2 + 20000
        else:
            off = 0
        if lab:
            w = len(lab) * CH + 60000
            if side == "l":
                s.box(x - off - w, y, w, LANE, lab, sz=700, algn="r")
            else:
                s.box(x + off, y, w, LANE, lab, sz=700)
    elif it["type"] == "run":
        x = X(it["start"])
        s.box(x, y + LANE * 0.15, X1 - x, LANE * 0.7, it.get("label", "Run"), geom="homePlate",
              fill="D9D9D9", sz=700, italic=True, algn="ctr")


def echeances_slides(data, t):
    """Deux tableaux cote a cote ; pagination si besoin. Couloirs jamais coupes."""
    rows = echeances(data)
    groups = []
    for e in rows:
        if groups and groups[-1][0] == e["domain"]:
            groups[-1][1].append(e)
        else:
            groups.append((e["domain"], [e]))
    W = [820000, 2600000, 830000]
    HDR, LIMIT = 150000, SH - 330000 - 1100000
    cpl = int(W[1] / 45000)
    def gh(g):  # hauteur d'un couloir
        return sum(nlines(e["label"], cpl) * 110000 + 45000 for e in g[1])  # estimation prudente
    cols, cur, h = [], [], HDR
    for g in groups:
        if cur and h + gh(g) > LIMIT:
            cols.append(cur); cur, h = [], HDR
        cur.append(g); h += gh(g)
    if cur:
        cols.append(cur)
    slides = []
    for k in range(0, len(cols), 2):
        s = Slide(t)
        sub = data.get("echeances_subtitle", "Échéances du planning")
        if len(cols) > 2:
            sub += f" ({k // 2 + 1}/{(len(cols) + 1) // 2})"
        s.header(data.get("echeances_title", "Les échéances du planning"), sub)
        for j, col in enumerate(cols[k:k + 2]):
            trs = [(HDR, [{"text": x, "bold": True, "fill": t["header"], "color": "FFFFFF"} for x in ("Domaine", "Élément du planning", "Date")])]
            for gi, (dom, es) in enumerate(col):
                band = t["band1"] if gi % 2 == 0 else t["band2"]
                for i, e in enumerate(es):
                    hh = nlines(e["label"], cpl) * 92000 + 40000
                    first = ({"text": dom, "bold": True, "fill": band, "span": len(es)} if i == 0 else {"merged": True, "fill": band})
                    trs.append((hh, [first, {"text": e["label"], "fill": band}, {"text": e["when"], "fill": band, "algn": "ctr"}]))
            s.table(300000 + j * (sum(W) + 90000), 1100000, W, trs, sz=600)
        slides.append(s)
    return slides


def status_slides(data, t):
    st = data.get("status", {})
    if not st:
        return []
    COLS = [800000, 1400000, 750000, 2700000, 1950000, 744000]
    CPL = [16, 27, 14, 56, 39, 14]
    hdr = ["Domaine", "Sujet", "Statut", "Situation", "Levier en cours", "Échéance"]
    out = []; n = len(st["slides"])
    for k, sl in enumerate(st["slides"]):
        s = Slide(t)
        s.header(sl["title"], f'{st.get("subtitle", "Situation")} ({k + 1}/{n})')
        trs = [(200000, [{"text": x, "bold": True, "fill": t["header"], "color": "FFFFFF"} for x in hdr])]
        for sec in sl["sections"]:
            for i, r in enumerate(sec["rows"]):
                f, c = STATUS.get(r["status"], ("FFFFFF", "000000"))
                nl = max(nlines(r["subject"], CPL[1]), nlines(r["situation"], CPL[3]), nlines(r.get("lever", ""), CPL[4]), nlines(r.get("due", ""), CPL[5]))
                first = ({"text": sec["domain"], "bold": True, "span": len(sec["rows"]), "fill": t["band1"]} if i == 0 else {"merged": True, "fill": t["band1"]})
                trs.append((nl * 112000 + 95000, [first, {"text": r["subject"], "bold": True, "fill": t["band2"]},
                            {"text": r["status"], "bold": True, "fill": f, "color": c, "algn": "ctr"},
                            {"text": r["situation"], "fill": t["band2"]}, {"text": r.get("lever", ""), "fill": t["band2"]},
                            {"text": r.get("due", ""), "fill": t["band2"]}]))
        tot = s.table(300000, 1100000, COLS, trs)
        if tot > SH - 330000 - 1100000:
            print(f"ATTENTION : la slide « {sl['title']} » deborde ({tot} EMU) : la scinder en deux.", file=sys.stderr)
        out.append(s)
    return out


def table_slides(data, t):
    out = []
    for tb in data.get("tables", []):
        s = Slide(t)
        s.header(tb["title"], tb.get("subtitle"))
        tw = SW - 600000; rel = tb.get("widths") or [1] * len(tb["header"])
        W = [tw * w / sum(rel) for w in rel]
        trs = [(200000, [{"text": x, "bold": True, "fill": t["header"], "color": "FFFFFF"} for x in tb["header"]])]
        for ri, r in enumerate(tb["rows"]):
            last = tb.get("bold_last") and ri == len(tb["rows"]) - 1
            nl = max(nlines(c, int(w / 52000)) for c, w in zip(r, W))
            band = t["band1"] if ri % 2 == 0 else t["band2"]
            trs.append((nl * 112000 + 95000, [{"text": c, "bold": (j == 0 or last), "fill": band} for j, c in enumerate(r)]))
        s.table(300000, 1100000, W, trs)
        out.append(s)
    return out


THEME_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="pmf">'
  '<a:themeElements><a:clrScheme name="pmf"><a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
  '<a:dk2><a:srgbClr val="1F3864"/></a:dk2><a:lt2><a:srgbClr val="E7E6E6"/></a:lt2><a:accent1><a:srgbClr val="2E75B6"/></a:accent1>'
  '<a:accent2><a:srgbClr val="F39200"/></a:accent2><a:accent3><a:srgbClr val="A5A5A5"/></a:accent3><a:accent4><a:srgbClr val="FFC000"/></a:accent4>'
  '<a:accent5><a:srgbClr val="5B9BD5"/></a:accent5><a:accent6><a:srgbClr val="70AD47"/></a:accent6><a:hlink><a:srgbClr val="0563C1"/></a:hlink>'
  '<a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme><a:fontScheme name="pmf"><a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
  '<a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme><a:fmtScheme name="pmf"><a:fillStyleLst>'
  '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
  '</a:fillStyleLst><a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="12700"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
  '<a:ln w="19050"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle>'
  '<a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst>'
  '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
  '</a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>')

GRP = ('<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/>'
       '<a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>')
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'


def write_pptx(slides, out):
    n = len(slides)
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
          '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
          '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
          '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
          '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
          + "".join(f'<Override PartName="/ppt/slides/slide{i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>' for i in range(n))
          + '</Types>')
    rels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{PKG}">'
            f'<Relationship Id="rId1" Type="{REL}/officeDocument" Target="ppt/presentation.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            f'<Relationship Id="rId3" Type="{REL}/extended-properties" Target="docProps/app.xml"/></Relationships>')
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>Planning</dc:title><dc:creator>pm-framework</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
           f'<Application>pm-framework</Application><Slides>{n}</Slides></Properties>')
    pres = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation {NS} saveSubsetFonts="1">'
            '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst>'
            + "".join(f'<p:sldId id="{256 + i}" r:id="rId{10 + i}"/>' for i in range(n))
            + f'</p:sldIdLst><p:sldSz cx="{SW}" cy="{SH}"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>')
    prels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{PKG}">'
             f'<Relationship Id="rId1" Type="{REL}/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
             f'<Relationship Id="rId2" Type="{REL}/theme" Target="theme/theme1.xml"/>'
             + "".join(f'<Relationship Id="rId{10 + i}" Type="{REL}/slide" Target="slides/slide{i + 1}.xml"/>' for i in range(n))
             + '</Relationships>')
    master = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster {NS}><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>'
              f'<a:effectLst/></p:bgPr></p:bg><p:spTree>{GRP}</p:spTree></p:cSld>'
              '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" '
              'accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/>'
              '</p:sldLayoutIdLst></p:sldMaster>')
    mrels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{PKG}">'
             f'<Relationship Id="rId1" Type="{REL}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
             f'<Relationship Id="rId2" Type="{REL}/theme" Target="../theme/theme1.xml"/></Relationships>')
    layout = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout {NS} type="blank" preserve="1"><p:cSld name="Blank">'
              f'<p:spTree>{GRP}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')
    lrels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{PKG}">'
             f'<Relationship Id="rId1" Type="{REL}/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>')
    srels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{PKG}">'
             f'<Relationship Id="rId1" Type="{REL}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>')
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels)
        z.writestr("docProps/core.xml", core); z.writestr("docProps/app.xml", app)
        z.writestr("ppt/presentation.xml", pres); z.writestr("ppt/_rels/presentation.xml.rels", prels)
        z.writestr("ppt/slideMasters/slideMaster1.xml", master); z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", mrels)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", layout); z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", lrels)
        z.writestr("ppt/theme/theme1.xml", THEME_XML)
        for i, s in enumerate(slides):
            z.writestr(f"ppt/slides/slide{i + 1}.xml", s.xml()); z.writestr(f"ppt/slides/_rels/slide{i + 1}.xml.rels", srels)


def build_deck(data):
    t = theme_of(data)
    slides = [gantt_slide(data, t)] + echeances_slides(data, t) + status_slides(data, t) + table_slides(data, t)
    return slides


# --------------------------------------------------------------------------- XLSX (template Gantt)
def _col(c):
    n = 0
    for ch in c:
        n = n * 26 + ord(ch) - 64
    return n


def _serial(d):
    return (D(d) - dt.date(1899, 12, 30)).days


def write_xlsx(data, out, template=None):
    """Remplit le template Gantt : une ligne par tache (B section fusionnee, E tache, F equipe,
    G porteur, H entite, I avancement, J debut, K fin ; C-D masquees). Les barres viennent de la mise en forme conditionnelle du template."""
    template = Path(template or HERE / "templates" / "gantt_template.xlsx")
    zin = zipfile.ZipFile(template)
    files = {n: zin.read(n) for n in zin.namelist()}
    s = files["xl/worksheets/sheet1.xml"].decode("utf-8")
    FIRST, LAST = 8, 127
    tasks = []
    for lane, it in items_of(data):
        if it["type"] == "bar":
            tasks.append((lane, it.get("label", ""), it["start"], it["end"], it))
        elif it["type"] in ("milestone", "note") and it.get("label") and it.get("in_table") is not False:
            tasks.append((lane, it.get("label", ""), it["date"], it["date"], it))
        elif it["type"] == "run":
            end = D(data["start"]) + dt.timedelta(weeks=int(data.get("weeks", 14)))
            tasks.append((lane, it.get("label", "Run"), it["start"], end.isoformat(), it))
    for v in data.get("vlines", []):
        tasks.append((data.get("vlines_domain", "Jalons"), v.get("label", ""), v["date"], v["date"], v))
    if len(tasks) > LAST - FIRST + 1:
        raise SystemExit(f"{len(tasks)} elements : le template n'a que {LAST - FIRST + 1} lignes (8 a 127).")
    C = re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)', re.S)

    def setcell(body, col, rown, value):
        def rep(m):
            if m.group(1) != col:
                return m.group(0)
            attrs = re.sub(r'\s*t="[^"]*"', '', m.group(3)).rstrip('/')
            if value is None or value == "":
                return f'<c r="{col}{rown}"{attrs}/>'
            if isinstance(value, (int, float)):
                return f'<c r="{col}{rown}"{attrs}><v>{value}</v></c>'
            return f'<c r="{col}{rown}"{attrs} t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
        nb, k = C.subn(rep, body)
        return nb

    def editrow(rown, vals):
        nonlocal s
        m = re.search(rf'<row r="{rown}"[^>]*>(.*?)</row>', s, re.S)
        body = m.group(1)
        for col, v in vals.items():
            body = setcell(body, col, rown, v)
        s = s[:m.start(1)] + body + s[m.end(1):]

    # en-tete ; colonnes : Section (B, fusionnee par section) | Tache (E, colonnes C-D masquees)
    # | Equipe | Porteur | Entite | Avancement | Debut | Fin
    editrow(6, {"B": "Section", "C": "", "D": "", "E": "Tâche", "F": "Équipe", "G": "Porteur",
                "H": "Entité", "I": "Avancement", "J": "Début", "K": "Fin"})
    s = re.sub(r'<col min="2" max="4" ([^>]*?)/>',
               lambda m: f'<col min="2" max="2" {m.group(1)}/><col min="3" max="4" {m.group(1)} hidden="1"/>', s, count=1)
    s = re.sub(r'<col min="5" max="5" width="[\d.]+"', '<col min="5" max="5" width="52"', s, count=1)
    editrow(1, {"B": data.get("title", "Planning")})
    editrow(2, {"B": " " + data.get("client", "")})
    editrow(3, {"B": " " + data.get("project", "Project management"), "J": _serial(D(data["start"]) - dt.timedelta(days=D(data["start"]).weekday()))})
    editrow(4, {"J": 1})
    # lignes de taches
    for k in range(FIRST, LAST + 1):
        i = k - FIRST
        if i < len(tasks):
            lane, lab, d1, d2, it = tasks[i]
            first = i == 0 or tasks[i - 1][0] != lane
            editrow(k, {"B": lane if first else "", "C": "", "D": "", "E": lab,
                        "F": it.get("team", ""), "G": it.get("owner", ""), "H": it.get("entity", ""),
                        "I": float(it.get("progress", 0)), "J": _serial(d1), "K": _serial(d2)})
        else:
            editrow(k, {c: "" for c in "BCDEFGHIJK"})
            # lignes inutilisees masquees (elles restent dans le classeur pour ajouter des taches)
            s = re.sub(rf'<row r="{k}"(?![^>]*hidden)', f'<row r="{k}" hidden="1"', s, count=1)
    # valeurs en cache de l'axe (jours ligne 5, debut de semaine ligne 4) : l'apercu est juste
    # meme avant le recalcul d'Excel ; Excel recalcule tout a l'ouverture (fullCalcOnLoad)
    mon = _serial(D(data["start"]) - dt.timedelta(days=D(data["start"]).weekday()))
    def _cache(rown):
        nonlocal s
        m = re.search(rf'<row r="{rown}"[^>]*>(.*?)</row>', s, re.S)
        def rep(c):
            col = c.group(1)
            if _col(col) < _col("N") or not c.group(4) or "<f" not in c.group(4):
                return c.group(0)
            val = mon + _col(col) - _col("N")
            return c.group(0).replace(re.search(r'<v>[^<]*</v>', c.group(0)).group(0), f'<v>{val}</v>') if '<v>' in c.group(0) else c.group(0)
        body = C.sub(rep, m.group(1))
        s = s[:m.start(1)] + body + s[m.end(1):]
    _cache(4); _cache(5)
    # legende compacte : pastille de couleur en J (colonne etroite), libelle en K ; B-E videes
    LEG = [("Fait", 57), ("À faire", 58), ("Week-end", 59), ("Jour férié", 60), ("Autre", 61)]
    def _restyle(rown, col, style, value=None):
        nonlocal s
        m = re.search(rf'<row r="{rown}"([^>]*)>(.*?)</row>', s, re.S)
        if not m:
            return
        body = m.group(2)
        cell = (f'<c r="{col}{rown}" s="{style}"/>' if value is None
                else f'<c r="{col}{rown}" s="{style}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        if re.search(rf'<c r="{col}{rown}"', body):
            body = re.sub(rf'<c r="{col}{rown}"[^>]*?(?:/>|>.*?</c>)', cell, body, count=1, flags=re.S)
        else:  # insertion a la bonne place (ordre des colonnes)
            cells = list(C.finditer(body)); pos = len(body)
            for c in cells:
                if _col(c.group(1)) > _col(col):
                    pos = c.start(); break
            body = body[:pos] + cell + body[pos:]
        attrs = re.sub(r'spans="[^"]*"', 'spans="1:12"', m.group(1))
        s = s[:m.start()] + f'<row r="{rown}"{attrs}>{body}</row>' + s[m.end():]
    s = s.replace('<mergeCell ref="B129:E129"/>', '<mergeCell ref="J129:K129"/>')
    for r in range(129, 135):
        for col in "BCDE":
            _restyle(r, col, 47)
    _restyle(129, "J", 106, "Légende"); _restyle(129, "K", 108)
    for i, (lab, st_) in enumerate(LEG):
        _restyle(130 + i, "J", st_); _restyle(130 + i, "K", 47, lab)
    # fusions de la colonne B par couloir
    s = re.sub(r'<mergeCell ref="B(\d+):B(\d+)"/>', lambda m: '' if FIRST <= int(m.group(1)) <= LAST else m.group(0), s)
    merges, i = [], 0
    while i < len(tasks):
        j = i
        while j + 1 < len(tasks) and tasks[j + 1][0] == tasks[i][0]:
            j += 1
        if j > i:
            merges.append(f'<mergeCell ref="B{FIRST + i}:B{FIRST + j}"/>')
        i = j + 1
    s = re.sub(r'<mergeCells count="\d+">', lambda m: m.group(0) + "".join(merges), s, count=1)
    s = re.sub(r'<mergeCells count="\d+">', f'<mergeCells count="{len(re.findall("<mergeCell ", s))}">', s, count=1)
    files["xl/worksheets/sheet1.xml"] = s.encode("utf-8")
    # typographie : une seule police pour tout le classeur (Calibri par defaut, theme.xlsx_font)
    font = data.get("theme", {}).get("xlsx_font", "Calibri")
    st = files["xl/styles.xml"].decode("utf-8")
    st = re.sub(r'<name val="[^"]*"/>', f'<name val="{font}"/>', st)
    st = re.sub(r'<family val="\d+"/>', '<family val="2"/>', st)
    st = re.sub(r'<scheme val="(major|minor)"/>', '', st)
    files["xl/styles.xml"] = st.encode("utf-8")
    th = files["xl/theme/theme1.xml"].decode("utf-8")
    th = re.sub(r'(<a:(?:major|minor)Font><a:latin typeface=")[^"]*"', rf'\g<1>{font}"', th)
    files["xl/theme/theme1.xml"] = th.encode("utf-8")
    # recalcul complet a l'ouverture ; la chaine de calcul (formules retirees) est supprimee
    wb = files["xl/workbook.xml"].decode("utf-8")
    wb = re.sub(r'<calcPr[^>]*/>', '<calcPr calcId="191028" fullCalcOnLoad="1"/>', wb)
    files["xl/workbook.xml"] = wb.encode("utf-8")
    files.pop("xl/calcChain.xml", None)
    files["[Content_Types].xml"] = re.sub(rb'<Override PartName="/xl/calcChain.xml"[^>]*/>', b'', files["[Content_Types].xml"])
    files["xl/_rels/workbook.xml.rels"] = re.sub(rb'<Relationship [^>]*calcChain[^>]*/>', b'', files["xl/_rels/workbook.xml.rels"])
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n in zin.namelist():
            if n in files:
                z.writestr(n, files[n])
    return len(tasks)


# --------------------------------------------------------------------------- CLI
def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__); return 2
    mission, args = argv[0], argv[1:]
    def opt(name):
        return args[args.index(name) + 1] if name in args else None
    data, src = load_data(mission, opt("--input"))
    if "--json" in args:
        print(json.dumps({"source": str(src), "echeances": echeances(data), "checks": checks(data), "data": data}, ensure_ascii=False, indent=1))
        return 0
    did = False
    if opt("--pptx"):
        tpl = opt("--pptx-template") or (data.get("template") or {}).get("pptx")
        layout = opt("--layout") or (data.get("template") or {}).get("layout")
        box = (data.get("template") or {}).get("box")
        if tpl:
            tplp = Path(tpl).expanduser()
            if not tplp.is_absolute() and src:
                tplp = (Path(src).parent / tplp) if (Path(src).parent / tplp).exists() else tplp
            load_template(str(tplp), layout, box)        # fixe la zone utile avant de dessiner
            slides = build_deck(data)
            lay = write_pptx_template(slides, str(tplp), opt("--pptx"), layout, box)
            print(f"deck : {opt('--pptx')} ({len(slides)} slides, gabarit {tplp.name}, mise en page {lay.rsplit('/', 1)[1]})")
        else:
            slides = build_deck(data)
            write_pptx(slides, opt("--pptx"))
            print(f"deck : {opt('--pptx')} ({len(slides)} slides : Gantt, echeances, situation, tableaux)")
        did = True
    if opt("--xlsx"):
        n = write_xlsx(data, opt("--xlsx"), opt("--template"))
        print(f"Gantt Excel : {opt('--xlsx')} ({n} lignes)"); did = True
    if not did:
        print(f"source : {src}\n"); print(to_md(data))
    iss = checks(data)
    if did and iss:
        print("\nControles :\n" + "\n".join(f"- {i}" for i in iss))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
