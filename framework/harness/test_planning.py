#!/usr/bin/env python3
"""Test du generateur planning : exemple -> markdown, PPTX et XLSX valides, echeances = elements libelles."""
import sys, zipfile, tempfile, importlib.util, json
from pathlib import Path
import xml.dom.minidom as m
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("planning", ROOT / "framework/departements/planification/generators/planning/planning.py")
P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
data = json.load(open(ROOT / "framework/departements/planification/generators/planning/planning.example.json"))
ok = True
def check(cond, msg):
    global ok
    print(("OK   " if cond else "FAIL ") + msg); ok = ok and cond
ech = P.echeances(data)
labelled = [it for _, it in P.items_of(data) if it.get("label") and it.get("in_table") is not False]
check(len(ech) == len(labelled), f"echeances derivees du Gantt ({len(ech)} = {len(labelled)})")
check(P.checks(data) == [], "exemple sans ecart de controle")
with tempfile.TemporaryDirectory() as d:
    pp = Path(d) / "p.pptx"; xx = Path(d) / "g.xlsx"
    slides = P.build_deck(data); P.write_pptx(slides, pp)
    z = zipfile.ZipFile(pp)
    for n in z.namelist():
        if n.endswith(".xml") or n.endswith(".rels"):
            m.parseString(z.read(n))
    check(len(slides) >= 4, f"deck PPTX valide ({len(slides)} slides, XML bien forme)")
    for e in ech:
        if e["label"] not in z.read("ppt/slides/slide2.xml").decode():
            check(False, f"echeance absente de la slide 2 : {e['label']}"); break
    else:
        check(True, "toutes les echeances sont sur la slide 2")
    n = P.write_xlsx(data, xx)
    zx = zipfile.ZipFile(xx); m.parseString(zx.read("xl/worksheets/sheet1.xml"))
    check("xl/calcChain.xml" not in zx.namelist(), f"Gantt Excel valide ({n} lignes, calcChain retire)")

# --- gabarit d'entreprise (--pptx-template) : un deck existant sert de gabarit, ses slides sont retirees
with tempfile.TemporaryDirectory() as d:
    tpl = Path(d) / "tpl.pptx"; out = Path(d) / "o.pptx"
    P.TPL = None; P.write_pptx(P.build_deck(data), tpl)
    zt = zipfile.ZipFile(tpl); files = {n: zt.read(n) for n in zt.namelist()}
    title_ph = ('<p:sp><p:nvSpPr><p:cNvPr id="2" name="Titre"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>'
                '<p:spPr><a:xfrm><a:off x="300000" y="150000"/><a:ext cx="8500000" cy="450000"/></a:xfrm></p:spPr></p:sp>')
    lay = files["ppt/slideLayouts/slideLayout1.xml"].decode().replace('name="Blank"', 'name="Corporate"')
    lay = lay.replace('</p:grpSpPr></p:spTree>', '</p:grpSpPr>' + title_ph + '</p:spTree>')
    files["ppt/slideLayouts/slideLayout1.xml"] = lay.encode()
    with zipfile.ZipFile(tpl, "w") as zo:
        for n, b in files.items():
            zo.writestr(n, b)
    P.load_template(str(tpl), "Corporate")
    slides = P.build_deck(data); P.write_pptx_template(slides, str(tpl), str(out), "Corporate")
    zo = zipfile.ZipFile(out)
    for n in zo.namelist():
        if n.endswith(".xml") or n.endswith(".rels"):
            m.parseString(zo.read(n))
    pres = zo.read("ppt/presentation.xml").decode()
    nslides = len([n for n in zo.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")])
    check(nslides == len(slides) and pres.count("<p:sldId ") == len(slides),
          f"gabarit : slides du gabarit retirees, {len(slides)} slides generees")
    s1 = zo.read("ppt/slides/slide1.xml").decode()
    check('<p:ph type="title"/>' in s1 and "slideLayout1.xml" in zo.read("ppt/slides/_rels/slide1.xml.rels").decode(),
          "gabarit : titre dans l'emplacement titre de la mise en page choisie")
    import re as _re
    body = s1.split("</p:grpSpPr>", 1)[1]          # sans l'en-tete de groupe (origine 0,0)
    ys = [int(y) for y in _re.findall(r'<a:off x="-?\d+" y="(\d+)"', body)]
    check(min(ys) >= 600000, "gabarit : le contenu est recale sous le titre")
    P.TPL = None
sys.exit(0 if ok else 1)
